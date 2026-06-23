"""Language detection + FAQ routing in the chatbot prefilter.

Guards against the regression where short English FAQ questions ("laundry",
"safe"...) were answered in Spanish because their vocabulary was missing from
the language detector.
"""
from __future__ import annotations

import pytest

from app.chat.prefilter import _data, _normalize, detect_lang, quick_answer


def _answers_for(lang: str) -> set[str]:
    """All canned answers in a given language, straight from quick_replies.json."""
    out: set[str] = set()
    data = _data()
    for block in ("greetings", "thanks"):
        b = data.get(block)
        if b:
            out.add(b["answer"][lang])
    for rule in data.get("rules", []):
        out.add(rule["answer"][lang])
    return out

EN_FAQ = [
    "laundry", "iron", "safe", "luggage", "late check in", "cancellation policy",
    "visitors", "children", "wifi password", "do you have a pool",
    "is breakfast included", "what time is check-in", "do you allow pets",
    "where are you located", "can I store my luggage", "do you have parking",
    "airport transfer", "can I smoke", "thanks", "hello",
]
ES_FAQ = [
    "lavanderia", "plancha", "caja fuerte", "equipaje", "llego tarde",
    "politica de cancelacion", "reciben visitas", "tienen niños",
    "clave del wifi", "tienen piscina", "incluye desayuno", "se permiten mascotas",
    "donde estan ubicados", "hay caja de seguridad", "tienen parqueadero",
    "puedo fumar", "gracias", "hola",
]


@pytest.mark.parametrize("msg", EN_FAQ)
def test_english_messages_detected_as_english(msg):
    assert detect_lang(_normalize(msg)) == "en", msg


@pytest.mark.parametrize("msg", ES_FAQ)
def test_spanish_messages_detected_as_spanish(msg):
    assert detect_lang(_normalize(msg)) == "es", msg


@pytest.mark.parametrize("msg", EN_FAQ)
def test_english_faq_answers_in_english(msg):
    """When the prefilter has a canned answer, it must be the English variant."""
    ans = quick_answer(msg)
    if ans is None:
        return  # routed to the LLM, which handles language itself
    assert ans in _answers_for("en"), f"{msg!r} -> {ans!r}"
    assert ans not in _answers_for("es"), f"{msg!r} returned the Spanish answer"


def test_availability_questions_are_not_intercepted():
    """Availability/booking must fall through to the LLM, not the FAQ."""
    for msg in ["do you have rooms available next weekend?",
                "how much for 2 nights?",
                "tienen disponibilidad para el otro fin de semana?"]:
        assert quick_answer(msg) is None, msg
