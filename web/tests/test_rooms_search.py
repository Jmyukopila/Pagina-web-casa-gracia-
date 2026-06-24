"""Date-range search on /habitaciones: shows only available rooms."""
from __future__ import annotations

from datetime import date, timedelta

from app import crud
from tests.conftest import make_booking_data


async def test_no_dates_lists_all_rooms(client):
    r = await client.get("/habitaciones")
    assert r.status_code == 200
    assert "/habitaciones/DBL-01" in r.text
    assert "results-bar" not in r.text  # not in search mode


async def test_search_free_dates_shows_room(client):
    ci = (date.today() + timedelta(days=30)).isoformat()
    co = (date.today() + timedelta(days=32)).isoformat()
    r = await client.get(f"/habitaciones?checkin={ci}&checkout={co}")
    assert r.status_code == 200
    assert "results-bar" in r.text
    # the room link carries the searched dates through to the detail page
    # (& is HTML-escaped to &amp; in the href, so check the path + first param)
    assert f"/habitaciones/DBL-01?checkin={ci}" in r.text
    assert f"checkout={co}" in r.text


async def test_search_hides_unavailable_room(client, session):
    data = make_booking_data()  # blocks DBL-01 for today+10..+12
    room = await crud.get_room(session, "DBL-01")
    await crud.create_booking(session, room, data)

    r = await client.get(
        f"/habitaciones?checkin={data.checkin}&checkout={data.checkout}")
    assert r.status_code == 200
    assert "/habitaciones/DBL-01" not in r.text   # blocked -> not listed
    assert "empty-state" in r.text                 # friendly no-availability


async def test_search_filters_by_guest_capacity(client):
    ci = (date.today() + timedelta(days=30)).isoformat()
    co = (date.today() + timedelta(days=32)).isoformat()
    # DBL-01 holds max 2 guests -> excluded when asking for 5.
    r = await client.get(f"/habitaciones?checkin={ci}&checkout={co}&guests=5")
    assert "/habitaciones/DBL-01" not in r.text


async def test_invalid_dates_fall_back_to_all(client):
    # Past dates are ignored -> full list, no search bar.
    r = await client.get("/habitaciones?checkin=2020-01-01&checkout=2020-01-03")
    assert r.status_code == 200
    assert "/habitaciones/DBL-01" in r.text
    assert "results-bar" not in r.text
