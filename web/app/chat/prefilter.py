"""Pre-filter WITHOUT AI: answer obvious messages with fixed text (0 tokens).

Greetings, thanks and typical FAQs (wifi, parking, check-in...) never reach the
model. Rules live in data/quick_replies.json so the hotel controls the answers.
Bilingual: detects Spanish vs English and replies in that language.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_NONWORD = re.compile(r"[^a-z0-9 ]")

RULES_PATH = Path(__file__).resolve().parent / "data" / "quick_replies.json"

# Words that strongly signal each language (lightweight detection, no libraries).
# Includes the FAQ vocabulary of quick_replies.json so short keyword questions
# ("laundry", "iron", "safe"...) are detected reliably instead of defaulting to
# Spanish. Terms that are identical in both languages (wifi, tv, internet) live
# in BOTH sets so they don't bias detection either way.
_NEUTRAL = {"wifi", "internet", "tv", "minibar"}
_EN_WORDS = {
    "the", "you", "your", "do", "does", "did", "have", "has", "is", "are", "was",
    "were", "what", "where", "when", "how", "why", "which", "can", "could",
    "would", "i", "my", "we", "to", "with", "please", "for", "of", "and", "there",
    "this", "that", "about", "from", "hi", "hello", "hey", "good", "morning",
    "afternoon", "evening", "thanks", "thank", "want", "need", "looking",
    "available", "included", "they", "it",
    "parking", "park", "garage", "car", "vehicle", "pool", "swimming", "rooftop",
    "terrace", "breakfast", "airport", "beach", "beaches", "room", "rooms",
    "price", "prices", "rate", "rates", "booking", "book", "reserve",
    "reservation", "night", "nights", "availability", "smoking", "smoke",
    "transfer", "shuttle", "pickup", "arrival", "departure", "checkin",
    "checkout", "reception", "late", "early", "pet", "pets", "dog", "dogs",
    "cat", "cats", "children", "child", "kids", "kid", "baby", "crib", "family",
    "currency", "dollars", "dollar", "payment", "pay", "card", "cards", "credit",
    "debit", "cash", "cancel", "cancellation", "refund", "luggage", "bags",
    "baggage", "store", "safe", "valuables", "lockbox", "laundry", "wash",
    "washing", "iron", "ironing", "password", "air", "conditioning", "fridge",
    "visitor", "visitors", "languages", "language", "english", "spanish",
    "location", "address", "neighborhood", *_NEUTRAL,
}
_ES_WORDS = {
    "hola", "buenas", "buenos", "dias", "tardes", "noches", "que", "cual",
    "como", "donde", "cuando", "cuanto", "cuanta", "cuantas", "cuantos",
    "tienen", "tiene", "tienes", "hay", "los", "las", "del", "para", "por",
    "con", "gracias", "quiero", "quisiera", "necesito", "puedo", "puede",
    "pueden", "esta", "estan", "estoy", "estamos", "son", "soy", "mi", "su",
    "sus", "tus", "busco", "el", "la", "un", "una", "unos", "unas", "de", "en",
    "y", "si", "muy", "tengo", "se",
    "habitacion", "habitaciones", "precio", "precios", "tarifa", "tarifas",
    "desayuno", "parqueadero", "estacionamiento", "parqueo", "garaje",
    "vehiculo", "carro", "piscina", "terraza", "noche", "disponible",
    "disponibilidad", "reservar", "reserva", "playa", "aeropuerto", "traslado",
    "recogida", "llegada", "salida", "entrada", "recepcion", "ubicacion",
    "direccion", "barrio", "moneda", "pesos", "dolares", "fumar", "idioma",
    "idiomas", "mascota", "mascotas", "perro", "perros", "gato", "nino",
    "ninos", "nina", "ninas", "menores", "bebe", "cuna", "familia", "pago",
    "pagar", "tarjeta", "credito", "debito", "efectivo", "cancelar",
    "cancelacion", "reembolso", "equipaje", "maletas", "consigna", "caja",
    "fuerte", "valores", "lavanderia", "lavar", "lavado", "plancha", "planchar",
    "clave", "contrasena", "aire", "acondicionado", "ventilador", "nevera",
    "visita", "visitas", "invitado", "invitados", *_NEUTRAL,
}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def detect_lang(norm_text: str) -> str:
    words = set(norm_text.replace("?", " ").replace("!", " ").replace(",", " ").split())
    return "en" if len(words & _EN_WORDS) > len(words & _ES_WORDS) else "es"


@lru_cache(maxsize=1)
def _data() -> dict:
    if RULES_PATH.exists():
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return {}


def _tokens(norm_text: str) -> list[str]:
    """Words of the normalized text, with punctuation stripped."""
    return _NONWORD.sub(" ", norm_text).split()


def _match(wordset: set[str], joined: str, keywords: list[str]) -> bool:
    """Single-word keywords match whole words (so 'hi' doesn't hit 'children');
    multi-word keywords match as a phrase substring."""
    for k in keywords:
        nk = _NONWORD.sub(" ", _normalize(k)).strip()
        if not nk:
            continue
        if " " in nk:
            if nk in joined:
                return True
        elif nk in wordset:
            return True
    return False


def _pick(answer, lang: str) -> str:
    if isinstance(answer, dict):
        return answer.get(lang) or answer.get("es") or next(iter(answer.values()), "")
    return answer


def quick_answer(user_text: str, lang: str | None = None) -> str | None:
    """Fixed reply if the message matches a rule, else None.

    If `lang` ("es"/"en") is given (the page language), the answer is returned in
    that language; otherwise it falls back to keyword detection on the message."""
    data = _data()
    if not data:
        return None
    norm = _normalize(user_text)
    tokens = _tokens(norm)
    wordset = set(tokens)
    joined = " ".join(tokens)
    lang = lang if lang in ("es", "en") else detect_lang(norm)

    for key in ("greetings", "thanks"):
        block = data.get(key)
        if block and len(tokens) <= 4 and _match(wordset, joined, block["keywords"]):
            return _pick(block["answer"], lang)

    if len(tokens) <= 8:
        for rule in data.get("rules", []):
            if _match(wordset, joined, rule["keywords"]):
                return _pick(rule["answer"], lang)
    return None
