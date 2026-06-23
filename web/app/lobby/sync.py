"""Two-way sync between the local DB and Lobby PMS.

Inbound  (pull): OTA reservations + nightly rates from Lobby into the local DB,
                 so the direct site never oversells and shows Lobby prices.
Outbound (push): a confirmed direct booking is created in Lobby, so it blocks
                 the dates across all channels.

All functions degrade gracefully: a Lobby outage logs and returns a result
summary instead of breaking the request that triggered it.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..config import settings
from . import mapping
from .client import LobbyClient, LobbyError, get_client

log = logging.getLogger("casagracia.lobby.sync")


def _window() -> tuple[date, date]:
    today = date.today()
    return today, today + timedelta(days=settings.lobby_sync_window_days)


async def pull_reservations(db: AsyncSession, client: LobbyClient) -> dict:
    """Import/refresh OTA reservations from Lobby as local blocking rows."""
    desde, hasta = _window()
    rows = await client.list_reservations(checkin_from=desde, checkin_to=hasta)
    imported = skipped = 0
    for raw in rows:
        norm = mapping.normalize_reservation(raw)
        if not norm or not norm["lobby_code"]:
            skipped += 1
            continue
        await crud.upsert_external_reservation(db, norm)
        imported += 1
    log.info("Lobby pull_reservations: %d imported, %d skipped", imported, skipped)
    return {"imported": imported, "skipped": skipped}


async def pull_rates(db: AsyncSession, client: LobbyClient) -> dict:
    """Refresh local nightly prices/availability from Lobby's configured rooms."""
    rooms = await client.available_rooms()
    updated = 0
    for raw in rooms:
        norm = mapping.normalize_room(raw)
        if not norm:
            continue
        if await crud.update_room_price(db, norm["id_hab"], norm["price"], norm["active"]):
            updated += 1
    log.info("Lobby pull_rates: %d rooms updated", updated)
    return {"updated": updated}


async def push_booking(db: AsyncSession, reserva) -> str | None:
    """Create a direct booking in Lobby. Idempotent: if it already carries a
    lobby_code it is not re-sent. Returns the Lobby code (or None if disabled/
    unmapped/failed — the caller treats Lobby as best-effort)."""
    if not settings.lobby_enabled:
        return None
    if reserva.lobby_code:
        return reserva.lobby_code
    lobby_room = mapping.room_id_to_lobby(reserva.id_hab)
    if not lobby_room:
        log.warning("push_booking: no Lobby room mapped for %s", reserva.id_hab)
        return None
    payload = mapping.booking_to_lobby_payload(reserva, lobby_room)
    try:
        async with get_client() as client:
            resp = await client.create_reservation(payload)
    except LobbyError:
        log.exception("push_booking failed for %s", reserva.referencia)
        return None
    code = mapping.reservation_code_from_response(resp)
    if code:
        await crud.mark_booking_pushed(db, reserva, code)
    return code or None


async def run_full_sync(db: AsyncSession) -> dict:
    """Inbound sync entrypoint (Vercel Cron / admin button). Pulls reservations
    and rates. Never raises: returns an ``ok`` flag plus per-step summaries."""
    if not settings.lobby_enabled:
        return {"ok": False, "reason": "lobby disabled"}
    try:
        async with get_client() as client:
            reservations = await pull_reservations(db, client)
            rates = await pull_rates(db, client)
    except LobbyError as e:
        log.exception("Lobby full sync failed")
        return {"ok": False, "reason": str(e)}
    return {"ok": True, "reservations": reservations, "rates": rates}
