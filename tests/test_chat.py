"""Chat tests — AI integratsiyasini monkey patch qilamiz."""
from __future__ import annotations

import pytest

from app.services import ai


@pytest.fixture(autouse=True)
def _stub_openrouter(monkeypatch):
    async def _fake_chat(prompt, system="", **kwargs):
        return f"AI javob: {prompt[:30]}"
    monkeypatch.setattr(ai, "openrouter_chat", _fake_chat)
    # Endpoint ham app.api.chat'dan import qiladi
    from app.api import chat as chat_mod
    monkeypatch.setattr(chat_mod, "openrouter_chat", _fake_chat)


async def _login(client, phone="+998900000001"):
    r = await client.post("/api/auth/login/", json={"phone": phone, "password": "pass"})
    return r.json()["access"]


@pytest.mark.asyncio
async def test_send_creates_conversation_and_replies(client):
    token = await _login(client)
    r = await client.post(
        "/api/chat/send/",
        json={"text": "Salom"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["conversation_id"] > 0
    assert data["reply"]["role"] == "ai"
    assert "AI javob:" in data["reply"]["text"]


@pytest.mark.asyncio
async def test_continue_conversation(client):
    token = await _login(client, "+998900000002")
    r1 = await client.post(
        "/api/chat/send/", json={"text": "Birinchi xabar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    cid = r1.json()["conversation_id"]
    r2 = await client.post(
        "/api/chat/send/", json={"text": "Ikkinchi", "conversation_id": cid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["conversation_id"] == cid

    r3 = await client.get(
        f"/api/chat/conversations/{cid}/messages/",
        headers={"Authorization": f"Bearer {token}"},
    )
    msgs = r3.json()["results"]
    assert len(msgs) == 4  # 2 user + 2 ai


@pytest.mark.asyncio
async def test_list_conversations(client):
    token = await _login(client, "+998900000003")
    await client.post("/api/chat/send/", json={"text": "Test"},
                      headers={"Authorization": f"Bearer {token}"})
    r = await client.get("/api/chat/conversations/",
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1
