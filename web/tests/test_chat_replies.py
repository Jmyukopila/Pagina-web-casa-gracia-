"""Live admin->widget chat replies: escalation thread, polling, admin reply form."""
from __future__ import annotations

from app import crud
from app.chat import tools
from app.config import settings
from app.schemas import ChatRequest

TOKEN = "tok-test-123"


# --- schema ----------------------------------------------------------------
def test_chat_request_accepts_thread_id():
    assert ChatRequest(message="hi", thread_id="  abc  ").thread_id == "abc"
    assert ChatRequest(message="hi").thread_id is None
    assert ChatRequest(message="hi", thread_id="").thread_id is None
    assert len(ChatRequest(message="hi", thread_id="x" * 80).thread_id) == 40


# --- escalation carries the thread ----------------------------------------
async def test_escalation_stores_thread_id(session):
    esc = await crud.create_escalation(session, motivo="cambio", thread_id="T-1")
    assert esc.thread_id == "T-1"


async def test_escalate_tool_passes_thread_id(session):
    await tools.run_tool("escalate_to_human", {"reason": "queja"}, session,
                         user_text="quiero hablar con una persona", thread_id="T-9")
    rows = await crud.list_escalations(session)
    assert rows and rows[0].thread_id == "T-9"


# --- polling endpoint ------------------------------------------------------
async def test_polling_returns_thread_replies_after_cursor(client, session):
    r1 = await crud.create_chat_reply(session, "A", "primera")
    await crud.create_chat_reply(session, "A", "segunda")
    await crud.create_chat_reply(session, "B", "otra")  # different thread

    res = await client.get("/api/chat/replies?thread=A&after=0")
    assert res.status_code == 200
    data = res.json()
    texts = [x["text"] for x in data["replies"]]
    assert texts == ["primera", "segunda"]  # only thread A, in order

    # The cursor advances; nothing new after it.
    after = await client.get(f"/api/chat/replies?thread=A&after={data['cursor']}")
    assert after.json()["replies"] == []

    # After the first reply's id, only the second remains.
    mid = await client.get(f"/api/chat/replies?thread=A&after={r1.id}")
    assert [x["text"] for x in mid.json()["replies"]] == ["segunda"]


async def test_polling_empty_thread_is_safe(client):
    res = await client.get("/api/chat/replies?thread=&after=0")
    assert res.status_code == 200
    assert res.json()["replies"] == []


# --- admin reply form ------------------------------------------------------
async def test_admin_reply_requires_token(client, session):
    esc = await crud.create_escalation(session, motivo="x", thread_id="T-7")
    res = await client.post(f"/admin/escalaciones/{esc.id}/responder",
                            data={"texto": "hola"})
    assert res.status_code == 401
    assert await crud.list_chat_replies(session, "T-7") == []


async def test_admin_reply_creates_chat_reply(client, session, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", TOKEN)
    esc = await crud.create_escalation(session, motivo="x", thread_id="T-7")

    res = await client.post(
        f"/admin/escalaciones/{esc.id}/responder?token={TOKEN}",
        data={"texto": "Te ayudo enseguida"})
    assert res.status_code == 303  # redirect back to /admin

    replies = await crud.list_chat_replies(session, "T-7")
    assert [r.texto for r in replies] == ["Te ayudo enseguida"]


async def test_admin_reply_ignores_empty_text(client, session, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", TOKEN)
    esc = await crud.create_escalation(session, motivo="x", thread_id="T-7")
    await client.post(f"/admin/escalaciones/{esc.id}/responder?token={TOKEN}",
                      data={"texto": "   "})
    assert await crud.list_chat_replies(session, "T-7") == []
