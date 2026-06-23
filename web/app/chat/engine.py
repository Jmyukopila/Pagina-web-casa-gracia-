"""LLM engine: OpenAI-compatible async clients with failover and a tool loop.

STATELESS conversation (the browser sends prior turns), but tools may read the
live database, so it runs fully async on the request's event loop and receives
the DB session + the site's base URL from the router.
"""
from __future__ import annotations

import json
import logging
import re

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from .prompts import system_prompt
from .tools import TOOLS_SCHEMA, run_tool

log = logging.getLogger("casagracia.chat")

MAX_TOOL_ROUNDS = 4
_CHAIN: list[dict] | None = None

# Some models emit tool calls as text, e.g. <function=escalate_to_human>{...}</function>.
_TEXT_TOOL_RE = re.compile(r"<function=([a-zA-Z_]\w*)>\s*(\{.*?\})?\s*(?:</function>)?", re.DOTALL)


def _get_chain() -> list[dict]:
    global _CHAIN
    if _CHAIN is None:
        _CHAIN = [
            {"provider": prov, "model": model,
             "client": AsyncOpenAI(base_url=base_url, api_key=key or "none", timeout=22.0)}
            for (prov, base_url, key, model) in settings.llm_chain()
        ]
    return _CHAIN


async def _clean_leaked_tools(content: str, db: AsyncSession,
                              user_text: str = "", context: str = "",
                              thread_id: str | None = None) -> str:
    if "<function=" not in content:
        return content
    for name, raw_args in _TEXT_TOOL_RE.findall(content):
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            args = {}
        await run_tool(name, args, db, user_text=user_text, context=context,
                       thread_id=thread_id)  # side effect only
    return _TEXT_TOOL_RE.sub("", content).strip()


async def _complete(messages: list[dict]):
    chain = _get_chain()
    if not chain:
        raise RuntimeError("No LLM provider configured (missing API keys).")
    last_error = None
    for node in chain:
        try:
            resp = await node["client"].chat.completions.create(
                model=node["model"], messages=messages,
                tools=TOOLS_SCHEMA, temperature=0.3,
            )
            return resp.choices[0].message
        except (RateLimitError, APIConnectionError) as e:
            last_error = e
            log.warning("LLM %s unavailable (%s); trying next.", node["provider"], type(e).__name__)
        except APIError as e:
            last_error = e
            log.warning("LLM %s error: %s; trying next.", node["provider"], e)
    raise RuntimeError(f"All LLM providers failed: {last_error}")


async def generate_reply(db: AsyncSession, history: list[dict], user_text: str,
                         lang: str = "es", thread_id: str | None = None) -> str:
    """Reply to user_text given prior turns (each {'role','content'}).

    `lang` ("es"/"en") is the page language and fixes the reply language.
    `thread_id` (browser conversation id) is stored on any escalation so a human
    can reply into this widget. Stateless on memory; reads the live DB via tools."""
    messages: list[dict] = [{"role": "system", "content": system_prompt(lang)}]
    recent: list[str] = []
    for m in history[-settings.llm_history_limit:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
            recent.append(f"{role}: {content}")
    messages.append({"role": "user", "content": user_text})

    # Short transcript passed to tools (e.g. so an escalation is logged with context).
    context = "\n".join([*recent[-6:], f"user: {user_text}"])[:3000]

    for _ in range(MAX_TOOL_ROUNDS):
        msg = await _complete(messages)
        if not msg.tool_calls:
            reply = (await _clean_leaked_tools(msg.content or "", db,
                                               user_text, context,
                                               thread_id)).strip()
            if reply:
                return reply
            return ("Sorry, could you say that again?" if lang == "en"
                    else "Disculpa, ¿puedes repetirlo?")
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": await run_tool(tc.function.name, args, db,
                                          user_text=user_text, context=context,
                                          thread_id=thread_id),
            })

    return ("I'm having trouble completing that. I'd recommend messaging reception on WhatsApp."
            if lang == "en"
            else "Estoy teniendo un problema para completar eso. Te recomiendo escribir a recepción por WhatsApp.")
