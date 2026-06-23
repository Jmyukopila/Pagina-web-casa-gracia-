"""Tests for admin crud helpers (escalation queue, pending reviews, bookings)."""
from __future__ import annotations

from app import crud
from app.schemas import ReviewCreate
from tests.conftest import make_booking_data


async def test_mark_escalation_attended(session):
    esc = await crud.create_escalation(session, motivo="x")
    assert (await crud.list_escalations(session, pending_only=True))[0].id == esc.id

    ok = await crud.mark_escalation_attended(session, esc.id)
    assert ok is True
    assert await crud.list_escalations(session, pending_only=True) == []
    assert await crud.mark_escalation_attended(session, 999999) is False


async def test_list_pending_reviews(session):
    await crud.create_review(
        session, ReviewCreate(author="Luisa", rating=5, body="Excelente estadía"),
        auto_approve=False)
    await crud.create_review(
        session, ReviewCreate(author="Pedro", rating=4, body="Muy bien todo"),
        auto_approve=True)

    pending = await crud.list_pending_reviews(session)
    assert len(pending) == 1
    assert pending[0].autor == "Luisa"


async def test_list_recent_bookings(session):
    room = await crud.get_room(session, "DBL-01")
    await crud.create_booking(session, room, make_booking_data())
    bookings = await crud.list_recent_bookings(session, limit=10)
    assert len(bookings) == 1
    assert bookings[0].referencia.startswith("CG-")
