"""Data access layer against the Supabase schema (habitacion/reserva/cliente/opinion)."""
from __future__ import annotations

import random
import re
import secrets
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Cliente, Escalacion, Habitacion, Opinion, Reserva

HOLD_MINUTES = 20
ACTIVE_STATES = ("pendiente", "confirmada")


class DatesUnavailable(Exception):
    """Raised when a room's dates are no longer free (lost a race against the
    database exclusion constraint). Routers turn this into a clean 409."""


def _utcnow() -> datetime:
    # timezone-aware UTC (utcnow() is naive and deprecated on 3.12+).
    return datetime.now(timezone.utc)


# --- Habitaciones ----------------------------------------------------------
async def list_rooms(db: AsyncSession) -> list[Habitacion]:
    res = await db.execute(
        select(Habitacion).where(Habitacion.activa).order_by(Habitacion.precio_noche))
    return list(res.scalars().all())


async def get_room(db: AsyncSession, id_hab: str) -> Habitacion | None:
    return await db.get(Habitacion, id_hab)


# slug == id_hab in this schema
async def get_room_by_slug(db: AsyncSession, slug: str) -> Habitacion | None:
    return await db.get(Habitacion, slug)


# --- Availability ----------------------------------------------------------
def _active_filter():
    now = _utcnow()
    return or_(
        Reserva.estado == "confirmada",
        and_(Reserva.estado == "pendiente",
             or_(Reserva.hold_expira.is_(None), Reserva.hold_expira > now)),
    )


async def is_available(db: AsyncSession, id_hab: str,
                       checkin: date, checkout: date) -> bool:
    res = await db.execute(
        select(func.count(Reserva.id_res)).where(
            Reserva.id_hab == id_hab,
            Reserva.fecha_in < checkout,
            Reserva.fecha_fi > checkin,
            _active_filter(),
        ))
    return (res.scalar_one() or 0) == 0


async def booked_ranges(db: AsyncSession, id_hab: str,
                        start: date, end: date) -> list[tuple[date, date]]:
    res = await db.execute(
        select(Reserva.fecha_in, Reserva.fecha_fi).where(
            Reserva.id_hab == id_hab,
            Reserva.fecha_in < end,
            Reserva.fecha_fi > start,
            _active_filter(),
        ))
    return [(r[0], r[1]) for r in res.all()]


async def release_expired_holds(db: AsyncSession) -> int:
    """Flip pending holds whose 20-minute window elapsed to 'expirada'.

    This frees the dates BOTH logically (queries) and physically (the database
    EXCLUDE constraint), so another guest can book them. It is a cheap no-op
    when nothing has expired (backed by a partial index)."""
    res = await db.execute(
        update(Reserva)
        .where(Reserva.estado == "pendiente",
               Reserva.hold_expira.is_not(None),
               Reserva.hold_expira < _utcnow())
        .values(estado="expirada")
    )
    return res.rowcount or 0


# --- Clientes + Reservas ---------------------------------------------------
def _new_reference() -> str:
    return "CG-" + _utcnow().strftime("%y%m%d") + "-" + secrets.token_hex(3).upper()


async def _get_or_create_cliente(db: AsyncSession, nombre: str, correo: str,
                                 telefono: str) -> Cliente:
    res = await db.execute(select(Cliente).where(Cliente.correo == correo).limit(1))
    cli = res.scalar_one_or_none()
    if cli:
        cli.nombre = nombre or cli.nombre
        if telefono:
            cli.telefono = telefono
        return cli
    cli = Cliente(nombre=nombre, correo=correo, telefono=telefono or None)
    db.add(cli)
    await db.flush()      # assign id
    return cli


async def create_booking(db: AsyncSession, room: Habitacion, data) -> Reserva:
    nights = (data.checkout - data.checkin).days
    # Free any stale holds first, so the exclusion constraint won't reject dates
    # that are actually available again.
    await release_expired_holds(db)
    cli = await _get_or_create_cliente(db, data.guest_name, str(data.guest_email),
                                       data.guest_phone)
    reserva = Reserva(
        referencia=_new_reference(),
        id_cliente=cli.id,
        id_hab=room.id_hab,
        fecha_in=data.checkin,
        fecha_fi=data.checkout,
        n_adultos=data.guests,
        n_ninos=0,
        valor=nights * room.precio_noche,
        moneda="COP",
        estado="pendiente",
        notas=data.notes or None,
        hold_expira=_utcnow() + timedelta(minutes=HOLD_MINUTES),
    )
    db.add(reserva)
    try:
        await db.commit()
    except IntegrityError:
        # Lost the race: another booking grabbed these dates (EXCLUDE constraint).
        await db.rollback()
        raise DatesUnavailable()
    await db.refresh(reserva)
    return reserva


async def get_booking(db: AsyncSession, referencia: str) -> Reserva | None:
    res = await db.execute(select(Reserva).where(Reserva.referencia == referencia))
    return res.scalar_one_or_none()


