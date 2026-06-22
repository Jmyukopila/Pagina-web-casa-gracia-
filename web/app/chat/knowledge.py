"""Loads the hotel knowledge base (FAQs) from data/hotel_info.md (cached)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

INFO_PATH = Path(__file__).resolve().parent / "data" / "hotel_info.md"


@lru_cache(maxsize=1)
def hotel_info() -> str:
    if INFO_PATH.exists():
        return INFO_PATH.read_text(encoding="utf-8")
    return "No hay información del hotel cargada todavía."
