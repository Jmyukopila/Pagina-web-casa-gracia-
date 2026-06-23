"""Tests for the distributed (DB-backed) rate-limit counter."""
from __future__ import annotations

from app import crud


async def test_hit_rate_limit_increments_within_window(session):
    counts = [await crud.hit_rate_limit(session, "1.2.3.4:60") for _ in range(3)]
    assert counts == [1, 2, 3]


async def test_hit_rate_limit_separate_keys_are_independent(session):
    assert await crud.hit_rate_limit(session, "a:60") == 1
    assert await crud.hit_rate_limit(session, "b:60") == 1
    assert await crud.hit_rate_limit(session, "a:60") == 2


async def test_hit_rate_limit_enforces_threshold(session):
    limit = 5
    allowed = 0
    for _ in range(8):
        if await crud.hit_rate_limit(session, "9.9.9.9:5") <= limit:
            allowed += 1
    assert allowed == limit  # the 6th..8th exceed the limit
