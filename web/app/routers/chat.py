"""Same-origin chatbot endpoint: POST /api/chat.

Stateless on memory — the browser sends prior turns with each message. Tries the
0-token FAQ pre-filter first, then the async LLM engine, which can read live
availability/prices from the database. Always returns a friendly reply.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..chat import engine
from ..chat.prefilter import detect_lang, quick_answer
from ..config import settings
from ..database import get_session
from ..deps import rate_limit
from ..schemas import ChatRequest

log = logging.getLogger("casagracia.chat")
router = APIRouter(prefix="/api", tags=["chat"])

_WA = f"https://wa.me/{settings.hotel_whatsapp}" if settings.hotel_whatsapp else ""


def _fallback(text: str) -> str:
    """Friendly bilingual message when the AI can't answer right now."""
    if detect_lang(text.lower()) == "en":
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
    text = payload.message.strip()
    if not text:
        return {"reply": "¿En qué puedo ayudarte?", "source": "empty"}

    # 1) Fixed FAQ answers (0 tokens).
    canned = quick_answer(text)
    if canned is not None:
        return {"reply": canned, "source": "faq"}

    # 2) LLM (only if a provider is configured).
    if not settings.chat_enabled:
        return {"reply": _fallback(text), "source": "disabled"}
    try:
        history = [t.model_dump() for t in payload.history]
        reply = await engine.generate_reply(db, history, text)
    except Exception:
        log.exception("Chat generation failed")
        reply = _fallback(text)
    return {"reply": reply, "source": "ai"}
