"""
JSON API connecting the database with the front-end (and any external client):
rooms, availability, calendar, bookings and reviews. All read/write goes
through the crud layer (Supabase).
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, i18n
from ..config import settings
from ..database import get_session
from ..deps import rate_limit
from ..schemas import AvailabilityResult, BookingCreate, ReviewCreate

router = APIRouter(prefix="/api", tags=["api"])


def _usd(cop: int) -> int:
    return round((cop or 0) / settings.usd_to_cop)


def room_dict(room, lang: str = "es") -> dict:
    return {
        "id": room.id_hab,
        "name": i18n.room_name(room, lang),
        "name_es": room.nom_hab,
        "name_en": i18n.ROOM_EN.get(room.id_hab, {}).get("name", room.nom_hab),
        "type": room.tipo,
        "description": i18n.room_desc(room, lang),
        "bed": room.cama,
        "size_m2": room.tam_m2,
        "max_occupancy": room.ca_max,
        "view": room.vista,
        "price_cop": room.precio_noche,
        "price_usd": _usd(room.precio_noche),
        "images": room.images,
        "amenities": room.amenities,
        "active": room.activa,
    }


def booking_dict(b) -> dict:
    return {
        "reference": b.referencia,
        "room_id": b.id_hab,
        "checkin": b.fecha_in.isoformat(),
        "checkout": b.fecha_fi.isoformat(),
        "nights": b.nights,
        "guests": b.guests,
        "amount_cop": b.valor,
        "amount_usd": _usd(b.valor),
        "currency": b.moneda,
        "status": b.estado,
        "guest_name": b.guest_name,
        "guest_email": b.guest_email,
    }


# --- Rooms -----------------------------------------------------------------
@router.get("/rooms")
async def api_rooms(request: Request, db: AsyncSession = Depends(get_session)):
    await rate_limit(request)
    lang = i18n.get_lang(request)
    rooms = await crud.list_rooms(db)
    return {"rooms": [room_dict(r, lang) for r in rooms]}


@router.get("/rooms/{room_id}")
async def api_room(request: Request, room_id: str,
                  db: AsyncSession = Depends(get_session)):
    await rate_limit(request)
    room = await crud.get_room(db, room_id)
    if not room or not room.activa:
        raise HTTPException(404, "Room not found")
    return room_dict(room, i18n.get_lang(request))


# --- Availability + calendar ----------------------------------------------
@router.get("/availability", response_model=AvailabilityResult)
async def availability(request: Request, room_id: str, checkin: date, checkout: date,
                      db: AsyncSession = Depends(get_session)):
    await rate_limit(request)
    if checkin < date.today():
        raise HTTPException(400, "Check-in cannot be in the past.")
    if checkout <= checkin:
        raise HTTPException(400, "Check-out must be after check-in.")
    room = await crud.get_room(db, room_id)
    if not room or not room.activa:
        raise HTTPException(404, "Room not found")
    nights = (checkout - checkin).days
    ok = await crud.is_available(db, room_id, checkin, checkout)
    return AvailabilityResult(room_id=room_id, available=ok, nights=nights,
                              price_cop=room.precio_noche,
                              total_cop=nights * room.precio_noche)


@router.get("/rooms/{room_id}/calendar")
async def calendar(request: Request, room_id: str,
                  start: date | None = None, days: int = 90,
                  db: AsyncSession = Depends(get_session)):
    await rate_limit(request)
    room = await crud.get_room(db, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    start = start or date.today()
    end = start + timedelta(days=min(days, 365))
    ranges = await crud.booked_ranges(db, room_id, start, end)
    return {"room_id": room_id, "start": start.isoformat(), "end": end.isoformat(),
            "booked": [{"from": a.isoformat(), "to": b.isoformat()} for a, b in ranges]}


# --- Bookings --------------------------------------------------------------
@router.post("/bookings", status_code=201)
async def api_create_booking(request: Request, payload: BookingCreate,
                            db: AsyncSession = Depends(get_session)):
    await rate_limit(request, max_per_minute=15)
    room = await crud.get_room(db, payload.room_id)
    if not room or not room.activa:
        raise HTTPException(404, "Room not found")
    if payload.guests > room.max_occupancy:
        raise HTTPException(400, f"Max {room.max_occupancy} guests for this room.")
    if not await crud.is_available(db, room.id_hab, payload.checkin, payload.checkout):
        raise HTTPException(409, "Those dates are no longer available.")
    try:
        booking = await crud.create_booking(db, room, payload)
    except crud.DatesUnavailable:
        raise HTTPException(409, "Those dates are no longer available.") from None
    return booking_dict(booking)


@router.get("/bookings/{reference}")
async def api_booking(request: Request, reference: str,
                     db: AsyncSession = Depends(get_session)):
    await rate_limit(request)
    booking = await crud.get_booking(db, reference)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking_dict(booking)


# --- Reviews ---------------------------------------------------------------
@router.get("/reviews")
async def api_reviews(request: Request, db: AsyncSession = Depends(get_session)):
    await rate_limit(request)
    rows = await crud.list_reviews(db, approved_only=True, limit=100)
    avg, count = await crud.average_rating(db)
    return {
        "average": avg, "count": count,
        "reviews": [{"author": r.autor, "country": r.pais, "rating": r.rating,
                     "title": r.titulo, "body": r.cuerpo,
                     "created_at": r.creado_en.isoformat() if r.creado_en else None}
                    for r in rows],
    }


@router.post("/reviews", status_code=201)
async def api_create_review(request: Request, payload: ReviewCreate,
                           db: AsyncSession = Depends(get_session)):
    await rate_limit(request, max_per_minute=6)
    op = await crud.create_review(db, payload,
                                  auto_approve=not settings.reviews_require_approval)
    return {"ok": True, "id": op.id, "approved": op.aprobado}
