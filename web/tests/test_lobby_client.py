"""Tests for the Lobby PMS HTTP client, using httpx.MockTransport (no network)."""
from __future__ import annotations

import json

import httpx
import pytest

from app.lobby.client import LobbyClient, LobbyError, get_client


def _client(handler, token="TOK") -> LobbyClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return LobbyClient(base_url="https://api.test/v2", token=token, http=http)


async def test_token_is_sent_as_param():
    seen = {}

    def handler(request):
        seen["token"] = request.url.params.get("token")
        return httpx.Response(200, json=[])

    async with _client(handler, token="SECRET") as c:
        await c.available_rooms()
    assert seen["token"] == "SECRET"


async def test_available_rooms_unwraps_list_and_dict():
    async def run(payload):
        async with _client(lambda r: httpx.Response(200, json=payload)) as c:
            return await c.available_rooms()

    assert await run([{"room_id": "1"}]) == [{"room_id": "1"}]
    assert await run({"rooms": [{"room_id": "2"}]}) == [{"room_id": "2"}]
    assert await run({"unexpected": 1}) == []


async def test_create_reservation_posts_body():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"code": "ABC"})

    async with _client(handler) as c:
        resp = await c.create_reservation({"room_id": "1", "adults": 2})
    assert seen["method"] == "POST"
    assert seen["body"]["adults"] == 2
    assert resp == {"code": "ABC"}


async def test_http_error_becomes_lobby_error():
    async with _client(lambda r: httpx.Response(500, text="boom")) as c:
        with pytest.raises(LobbyError):
            await c.available_rooms()


def test_get_client_gated_on_enabled():
    # Disabled (no token) and no injected http -> no client.
    assert get_client() is None
    # Injected http (test path) -> a client regardless of config.
    injected = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])))
    assert isinstance(get_client(http=injected), LobbyClient)
