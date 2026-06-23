"""Tests for the JSON API HTTP layer (app.routers.api) via an ASGI client."""
from __future__ import annotations

from datetime import date, timedelta


def _dates(offset_days: int = 10, nights: int = 2):
    ci = date.today() + timedelta(days=offset_days)
    co = ci + timedelta(days=nights)
    return ci.isoformat(), co.isoformat()


def _booking_payload(**over):
    ci, co = _dates()
    body = dict(
        room_id="DBL-01", guest_name="Ana Pérez", guest_email="ana@example.com",
        guest_phone="3001234567", checkin=ci, checkout=co, guests=2, notes="",
    )
    body.update(over)
    return body


# --- Rooms -----------------------------------------------------------------
async def test_list_rooms(client):
    r = await client.get("/api/rooms")
    assert r.status_code == 200
    rooms = r.json()["rooms"]
    assert [room["id"] for room in rooms] == ["DBL-01"]


async def test_get_room_ok_and_404(client):
    assert (await client.get("/api/rooms/DBL-01")).status_code == 200
    assert (await client.get("/api/rooms/NOPE")).status_code == 404


# --- Availability ----------------------------------------------------------
async def test_availability_rejects_checkout_before_checkin(client):
    ci, _ = _dates()
    r = await client.get("/api/availability",
                         params={"room_id": "DBL-01", "checkin": ci, "checkout": ci})
    assert r.status_code == 400


async def test_availability_rejects_past_checkin(client):
    past = (date.today() - timedelta(days=1)).isoformat()
    future = (date.today() + timedelta(days=3)).isoformat()
    r = await client.get("/api/availability",
                         params={"room_id": "DBL-01", "checkin": past, "checkout": future})
    assert r.status_code == 400


async def test_availability_reflects_bookings(client):
    ci, co = _dates()
    params = {"room_id": "DBL-01", "checkin": ci, "checkout": co}

    r = await client.get("/api/availability", params=params)
    assert r.status_code == 200 and r.json()["available"] is True

    assert (await client.post("/api/bookings", json=_booking_payload())).status_code == 201

    r = await client.get("/api/availability", params=params)
    assert r.json()["available"] is False


# --- Bookings --------------------------------------------------------------
async def test_create_booking_ok(client):
    r = await client.post("/api/bookings", json=_booking_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["reference"].startswith("CG-")
    assert body["status"] == "pendiente"
    assert body["amount_cop"] == 2 * 320000


async def test_create_booking_unknown_room(client):
    r = await client.post("/api/bookings", json=_booking_payload(room_id="NOPE"))
    assert r.status_code == 404


async def test_create_booking_too_many_guests(client):
    r = await client.post("/api/bookings", json=_booking_payload(guests=5))
    assert r.status_code == 400


async def test_create_booking_conflict_on_overlap(client):
    assert (await client.post("/api/bookings", json=_booking_payload())).status_code == 201
    r = await client.post("/api/bookings", json=_booking_payload())
    assert r.status_code == 409


async def test_get_booking_by_reference(client):
    created = (await client.post("/api/bookings", json=_booking_payload())).json()
    ref = created["reference"]
    assert (await client.get(f"/api/bookings/{ref}")).status_code == 200
    assert (await client.get("/api/bookings/CG-000000-XXXXXX")).status_code == 404
