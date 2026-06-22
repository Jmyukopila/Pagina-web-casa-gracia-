"""
Wompi integration (Colombia).

Two pieces:
1. integrity_signature() -> the SHA-256 signature the Web Checkout widget needs
   so Wompi trusts the amount/reference you send.
       signature = SHA256(reference + amount_in_cents + currency + integrity_secret)
2. verify_event_signature() -> validate the webhook Wompi calls when a
   transaction changes state, so nobody can fake a "payment approved".
       checksum = SHA256(concat(values at signature.properties) + timestamp + events_secret)

Docs: https://docs.wompi.co/  (Eventos / Firma de integridad)
No card data ever touches this server -- Wompi handles it.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

from ..config import settings


def integrity_signature(reference: str, amount_in_cents: int,
                        currency: str | None = None) -> str:
    currency = currency or settings.currency
    raw = f"{reference}{amount_in_cents}{currency}{settings.wompi_integrity_secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def checkout_context(booking) -> dict[str, Any]:
    """Everything the front-end widget template needs for a booking."""
    amount_in_cents = booking.amount_cop * 100
    reference = booking.reference
    return {
        "public_key": settings.wompi_public_key,
        "currency": settings.currency,
        "amount_in_cents": amount_in_cents,
        "reference": reference,
        "signature": integrity_signature(reference, amount_in_cents),
        "redirect_url": f"{settings.base_url}/reserva/{reference}/resultado",
        "checkout_base": settings.wompi_base_checkout,
    }


def _dig(data: dict, dotted: str) -> str:
    cur: Any = data
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return ""
    return "" if cur is None else str(cur)


def verify_event_signature(payload: dict) -> bool:
    """Return True if the webhook body is genuinely from Wompi."""
    if not settings.wompi_events_secret:
        # No secret configured -> cannot verify; refuse (fail closed).
        return False
    sig = payload.get("signature") or {}
    properties = sig.get("properties") or []
    checksum = sig.get("checksum") or ""
    timestamp = payload.get("timestamp", "")
    data = payload.get("data") or {}

    concatenated = "".join(_dig(data, p) for p in properties)
    raw = f"{concatenated}{timestamp}{settings.wompi_events_secret}"
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    # constant-time compare
    return hmac.compare_digest(expected, checksum.lower())


def transaction_from_event(payload: dict) -> dict:
    """Pull the bits we care about from a Wompi transaction.updated event."""
    tx = (payload.get("data") or {}).get("transaction") or {}
    return {
        "id": tx.get("id", ""),
        "reference": tx.get("reference", ""),
        "status": (tx.get("status") or "").upper(),   # APPROVED / DECLINED / VOIDED / ERROR
        "amount_in_cents": tx.get("amount_in_cents"),
    }
