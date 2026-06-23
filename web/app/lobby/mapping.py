"""Wire-format adapter for Lobby PMS v2 — the ONLY place that knows Lobby's
field names. The exact names are confirmed against the authenticated API docs
(app.lobbypms.com/api-docs) or Lobby support; until then we read tolerantly
(several candidate keys) so a single edit here fixes the whole integration.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from ..config import settings

# Local 'estado' we assign to a reservation imported from an OTA via Lobby.
EXTERNAL_STATE = "externa"

# Lobby statuses we treat as "no longer blocking" (cancelled / no-show).
_CANCELLED = {"cancelled", "canceled", "cancelada", "cancelado", "no_show",
              "no-show", "noshow"}


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    """Return the first present, non-None value among `keys` (tolerant to the
    not-yet-confirmed Lobby field names)."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


# --- Room id mapping (local id_hab <-> Lobby room/product id) ---------------
def room_id_to_lobby(id_hab: str) -> str | None:
    return settings.lobby_room_pairs().get(id_hab)


def lobby_to_room_id(lobby_room_id: str) -> str | None:
    for id_hab, lid in settings.lobby_room_pairs().items():
        if str(lid) == str(lobby_room_id):
            return id_hab
    return None


# --- Inbound: Lobby reservation -> local fields -----------------------------
def normalize_reservation(raw: dict) -> dict | None:
    """Map a Lobby reservation to the fields the sync needs. Returns None if the
    room can't be mapped or dates are missing (we skip it rather than guess)."""
    lobby_room = _first(raw, "room_id", "roomId", "id_habitacion", "room")
    id_hab = lobby_to_room_id(str(lobby_room)) if lobby_room is not None else None
    checkin = _as_date(_first(raw, "check_in", "checkin", "fecha_in", "arrival"))
    checkout = _as_date(_first(raw, "check_out", "checkout", "fecha_fi", "departure"))
    if not id_hab or not checkin or not checkout:
        return None

    status = str(_first(raw, "status", "estado", default="")).lower()
    adults = int(_first(raw, "adults", "n_adultos", "guests", default=1) or 1)
    children = int(_first(raw, "children", "n_ninos", default=0) or 0)
    return {
        "lobby_code": str(_first(raw, "code", "id", "reservation_code",
                                 "codigo", default="")),
        "id_hab": id_hab,
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
        "children": children,
        "amount": int(_first(raw, "total", "amount", "valor", default=0) or 0),
        "cancelled": status in _CANCELLED,
        "guest_name": str(_first(raw, "guest_name", "client_name", "nombre",
                                 default="Reserva OTA")),
        "guest_email": str(_first(raw, "guest_email", "email", "correo", default="")),
        "guest_phone": str(_first(raw, "guest_phone", "phone", "telefono", default="")),
    }


# --- Inbound: Lobby room/product -> rate update -----------------------------
def normalize_room(raw: dict) -> dict | None:
    """Map a Lobby available-room/product to {id_hab, price, active}."""
    lobby_room = _first(raw, "room_id", "roomId", "id", "product_id")
    id_hab = lobby_to_room_id(str(lobby_room)) if lobby_room is not None else None
    if not id_hab:
        return None
    price = _first(raw, "price", "rate", "precio", "amount")
    return {
        "id_hab": id_hab,
        "price": int(price) if price is not None else None,
        "active": bool(_first(raw, "active", "available", "activa", default=True)),
    }


# --- Outbound: local booking -> Lobby create-reservation body ---------------
def booking_to_lobby_payload(reserva, lobby_room_id: str) -> dict:
    """Build the create-reservation body Lobby expects for a direct booking,
    including the guest count for this channel."""
    cli = getattr(reserva, "cliente", None)
    return {
        "room_id": lobby_room_id,
        "check_in": reserva.fecha_in.isoformat(),
        "check_out": reserva.fecha_fi.isoformat(),
        "adults": reserva.n_adultos,
        "children": reserva.n_ninos,
        "guests": (reserva.n_adultos or 0) + (reserva.n_ninos or 0),
        "total": reserva.valor,
        "currency": reserva.moneda,
        "reference": reserva.referencia,
        "guest_name": getattr(cli, "nombre", "") if cli else "",
        "guest_email": getattr(cli, "correo", "") if cli else "",
        "guest_phone": getattr(cli, "telefono", "") if cli else "",
        "source": "directo",
    }


def reservation_code_from_response(raw: dict) -> str:
    """Pull the new reservation's code out of a create-reservation response."""
    return str(_first(raw, "code", "id", "reservation_code", "codigo", default=""))
