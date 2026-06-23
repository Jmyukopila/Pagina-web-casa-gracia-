"""Async HTTP client for the Lobby PMS v2 REST API.

Auth is a per-property API token; IP allowlisting is optional and left off
(Vercel has no fixed egress IP). The token is injected in ONE place
(``_request``) so the exact mechanism — currently a ``token`` query param — is
trivial to switch to a header once confirmed with Lobby.

The client is only constructed when ``settings.lobby_enabled`` is true. Tests
inject an ``httpx.AsyncClient`` built on ``httpx.MockTransport`` so no network
is touched.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger("casagracia.lobby")


class LobbyError(RuntimeError):
    """A Lobby API call failed (network or non-2xx). Callers degrade, never crash."""


class LobbyClient:
    def __init__(self, *, base_url: str | None = None, token: str | None = None,
                 http: httpx.AsyncClient | None = None, timeout: float = 20.0):
        self.base_url = (base_url or settings.lobby_base_url).rstrip("/")
        self.token = token if token is not None else settings.lobby_api_token
        self._http = http
        self._owns_http = http is None
        self._timeout = timeout

    async def __aenter__(self) -> LobbyClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    async def _request(self, method: str, path: str, *,
                       params: dict | None = None, json: Any = None) -> Any:
        assert self._http is not None, "use LobbyClient as an async context manager"
        # Single point of auth: token as a query param (confirm header form later).
        q = {"token": self.token, **(params or {})}
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = await self._http.request(method, url, params=q, json=json)
        except httpx.HTTPError as e:
            raise LobbyError(f"{method} {path} failed: {e}") from e
        if resp.status_code >= 400:
            raise LobbyError(f"{method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
        if not resp.content:
            return None
        return resp.json()

    @staticmethod
    def _items(payload: Any) -> list[dict]:
        """Lobby list endpoints may wrap results under data/items/results."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "items", "results", "reservations", "rooms"):
                if isinstance(payload.get(key), list):
                    return payload[key]
        return []

    # --- Endpoints ---------------------------------------------------------
    async def available_rooms(self, checkin: date | None = None,
                              checkout: date | None = None) -> list[dict]:
        params: dict = {}
        if checkin:
            params["check_in"] = checkin.isoformat()
        if checkout:
            params["check_out"] = checkout.isoformat()
        return self._items(await self._request("GET", "available-rooms", params=params))

    async def list_reservations(self, *, checkin_from: date | None = None,
                                checkin_to: date | None = None) -> list[dict]:
        params: dict = {}
        if checkin_from:
            params["check_in_from"] = checkin_from.isoformat()
        if checkin_to:
            params["check_in_to"] = checkin_to.isoformat()
        return self._items(await self._request("GET", "reservations", params=params))

    async def get_reservation(self, code: str) -> dict | None:
        return await self._request("GET", f"reservations/{code}")

    async def create_reservation(self, payload: dict) -> dict:
        return await self._request("POST", "reservations", json=payload) or {}

    async def cancel_reservation(self, code: str) -> Any:
        return await self._request("POST", f"reservations/{code}/cancel")

    async def block_rooms(self, lobby_room_id: str, desde: date, hasta: date) -> Any:
        return await self._request("POST", "block-rooms", json={
            "room_id": lobby_room_id,
            "check_in": desde.isoformat(),
            "check_out": hasta.isoformat(),
        })


def get_client(**kwargs) -> LobbyClient | None:
    """A client when Lobby is configured (or when a test injects `http`); else None."""
    if not settings.lobby_enabled and "http" not in kwargs:
        return None
    return LobbyClient(**kwargs)
