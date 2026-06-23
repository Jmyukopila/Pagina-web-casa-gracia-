"""Lobby PMS (channel manager) integration.

Two-way sync so the direct site and the OTAs share one calendar:
- pull OTA reservations + rates from Lobby (so we never oversell);
- push direct bookings to Lobby (so it blocks the dates everywhere).

Everything is gated on ``settings.lobby_enabled`` (a token is configured). With
no account the package is inert and the site behaves exactly as before.

The exact Lobby v2 wire format (field names, auth header) is confirmed against a
real account / Lobby support; it lives ONLY in ``mapping.py`` so adapting it
later does not touch the client, the sync or the routers.
"""
