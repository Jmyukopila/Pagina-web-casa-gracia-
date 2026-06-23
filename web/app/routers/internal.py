"""Internal endpoints triggered by infrastructure, not users.

`/internal/lobby/sync` is hit by a Vercel Cron job (and can be called manually)
to pull OTA reservations + rates from Lobby. It is protected by a shared secret
(`LOBBY_SYNC_SECRET`), accepted as a Bearer token — Vercel adds
`Authorization: Bearer <CRON_SECRET>` to cron requests automatically — or via an
`X-Sync-Secret` header / `?secret=` query for manual calls.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_session
from ..lobby.sync import run_full_sync

router = APIRouter(prefix="/internal", tags=["internal"])


def _provided_secret(request: Request, query_secret: str,
                     header_secret: str) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return header_secret or query_secret


def _require_sync_secret(request: Request, secret: str = Query(default=""),
                         x_sync_secret: str = Header(default="")) -> None:
    expected = settings.lobby_sync_secret
    provided = _provided_secret(request, secret, x_sync_secret)
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="No autorizado.")


@router.api_route("/lobby/sync", methods=["GET", "POST"],
                  dependencies=[Depends(_require_sync_secret)])
async def lobby_sync(db: AsyncSession = Depends(get_session)):
    # GET for Vercel Cron, POST for manual/scripted triggers.
    return await run_full_sync(db)
