"""Tests for the booking/hold logic in app.crud."""
from __future__ import annotations

from datetime import date, timedelta

from app import crud
from app.models import Reserva
from tests.conftest import make_booking_data


async def _room(session):
    return await crud.get_room(session, "DBL-01")


async def test_empty_room_is_available(session):
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    assert await crud.is_available(session, "DBL-01", ci, co) is True


async def test_create_booking_sets_reference_and_total(session):
    room = await _room(session)
    data = make_booking_data()
    booking = await crud.create_booking(session, room, data)

    assert booking.reference.startswith("CG-")
    assert booking.estado == "pendiente"
    # 2 nights * 320000
    assert booking.amount_cop == 2 * 320000
    assert booking.hold_expira is not None


async def test_booking_blocks_overlapping_dates(session):
    room = await _room(session)
    data = make_booking_data()
    await crud.create_booking(session, room, data)

    # Overlaps the held range -> not available.
    assert await crud.is_available(session, "DBL-01", data.checkin,
                                   data.checkout) is False
    # A range starting on the checkout day is free (checkout is exclusive).
    assert await crud.is_available(session, "DBL-01", data.checkout,
                                   data.checkout + timedelta(days=2)) is True


async def test_expired_hold_is_released_and_frees_dates(session):
    room = await _room(session)
    data = make_booking_data()
    booking = await crud.create_booking(session, room, data)

    # Force the hold into the past, as if the 20-minute window elapsed.
    booking.hold_expira = crud._utcnow() - timedelta(minutes=1)
    await session.commit()

    # While still 'pendiente' but expired, availability already ignores it.
    assert await crud.is_available(session, "DBL-01", data.checkin,
                                   data.checkout) is True

    freed = await crud.release_expired_holds(session)
    assert freed == 1
    refreshed = await session.get(Reserva, booking.id_res)
    assert refreshed.estado == "expirada"


async def test_confirmed_booking_blocks_even_without_hold(session):
    room = await _room(session)
    booking = await crud.create_booking(session, room, make_booking_data())
    await crud.set_booking_status(session, booking.reference, "confirmada")

    # Confirmed bookings have no hold_expira but must still block the dates.
    assert await crud.is_available(session, "DBL-01", booking.checkin,
                                   booking.checkout) is False
