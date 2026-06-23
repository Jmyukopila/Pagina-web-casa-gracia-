"""Tests for the Wompi integration: signatures, event parsing and the webhook."""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

import pytest

from app.config import settings
from app.payments import wompi

EVENTS_SECRET = "test_events_secret"


@pytest.fixture
def events_secret(monkeypatch):
    monkeypatch.setattr(settings, "wompi_events_secret", EVENTS_SECRET)
    return EVENTS_SECRET


def _signed_event(*, reference: str, status: str, amount_in_cents: int,
                  secret: str, timestamp: str = "1700000000",
                  tx_id: str = "tx-1") -> dict:
    """Build a Wompi transaction event whose checksum matches `secret`."""
    properties = ["transaction.id", "transaction.status",
                  "transaction.amount_in_cents"]
    values = {"transaction.id": tx_id, "transaction.status": status,
              "transaction.amount_in_cents": str(amount_in_cents)}
    concatenated = "".join(values[p] for p in properties)
    checksum = hashlib.sha256(
        f"{concatenated}{timestamp}{secret}".encode()).hexdigest()
    return {
        "timestamp": timestamp,
        "signature": {"properties": properties, "checksum": checksum},
        "data": {"transaction": {
            "id": tx_id, "reference": reference, "status": status,
            "amount_in_cents": amount_in_cents,
        }},
    }


# --- Pure functions --------------------------------------------------------
def test_integrity_signature_format(monkeypatch):
    monkeypatch.setattr(settings, "wompi_integrity_secret", "int_secret")
    expected = hashlib.sha256(b"CG-1100000COPint_secret").hexdigest()
    assert wompi.integrity_signature("CG-1", 100000, "COP") == expected


def test_verify_event_signature_accepts_valid(events_secret):
    event = _signed_event(reference="CG-1", status="APPROVED",
                          amount_in_cents=100, secret=events_secret)
    assert wompi.verify_event_signature(event) is True


def test_verify_event_signature_rejects_tampered(events_secret):
    event = _signed_event(reference="CG-1", status="APPROVED",
                          amount_in_cents=100, secret="wrong_secret")
    assert wompi.verify_event_signature(event) is False


def test_verify_event_signature_fails_closed_without_secret(monkeypatch):
    monkeypatch.setattr(settings, "wompi_events_secret", "")
    event = _signed_event(reference="CG-1", status="APPROVED",
                          amount_in_cents=100, secret="anything")
    assert wompi.verify_event_signature(event) is False


def test_transaction_from_event():
    event = _signed_event(reference="CG-9", status="approved",
                          amount_in_cents=500, secret="x", tx_id="abc")
    tx = wompi.transaction_from_event(event)
    assert tx == {"id": "abc", "reference": "CG-9",
                  "status": "APPROVED", "amount_in_cents": 500}


# --- Webhook endpoint ------------------------------------------------------
def _booking_payload():
    ci = date.today() + timedelta(days=10)
    co = ci + timedelta(days=2)
    return dict(room_id="DBL-01", guest_name="Ana", guest_email="ana@example.com",
                guest_phone="3001234567", checkin=ci.isoformat(),
                checkout=co.isoformat(), guests=2, notes="")


async def _create_booking(client) -> dict:
    r = await client.post("/api/bookings", json=_booking_payload())
    assert r.status_code == 201
    return r.json()


async def test_webhook_rejects_invalid_signature(client, events_secret):
    booking = await _create_booking(client)
    event = _signed_event(reference=booking["reference"], status="APPROVED",
                          amount_in_cents=booking["amount_cop"] * 100,
                          secret="wrong_secret")
    r = await client.post("/api/wompi/webhook", json=event)
    assert r.status_code == 401


async def test_webhook_approves_matching_payment(client, events_secret):
    booking = await _create_booking(client)
    event = _signed_event(reference=booking["reference"], status="APPROVED",
                          amount_in_cents=booking["amount_cop"] * 100,
                          secret=events_secret)
    r = await client.post("/api/wompi/webhook", json=event)
    assert r.status_code == 200

    refreshed = (await client.get(f"/api/bookings/{booking['reference']}")).json()
    assert refreshed["status"] == "confirmada"


async def test_webhook_rejects_amount_mismatch(client, events_secret):
    booking = await _create_booking(client)
    event = _signed_event(reference=booking["reference"], status="APPROVED",
                          amount_in_cents=booking["amount_cop"] * 100 + 1,
                          secret=events_secret)
    r = await client.post("/api/wompi/webhook", json=event)
    assert r.status_code == 400
