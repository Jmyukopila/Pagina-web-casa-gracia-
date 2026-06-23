"""Token-protected admin area.

Two surfaces, same ADMIN_TOKEN:
- JSON read API under /api/admin/* (for scripts / future tooling).
- A simple HTML dashboard at /admin to review bookings, approve pending
  reviews and work the chatbot escalation queue.

Auth: pass ?token=... once; on success it's stored in an httpOnly cookie so the
dashboard and its action buttons keep working. The default placeholder token is
always rejected. /api/ is disallowed in robots.txt.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..config import settings
from ..database import get_session
from ..deps import is_valid_admin_token as _valid
from ..deps import render

router = APIRouter(prefix="/api/admin", tags=["admin"])
ui_router = APIRouter(prefix="/admin", tags=["admin-ui"])

COOKIE = "cg_admin"


# --- JSON API --------------------------------------------------------------
def _require_token(token: str = Query(default=""),
                   x_admin_token: str = Header(default="")) -> None:
    if not _valid(token or x_admin_token):
        raise HTTPException(status_code=401, detail="No autorizado.")


@router.get("/escalaciones", dependencies=[Depends(_require_token)])
async def api_escalations(pending: bool = Query(default=False),
                          limit: int = Query(default=100, ge=1, le=500),
                          db: AsyncSession = Depends(get_session)):
    rows = await crud.list_escalations(db, pending_only=pending, limit=limit)
    return {
        "count": len(rows),
        "items": [
            {
                "id": e.id, "motivo": e.motivo, "mensaje": e.mensaje,
                "idioma": e.idioma, "contacto": e.contacto, "contexto": e.contexto,
                "atendido": e.atendido,
                "creado_en": e.creado_en.isoformat() if e.creado_en else None,
            }
            for e in rows
        ],
    }


# --- HTML dashboard --------------------------------------------------------
def _token_from(request: Request, token_q: str) -> str:
    return token_q or request.cookies.get(COOKIE, "")


def _require_ui(request: Request, token: str = Query(default="")) -> None:
    if not _valid(_token_from(request, token)):
        raise HTTPException(status_code=401, detail="No autorizado.")


@ui_router.get("")
async def dashboard(request: Request, token: str = Query(default=""),
                    db: AsyncSession = Depends(get_session)):
    tok = _token_from(request, token)
    if not _valid(tok):
        # Show a small login form (flag an error only if a token was attempted).
        return render(request, "admin_login.html", bad=bool(token))

    bookings = await crud.list_recent_bookings(db, 50)
    pending_reviews = await crud.list_pending_reviews(db, 50)
    escalations = await crud.list_escalations(db, pending_only=False, limit=100)
    pending_count = sum(1 for e in escalations if not e.atendido)

    resp = render(request, "admin.html", bookings=bookings,
                  pending_reviews=pending_reviews, escalations=escalations,
                  pending_count=pending_count, lobby_enabled=settings.lobby_enabled)
    if token:  # arrived via ?token= -> remember it (12h, httpOnly).
        resp.set_cookie(COOKIE, tok, httponly=True, samesite="lax",
                        max_age=43200, secure=settings.is_prod)
    return resp


@ui_router.post("/escalaciones/{esc_id}/atender",
                dependencies=[Depends(_require_ui)])
async def attend_escalation(esc_id: int,
                            db: AsyncSession = Depends(get_session)):
    await crud.mark_escalation_attended(db, esc_id)
    return RedirectResponse("/admin", status_code=303)


@ui_router.post("/opiniones/{review_id}/aprobar",
                dependencies=[Depends(_require_ui)])
async def approve_review(review_id: int,
                         db: AsyncSession = Depends(get_session)):
    await crud.approve_review(db, review_id)
    return RedirectResponse("/admin", status_code=303)


@ui_router.post("/lobby/sync", dependencies=[Depends(_require_ui)])
async def lobby_sync_now(db: AsyncSession = Depends(get_session)):
    """Manual 'Sync with Lobby' button on the dashboard (cookie/token auth)."""
    from ..lobby.sync import run_full_sync
    await run_full_sync(db)
    return RedirectResponse("/admin", status_code=303)


@ui_router.get("/salir")
async def logout():
    resp = RedirectResponse("/admin", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp
