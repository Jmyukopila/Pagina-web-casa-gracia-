"""Wompi webhook + admin review approval."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..database import get_session
from ..deps import is_valid_admin_token
from ..payments import wompi

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/wompi/webhook")
async def wompi_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    """
    Wompi calls this when a transaction changes state. We verify the signature,
    then move the matching booking to confirmed/cancelled. This is the source
    of truth for payment status (never trust the browser redirect alone).
    """
    payload = await request.json()
    if not wompi.verify_event_signature(payload):
        raise HTTPException(status_code=401, detail="Invalid signature")

    tx = wompi.transaction_from_event(payload)
    reference = tx["reference"]
    if not reference:
        return {"ok": True, "ignored": "no reference"}

    booking = await crud.get_booking(db, reference)
    if not booking:
        return {"ok": True, "ignored": "unknown reference"}

    if tx["status"] == "APPROVED":
        # Defensive: confirm the paid amount matches what we expected.
        if tx["amount_in_cents"] and int(tx["amount_in_cents"]) != booking.amount_cents:
            raise HTTPException(status_code=400, detail="Amount mismatch")
        confirmed = await crud.set_booking_status(db, reference, "confirmada", tx["id"])
        # Push the confirmed direct booking to Lobby so it blocks every channel
        # (no-op if Lobby is disabled or it was already pushed).
        if confirmed is not None:
            from ..lobby.sync import push_booking
            await push_booking(db, confirmed)
    elif tx["status"] in {"DECLINED", "VOIDED", "ERROR"}:
        await crud.set_booking_status(db, reference, "cancelada", tx["id"])

    return {"ok": True, "reference": reference, "status": tx["status"]}


@router.post("/reviews/{review_id}/approve")
async def approve_review(review_id: int, x_admin_token: str = Header(default=""),
                        db: AsyncSession = Depends(get_session)):
    if not is_valid_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="Forbidden")
    ok = await crud.approve_review(db, review_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"ok": True, "approved": review_id}
