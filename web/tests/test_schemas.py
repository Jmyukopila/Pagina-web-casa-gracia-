"""Tests for the booking schema validators (date bounds, stay length)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas import MAX_NIGHTS, BookingCreate
from tests.conftest import make_booking_data


def test_valid_booking_passes():
    data = make_booking_data()
    assert data.checkout > data.checkin


def test_rejects_past_checkin():
    with pytest.raises(ValidationError):
        make_booking_data(checkin=date.today() - timedelta(days=1),
                          checkout=date.today() + timedelta(days=1))


def test_rejects_checkout_before_or_equal_checkin():
    ci = date.today() + timedelta(days=5)
    with pytest.raises(ValidationError):
        make_booking_data(checkin=ci, checkout=ci)


def test_rejects_stay_over_max_nights():
    ci = date.today() + timedelta(days=5)
    with pytest.raises(ValidationError):
        make_booking_data(checkin=ci, checkout=ci + timedelta(days=MAX_NIGHTS + 1))


def test_accepts_stay_at_max_nights():
    ci = date.today() + timedelta(days=5)
    data = make_booking_data(checkin=ci, checkout=ci + timedelta(days=MAX_NIGHTS))
    assert isinstance(data, BookingCreate)