async def set_booking_status(db: AsyncSession, referencia: str, estado: str,
                             transaction_id: str = "") -> Reserva | None:
    reserva = await get_booking(db, referencia)
    if not reserva:
        return None
    reserva.estado = estado
    if transaction_id:
        reserva.wompi_tx_id = transaction_id
    if estado == "confirmada":
        reserva.hold_expira = None
    await db.commit()
    await db.refresh(reserva)
    return reserva


# --- Opiniones -------------------------------------------------------------
async def list_reviews(db: AsyncSession, approved_only: bool = True,
                       limit: int = 50) -> list[Opinion]:
    stmt = select(Opinion).order_by(Opinion.creado_en.desc()).limit(limit)
    if approved_only:
        stmt = stmt.where(Opinion.aprobado.is_(True))
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def average_rating(db: AsyncSession) -> tuple[float, int]:
    res = await db.execute(
        select(func.avg(Opinion.rating), func.count(Opinion.id))
        .where(Opinion.aprobado.is_(True)))
    avg, cnt = res.one()
    return (round(float(avg), 1) if avg else 0.0, int(cnt or 0))


async def create_review(db: AsyncSession, data, auto_approve: bool) -> Opinion:
    # Guard the FK: ignore a room id that doesn't exist (keep the review general)
    # instead of failing with a foreign-key error.
    room_id = data.room_id or None
    if room_id and await db.get(Habitacion, room_id) is None:
        room_id = None
    op = Opinion(
        id_hab=room_id, autor=data.author, pais=data.country,
        rating=data.rating, titulo=data.title, cuerpo=data.body,
        aprobado=auto_approve,
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def approve_review(db: AsyncSession, review_id: int) -> bool:
    op = await db.get(Opinion, review_id)
    if not op:
        return False
    op.aprobado = True
    await db.commit()
    return True


# --- Escalaciones del chatbot ---------------------------------------------
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def extract_contact(text: str) -> str | None:
    """Best-effort guest contact (email or phone) from free text, for follow-up."""
    if not text:
        return None
    m = _EMAIL_RE.search(text)
    if m:
        return m.group(0)
    m = _PHONE_RE.search(text)
    if m:
        return m.group(0).strip()
    return None


async def create_escalation(db: AsyncSession, *, motivo: str,
                            mensaje: str | None = None, idioma: str = "es",
                            contexto: str | None = None,
                            contacto: str | None = None) -> Escalacion:
    esc = Escalacion(
        motivo=(motivo or "Sin especificar")[:2000],
        mensaje=(mensaje or None),
        idioma=idioma if idioma in ("es", "en") else "es",
        contexto=contexto,
        contacto=contacto,
    )
    db.add(esc)
    await db.commit()
    await db.refresh(esc)
    return esc


async def list_escalations(db: AsyncSession, pending_only: bool = False,
                           limit: int = 100) -> list[Escalacion]:
    stmt = select(Escalacion).order_by(Escalacion.creado_en.desc()).limit(limit)
    if pending_only:
        stmt = stmt.where(Escalacion.atendido.is_(False))
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def mark_escalation_attended(db: AsyncSession, esc_id: int) -> bool:
    esc = await db.get(Escalacion, esc_id)
    if not esc:
        return False
    esc.atendido = True
    await db.commit()
    return True


# --- Admin views -----------------------------------------------------------
async def list_recent_bookings(db: AsyncSession, limit: int = 50) -> list[Reserva]:
    res = await db.execute(
        select(Reserva).order_by(Reserva.creado_en.desc()).limit(limit))
    return list(res.scalars().all())


async def list_pending_reviews(db: AsyncSession, limit: int = 50) -> list[Opinion]:
    res = await db.execute(
        select(Opinion).where(Opinion.aprobado.is_(False))
        .order_by(Opinion.creado_en.desc()).limit(limit))
    return list(res.scalars().all())


# --- Rate limiting (distributed, fixed window) -----------------------------
_RL_UPSERT = text(
    "insert into rate_limit (clave, ventana, conteo) values (:k, :w, 1) "
    "on conflict (clave, ventana) do update set conteo = rate_limit.conteo + 1 "
    "returning conteo"
)


async def hit_rate_limit(db: AsyncSession, key: str,
                         window_seconds: int = 60) -> int:
    """Atomically increment and return the request count for this key+window.
    Shared across instances (Postgres). Caller compares it against the limit."""
    window = int(time.time() // window_seconds)
    res = await db.execute(_RL_UPSERT, {"k": key, "w": window})
    count = int(res.scalar_one())
    # Cheap opportunistic purge of stale windows (~2% of calls).
    if random.random() < 0.02:
        await db.execute(text("delete from rate_limit where ventana < :old"),
                         {"old": window - 2})
    await db.commit()
    return count
