"""Tests for the secret-protected /internal/lobby/sync endpoint."""
from __future__ import annotations

from app.config import settings

SECRET = "cron-s3cr3t"


async def test_sync_requires_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "lobby_sync_secret", SECRET)
    # No credentials -> rejected.
    assert (await client.post("/internal/lobby/sync")).status_code == 401
    # Wrong secret -> rejected.
    bad = await client.get("/internal/lobby/sync",
                           headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


async def test_sync_accepts_valid_bearer(client, monkeypatch):
    monkeypatch.setattr(settings, "lobby_sync_secret", SECRET)
    r = await client.get("/internal/lobby/sync",
                         headers={"Authorization": f"Bearer {SECRET}"})
    assert r.status_code == 200
    # Lobby is disabled in tests (no token) -> the run reports it cleanly.
    assert r.json()["ok"] is False


async def test_sync_unconfigured_secret_is_closed(client):
    # With no LOBBY_SYNC_SECRET configured, every call is rejected (fail closed).
    assert (await client.get("/internal/lobby/sync")).status_code == 401
