"""Same-origin chatbot endpoint: POST /api/chat.

Stateless on memory — the browser sends prior turns with each message. Tries the
0-token FAQ pre-filter first, then the async LLM engine, which can read live
availability/prices from the database. Always returns a friendly reply.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..chat import engine
from ..chat.prefilter import detect_lang, quick_answer
from ..config import settings
from ..database import get_session
from ..deps import rate_limit
from ..schemas import ChatRequest

log = logging.getLogger("casagracia.chat")
router = APIRouter(prefix="/api", tags=["chat"])

_WA = f"https://wa.me/{settings.hotel_whatsapp}" if settings.hotel_whatsapp else ""


def _fallback(text: str, lang: str | None = None) -> str:
    """Friendly message when the AI can't answer right now.

    Uses the page `lang` when given; otherwise detects from the message."""
    use_lang = lang if lang in ("es", "en") else detect_lang(text.lower())
    if use_lang == "en":
        msg = "Sorry, I can't answer automatically right now."
        if _WA:
            msg += f" You can reach reception on WhatsApp: {_WA}"
        return msg
    msg = "Disculpa, ahora mismo no puedo responderte automáticamente."
    if _WA:
        msg += f" Puedes escribir a recepción por WhatsApp: {_WA}"
    return msg


@router.post("/chat")
async def chat(request: Request, payload: ChatRequest,
               db: AsyncSession = Depends(get_session)):
    await rate_limit(request, max_per_minute=20)
    lang = payload.lang  # page language ("es"/"en"), already normalized
    text = payload.message.strip()
    if not text:
        empty = "How can I help you?" if lang == "en" else "¿En qué puedo ayudarte?"
        return {"reply": empty, "source": "empty"}

    # 1) Fixed FAQ answers (0 tokens), in the page language.
    canned = quick_answer(text, lang=lang)
    if canned is not None:
        return {"reply": canned, "source": "faq"}

    # 2) LLM (only if a provider is configured).
    if not settings.chat_enabled:
        return {"reply": _fallback(text, lang), "source": "disabled"}
    try:
        history = [t.model_dump() for t in payload.history]
        reply = await engine.generate_reply(db, history, text, lang=lang,
                                             thread_id=payload.thread_id)
    except Exception:
        log.exception("Chat generation failed")
        reply = _fallback(text, lang)
    return {"reply": reply, "source": "ai"}


@router.get("/chat/replies")
async def chat_replies(request: Request,
                       thread: str = "",
                       after: int = 0,
                       db: AsyncSession = Depends(get_session)):
    """Live human replies for a chat thread (polled by the widget).

    Auth is the unguessable `thread` UUID itself; only that thread's replies are
    returned. Fails soft (empty list) so the widget never breaks."""
    await rate_limit(request, max_per_minute=40)
    thread = (thread or "").strip()[:40]
    if not thread:
        return {"replies": [], "cursor": after}
    try:
        rows = await crud.list_chat_replies(db, thread, after_id=max(after, 0))
    except Exception:
        log.exception("Chat replies poll failed")
        return {"replies": [], "cursor": after}
    cursor = rows[-1].id if rows else after
    return {"replies": [{"id": r.id, "text": r.texto} for r in rows],
            "cursor": cursor}
