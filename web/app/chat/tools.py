"""Tools the model can call: hotel info, live availability, and escalation.

`check_availability` reads the real Supabase data through the crud layer, so the
bot quotes actual rooms and prices and hands the guest a pre-filled booking link
(the actual reservation + payment still happen on the website's /reservar flow).
"""
from __future__ import annotations

import json
import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, i18n
from ..config import settings
from .knowledge import hotel_info
from .prefilter import detect_lang

log = logging.getLogger("casagracia.chat")

MAX_STAY_NIGHTS = 60
MAX_GUESTS = 10

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_hotel_info",
            "description": ("Devuelve la información detallada del hotel (servicios, horarios, "
                            "desayuno, parqueadero, traslados, políticas, ubicación, habitaciones, "
                            "cómo reservar). Úsala para responder dudas concretas del cliente."),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": ("Consulta habitaciones REALMENTE disponibles y su precio para un rango "
                            "de fechas, desde la base de datos del hotel. Úsala siempre que el "
                            "cliente pregunte por disponibilidad, precios o quiera reservar."),
            "parameters": {
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "description": "Fecha de entrada YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "Fecha de salida YYYY-MM-DD"},
                    "guests": {"type": "integer", "description": "Número de huéspedes", "default": 2},
                },
                "required": ["check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": ("Deriva la conversación a recepción (quejas, cambios o cancelaciones de "
                            "reserva, dudas que no puedes resolver). ANTES de llamarla, pregunta al "
                            "cliente cómo prefiere que recepción le responda (WhatsApp o correo) y pide "
                            "ese dato de contacto. Llama a esta función SOLO cuando ya tengas el canal "
                            "y el contacto; el sistema los guarda para que recepción le escriba."),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Motivo breve del escalado"},
                    "channel": {"type": "string", "enum": ["whatsapp", "correo"],
                                "description": "Canal elegido por el cliente para que le respondan."},
                    "contact": {"type": "string",
                                "description": "Número de WhatsApp o correo del cliente (según el canal)."},
                },
                "required": ["reason", "channel", "contact"],
            },
        },
    },
]


_CHANNEL_LABEL = {"whatsapp": "WhatsApp", "correo": "correo",
                  "email": "correo", "wa": "WhatsApp"}


def _norm_channel(channel: str | None) -> str | None:
    if not channel:
        return None
    c = channel.strip().lower()
    if c in ("whatsapp", "wa", "wsp", "ws"):
        return "whatsapp"
    if c in ("correo", "email", "mail", "e-mail"):
        return "correo"
    return None


def _usd(cop: int) -> int:
    return round((cop or 0) / settings.usd_to_cop) if settings.usd_to_cop else 0


def _validate(check_in: str, check_out: str, guests: int):
    try:
        ci = date.fromisoformat(check_in)
        co = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return None, "Las fechas deben tener formato YYYY-MM-DD."
    if ci < date.today():
        return None, "La fecha de entrada no puede ser una fecha pasada."
    if co <= ci:
        return None, "La fecha de salida debe ser posterior a la de entrada."
    if (co - ci).days > MAX_STAY_NIGHTS:
        return None, f"La estancia no puede superar {MAX_STAY_NIGHTS} noches; contacta con recepción."
    if not isinstance(guests, int) or guests < 1:
        return None, "El número de huéspedes debe ser al menos 1."
    if guests > MAX_GUESTS:
        return None, f"Para más de {MAX_GUESTS} huéspedes, contacta con recepción."
    return (ci, co), None


async def _check_availability(db: AsyncSession, check_in: str, check_out: str,
                              guests: int) -> dict:
    parsed, err = _validate(check_in, check_out, guests)
    if err:
        return {"error": err}
    ci, co = parsed
    nights = (co - ci).days
    options = []
    for r in await crud.list_rooms(db):
        if r.ca_max < guests:
            continue
        if not await crud.is_available(db, r.id_hab, ci, co):
            continue
        per_night = r.precio_noche
        total = per_night * nights
        options.append({
            "room_id": r.id_hab,
            "name_es": r.nom_hab,
            "name_en": i18n.ROOM_EN.get(r.id_hab, {}).get("name", r.nom_hab),
            "capacity": r.ca_max,
            "price_per_night": {"cop": per_night, "usd": _usd(per_night)},
            "total_price": {"cop": total, "usd": _usd(total)},
            # Relative, short link (same-origin). The widget makes it clickable.
            "book_url": f"/reservar?room={r.id_hab}&checkin={check_in}"
                        f"&checkout={check_out}&guests={guests}",
        })
    return {
        "nights": nights,
        "guests": guests,
        "currency_note": "Precios en COP con equivalente aproximado en USD (cambio referencial).",
        "available_count": len(options),
        "options": options,
    }


async def _escalate(db: AsyncSession, reason: str, user_text: str,
                    context: str, channel: str | None = None,
                    contact: str | None = None,
                    thread_id: str | None = None) -> dict:
    # Persist the hand-off so reception never loses it. Never let a DB hiccup
    # break the chat reply.
    canal = _norm_channel(channel)
    # Prefer the contact the guest explicitly gave; fall back to scanning text.
    contacto = (contact or "").strip() or crud.extract_contact(
        f"{user_text or ''} {context or ''}")
    try:
        lang = detect_lang((user_text or context or "").lower())
        await crud.create_escalation(
            db, motivo=reason, mensaje=(user_text or None), idioma=lang,
            contexto=(context or None), contacto=(contacto or None),
            canal=canal, thread_id=thread_id,
        )
    except Exception:
        log.exception("Could not persist chatbot escalation")
    label = _CHANNEL_LABEL.get(canal or "", "")
    return {
        "ok": True,
        "channel": canal,
        "contact_saved": contacto or None,
        "message": (
            f"Listo: recepción recibirá la solicitud y le escribirá al cliente por "
            f"{label} a {contacto}. Confírmaselo con amabilidad." if canal and contacto
            else "Falta el canal (WhatsApp o correo) o el dato de contacto del cliente. "
                 "Pídeselo antes de escalar."
        ),
        "reason": reason,
    }


def _as_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _missing(args: dict, required: list[str]) -> str | None:
    faltan = [k for k in required if args.get(k) in (None, "")]
    return ("Faltan datos para esta acción: " + ", ".join(faltan) +
            ". Pídeselos al cliente.") if faltan else None


async def run_tool(name: str, args: dict, db: AsyncSession,
                   user_text: str = "", context: str = "",
                   thread_id: str | None = None) -> str:
    """Execute a tool and return its JSON-serialized result. Never raises."""
    if not isinstance(args, dict):
        args = {}
    if name == "get_hotel_info":
        out = {"hotel_info": hotel_info()}
    elif name == "check_availability":
        err = _missing(args, ["check_in", "check_out"])
        out = ({"error": err} if err else
               await _check_availability(db, args["check_in"], args["check_out"],
                                         _as_int(args.get("guests"), 2)))
    elif name == "escalate_to_human":
        out = await _escalate(db, args.get("reason", "Sin especificar"),
                              user_text, context,
                              channel=args.get("channel"),
                              contact=args.get("contact"),
                              thread_id=thread_id)
    else:
        out = {"error": f"Herramienta desconocida: {name}"}
    return json.dumps(out, ensure_ascii=False)
