"""Tests for chatbot escalation persistence (app.crud + chat tools)."""
from __future__ import annotations

import json

from app import crud
from app.chat import tools


def test_extract_contact_email_and_phone():
    assert crud.extract_contact("escríbeme a ana@example.com porfa") == "ana@example.com"
    assert crud.extract_contact("mi número es +57 300 123 4567").startswith("+57")
    assert crud.extract_contact("no dejo datos aquí") is None


async def test_create_escalation_persists(session):
    esc = await crud.create_escalation(
        session, motivo="Quiere cancelar", mensaje="Necesito cancelar mi reserva",
        idioma="es", contexto="user: hola\nuser: necesito cancelar",
        contacto="ana@example.com",
    )
    assert esc.id is not None
    assert esc.atendido is False

    pending = await crud.list_escalations(session, pending_only=True)
    assert len(pending) == 1
    assert pending[0].motivo == "Quiere cancelar"
    assert pending[0].contacto == "ana@example.com"


async def test_run_tool_escalate_logs_and_returns_contact(session):
    raw = await tools.run_tool(
        "escalate_to_human", {"reason": "Queja sobre el aire"}, session,
        user_text="el aire no enfría, mi correo es juan@correo.com",
        context="user: el aire no enfría",
    )
    out = json.loads(raw)
    assert out["ok"] is True
    assert "reason" in out

    rows = await crud.list_escalations(session)
    assert len(rows) == 1
    assert rows[0].contacto == "juan@correo.com"
    assert rows[0].idioma in ("es", "en")
