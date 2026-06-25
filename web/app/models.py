"""
Database models mapped to the Supabase (Spanish) schema:
  cliente, habitacion, reserva, opinion.

Each model exposes compatibility @property aliases (name, price_cop, images,
status, ...) so the existing templates keep working without changes.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(160), index=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now())


class Habitacion(Base):
    __tablename__ = "habitacion"

    id_hab: Mapped[str] = mapped_column(String(16), primary_key=True)
    nom_hab: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cama: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tam_m2: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    vista: Mapped[str | None] = mapped_column(String(80), nullable=True)
    precio_noche: Mapped[int] = mapped_column(Integer)
    ca_max: Mapped[int] = mapped_column(SmallInteger, default=2)
    fotos: Mapped[str | None] = mapped_column(Text, nullable=True)
    amenidades: Mapped[str | None] = mapped_column(Text, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- template-compatibility aliases ---
    @property
    def id(self): return self.id_hab
    @property
    def slug(self): return self.id_hab
    @property
    def number(self): return self.id_hab
    @property
    def name(self): return self.nom_hab
    @property
    def room_type(self): return self.tipo or ""
    @property
    def bed(self): return self.cama or ""
    @property
    def size_m2(self): return self.tam_m2
    @property
    def max_occupancy(self): return self.ca_max
    @property
    def view(self): return self.vista or ""
    @property
    def price_cop(self): return self.precio_noche
    @property
    def description(self): return self.descripcion or ""
    @property
    def images(self) -> list[str]:
        return [s for s in (self.fotos or "").split(",") if s]
    @property
    def amenities(self) -> list[str]:
        return [s for s in (self.amenidades or "").split(",") if s]


class Reserva(Base):
    __tablename__ = "reserva"

    id_res: Mapped[int] = mapped_column(primary_key=True)
    referencia: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id"))
    id_hab: Mapped[str] = mapped_column(ForeignKey("habitacion.id_hab"), index=True)
    fecha_in: Mapped[date] = mapped_column(Date, index=True)
    fecha_fi: Mapped[date] = mapped_column(Date, index=True)
    n_adultos: Mapped[int] = mapped_column(SmallInteger, default=1)
    n_ninos: Mapped[int] = mapped_column(SmallInteger, default=0)
    valor: Mapped[int] = mapped_column(Integer)
    moneda: Mapped[str] = mapped_column(String(3), default="COP")
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)
    wompi_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hold_expira: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                        nullable=True)
    # Channel manager (Lobby PMS) sync metadata.
    #   origen: 'directo' (this site) | 'lobby' (imported from an OTA/Lobby)
    #   lobby_code: the reservation code in Lobby (set once pushed/imported)
    origen: Mapped[str] = mapped_column(String(10), default="directo", index=True)
    lobby_code: Mapped[str | None] = mapped_column(String(40), nullable=True,
                                                   unique=True, index=True)
    lobby_synced_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                             nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now())

    cliente: Mapped[Cliente] = relationship(lazy="selectin")
    habitacion: Mapped[Habitacion] = relationship(lazy="selectin")

    # --- template-compatibility aliases ---
    @property
    def reference(self): return self.referencia
    @property
    def amount_cop(self): return self.valor
    @property
    def checkin(self): return self.fecha_in
    @property
    def checkout(self): return self.fecha_fi
    @property
    def nights(self): return (self.fecha_fi - self.fecha_in).days
    @property
    def guests(self): return (self.n_adultos or 0) + (self.n_ninos or 0)
    @property
    def guest_name(self): return self.cliente.nombre if self.cliente else ""
    @property
    def guest_email(self): return self.cliente.correo if self.cliente else ""
    @property
    def amount_cents(self): return self.valor * 100


class RateLimit(Base):
    """Fixed-window request counter shared across serverless instances.
    Primary key (clave, ventana) = (ip+tier, epoch-minute); conteo is the count."""
    __tablename__ = "rate_limit"

    clave: Mapped[str] = mapped_column(String(80), primary_key=True)
    ventana: Mapped[int] = mapped_column(Integer, primary_key=True)
    conteo: Mapped[int] = mapped_column(Integer, default=0)


class Escalacion(Base):
    """A chatbot conversation handed off to reception (escalate_to_human)."""
    __tablename__ = "escalacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    motivo: Mapped[str] = mapped_column(Text)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    idioma: Mapped[str] = mapped_column(String(2), default="es")
    contexto: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Canal preferido por el huésped para que recepción le responda: "whatsapp"
    # o "correo" (lo elige en el chat al escalar).
    canal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Browser conversation thread (a client UUID) so a human reply written from
    # the admin can be delivered back into that guest's live chat widget.
    thread_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    atendido: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now())


class RespuestaChat(Base):
    """A human reply queued for a chat thread. The guest's widget polls these by
    `thread_id` (an unguessable client UUID) and renders them as bot bubbles.
    `id` is monotonic and doubles as the polling cursor."""
    __tablename__ = "respuesta_chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(40), index=True)
    texto: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now())


class Opinion(Base):
    __tablename__ = "opinion"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_hab: Mapped[str | None] = mapped_column(
        ForeignKey("habitacion.id_hab"), nullable=True)
    autor: Mapped[str] = mapped_column(String(120))
    pais: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    titulo: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cuerpo: Mapped[str] = mapped_column(Text)
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now())

    # --- template-compatibility aliases ---
    @property
    def author(self): return self.autor
    @property
    def country(self): return self.pais or ""
    @property
    def title(self): return self.titulo or ""
    @property
    def body(self): return self.cuerpo
