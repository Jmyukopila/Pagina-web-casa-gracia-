"""Dashboard login with user + password (the ?token= path stays as fallback)."""
from __future__ import annotations

from app.config import settings
from app.deps import is_valid_admin_login

USER = "recepcion"
PASS = "clave-super-segura"
TOKEN = "tok-login-123"


def _configure(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", TOKEN)
    monkeypatch.setattr(settings, "admin_user", USER)
    monkeypatch.setattr(settings, "admin_password", PASS)


# --- credential check ------------------------------------------------------
def test_login_check_rejects_empty_password(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "")  # unconfigured
    assert is_valid_admin_login("admin", "anything") is False


def test_login_check_matches(monkeypatch):
    _configure(monkeypatch)
    assert is_valid_admin_login(USER, PASS) is True
    assert is_valid_admin_login(USER, "wrong") is False
    assert is_valid_admin_login("other", PASS) is False


# --- HTTP flow -------------------------------------------------------------
async def test_login_page_shows_user_and_password(client):
    res = await client.get("/admin")
    assert res.status_code == 200
    assert 'name="user"' in res.text and 'name="password"' in res.text


async def test_bad_login_redirects_with_error(client, monkeypatch):
    _configure(monkeypatch)
    res = await client.post("/admin/login",
                            data={"user": USER, "password": "nope"})
    assert res.status_code == 303
    assert res.headers["location"] == "/admin?bad=1"
    # the error is rendered on the followed page
    page = await client.get("/admin?bad=1")
    assert "incorrectos" in page.text


async def test_good_login_sets_session_and_opens_dashboard(client, monkeypatch):
    _configure(monkeypatch)
    res = await client.post("/admin/login",
                            data={"user": USER, "password": PASS})
    assert res.status_code == 303
    assert res.headers["location"] == "/admin"
    assert "cg_admin" in res.headers.get("set-cookie", "")
    # cookie now grants the dashboard
    dash = await client.get("/admin")
    assert dash.status_code == 200
    assert "panel-escalaciones" in dash.text and "adm-side" in dash.text


async def test_token_query_still_works_as_fallback(client, monkeypatch):
    _configure(monkeypatch)
    res = await client.get(f"/admin?token={TOKEN}")
    assert res.status_code == 200
    assert "adm-side" in res.text
