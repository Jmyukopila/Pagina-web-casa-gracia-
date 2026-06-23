"""Tests for the two-way Lobby sync (pull reservations/rates, push booking)."""
from __future__ import annotations

from datetime import date, timedelta

import httpx
import pytest

from app import crud
from app.config import settings
from app.lobby import sync
from app.lobby.client import LobbyClient
from app.models import Reserva

CI = date.today() + timedelta(days=10)
CO = CI + timedelta(days=2)


@pytest.fixture(autouse=True)
def _map_room(monkeypatch):
    # Map local DBL-01 <-> Lobby room "100" for every test here.
    monkeypatch.setattr(settings, "lobby_room_map", '{"DBL-01": "100"}')


def _client(handler) -> LobbyClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return LobbyClient(base_url="https://api.test/v2", token="T", http=http)


def _reservation(code="LOB1", status="confirmed"):
    return {"code": code, "room_id": "100", "status": status,
            "check_in": CI.isoformat(), "check_out": CO.isoformat(),
            "adults": 2, "children": 0, "total": 500000,
            "guest_name": "OTA Guest", "guest_email": "ota@example.com"}


async def test_pull_reservations_blocks_dates(session):
    async with _client(lambda r: httpx.Response(200, json=[_reservation()])) as c:
        result = await sync.pull_reservations(session, c)

    assert result["imported"] == 1
    row = await crud.get_booking_by_lobby_code(session, "LOB1")
    assert row is not None and row.origen == "lobby" and row.estado == "externa"
    # An imported OTA booking makes the dates unavailable on the direct site.
    assert await crud.is_available(session, "DBL-01", CI, CO) is False


async def test_cancelled_reservation_frees_dates(session):
    async with _client(lambda r: httpx.Response(200, json=[_reservation()])) as c:
        await sync.pull_reservations(session, c)
    assert await crud.is_available(session, "DBL-01", CI, CO) is False

    # Same code now cancelled -> the local row is freed.
    async with _client(lambda r: httpx.Response(200, json=[_reservation(status="cancelled")])) as c:
        await sync.pull_reservations(session, c)
    row = await crud.get_booking_by_lobby_code(session, "LOB1")
    assert row.estado == "cancelada"
    assert await crud.is_available(session, "DBL-01", CI, CO) is True


async def test_pull_does_not_overwrite_our_direct_booking(session):
    # A direct booking we already pushed to Lobby, carrying the same code.
    cli = await crud._get_or_create_cliente(session, "Ana", "ana@example.com", "")
    session.add(Reserva(referencia="CG-X", id_cliente=cli.id, id_hab="DBL-01",
                        fecha_in=CI, fecha_fi=CO, n_adultos=2, n_ninos=0,
                        valor=640000, estado="confirmada", origen="directo",
                        lobby_code="DUP"))
    await session.commit()

    async with _client(lambda r: httpx.Response(200, json=[_reservation(code="DUP")])) as c:
        await sync.pull_reservations(session, c)

    row = await crud.get_booking_by_lobby_code(session, "DUP")
    assert row.origen == "directo" and row.estado == "confirmada"  # untouched


async def test_pull_rates_updates_price(session):
    rooms = [{"room_id": "100", "price": 250000, "active": True}]
    async with _client(lambda r: httpx.Response(200, json={"rooms": rooms})) as c:
        result = await sync.pull_rates(session, c)
    assert result["updated"] == 1
    room = await crud.get_room(session, "DBL-01")
    assert room.precio_noche == 250000


async def test_push_booking_idempotent_when_already_synced(session, monkeypatch):
    monkeypatch.setattr(settings, "lobby_api_token", "T")  # lobby_enabled True
    cli = await crud._get_or_create_cliente(session, "Ana", "ana@example.com", "")
    reserva = Reserva(referencia="CG-Y", id_cliente=cli.id, id_hab="DBL-01",
                      fecha_in=CI, fecha_fi=CO, n_adultos=2, n_ninos=0,
                      valor=640000, estado="confirmada", origen="directo",
                      lobby_code="ALREADY")
    session.add(reserva)
    await session.commit()

    # Already has a code -> returns it without any HTTP call.
    assert await sync.push_booking(session, reserva) == "ALREADY"


async def test_push_booking_creates_and_records_code(session, monkeypatch):
    monkeypatch.setattr(settings, "lobby_api_token", "T")
    cli = await crud._get_or_create_cliente(session, "Ana", "ana@example.com", "")
    reserva = Reserva(referencia="CG-Z", id_cliente=cli.id, id_hab="DBL-01",
                      fecha_in=CI, fecha_fi=CO, n_adultos=2, n_ninos=0,
                      valor=640000, estado="confirmada", origen="directo")
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    def handler(request):
        return httpx.Response(200, json={"code": "NEW123"})

    monkeypatch.setattr(sync, "get_client",
                        lambda **kw: _client(handler))
    code = await sync.push_booking(session, reserva)
    assert code == "NEW123"
    refreshed = await session.get(Reserva, reserva.id_res)
    assert refreshed.lobby_code == "NEW123"


async def test_push_booking_disabled_returns_none(session):
    cli = await crud._get_or_create_cliente(session, "Ana", "ana@example.com", "")
    reserva = Reserva(referencia="CG-W", id_cliente=cli.id, id_hab="DBL-01",
                      fecha_in=CI, fecha_fi=CO, n_adultos=2, n_ninos=0,
                      valor=640000, estado="confirmada", origen="directo")
    session.add(reserva)
    await session.commit()
    # lobby_api_token is empty here -> disabled -> no-op.
    assert await sync.push_booking(session, reserva) is None
