"""US-165 — Asistente IA conversacional (widget global, EP008).

Cubre el ciclo de vida de conversación (crear → continuar → historial →
borrar), el gate por modo IA (disabled → 409), el parseo de acciones
seguras (navigate) y el rechazo de rutas externas.
"""
from __future__ import annotations

import json

import pytest

from app.services.ai.assistant import parse_assistant_reply
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    enable_tenant_ai,
    login,
)


async def _setup(client, db_session, slug, *, mode="platform"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    if mode != "disabled":
        await enable_tenant_ai(db_session, t, mode=mode)
    await db_session.commit()
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


def _stub_reply(payload: dict):
    async def _stub_generate(*args, **kwargs):
        from app.services.ai.provider import AIResult

        return AIResult(text=json.dumps(payload), model="stub", tokens_in=1, tokens_out=1)

    return _stub_generate


# --------------------------------------------------------------------------
# Unit: parse_assistant_reply
# --------------------------------------------------------------------------
def test_parse_reply_navigate_action_ok():
    msg, actions = parse_assistant_reply(
        '{"message": "Abrí el proyecto", "actions": '
        '[{"type": "navigate", "path": "/pmo/projects/abc", "label": "Abrir"}]}'
    )
    assert msg == "Abrí el proyecto"
    assert actions == [{"type": "navigate", "path": "/pmo/projects/abc", "label": "Abrir"}]


def test_parse_reply_rejects_external_url():
    _, actions = parse_assistant_reply(
        '{"message": "x", "actions": [{"type": "navigate", "path": "//evil.com"}]}'
    )
    assert actions == []


def test_parse_reply_non_json_falls_back_to_message():
    msg, actions = parse_assistant_reply("Hola, soy texto plano sin JSON.")
    assert "texto plano" in msg
    assert actions == []


# --------------------------------------------------------------------------
# Endpoint lifecycle
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chat_creates_and_continues_conversation(client, db_session, monkeypatch):
    _, auth = await _setup(client, db_session, "us165-chat")
    from app.api.v1.endpoints import assistant as mod

    monkeypatch.setattr(
        mod,
        "generate_for_tenant",
        _stub_reply({"message": "Hola, ¿en qué ayudo?", "actions": []}),
    )

    r = await client.post(
        "/api/v1/assistant/chat",
        headers=auth["_authz"],
        json={"message": "Hola", "page_context": "ruta=/pmo"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    conv_id = data["conversation_id"]
    assert data["message"] == "Hola, ¿en qué ayudo?"

    # Continúa la misma conversación.
    r2 = await client.post(
        "/api/v1/assistant/chat",
        headers=auth["_authz"],
        json={"message": "¿Qué proyectos hay?", "conversation_id": conv_id},
    )
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id

    # Historial: 4 mensajes (2 user + 2 assistant).
    r3 = await client.get(
        f"/api/v1/assistant/conversations/{conv_id}", headers=auth["_authz"]
    )
    assert r3.status_code == 200
    assert len(r3.json()["messages"]) == 4

    # Lista: 1 conversación.
    r4 = await client.get("/api/v1/assistant/conversations", headers=auth["_authz"])
    assert r4.status_code == 200
    assert len(r4.json()) == 1

    # Borra.
    r5 = await client.delete(
        f"/api/v1/assistant/conversations/{conv_id}", headers=auth["_authz"]
    )
    assert r5.status_code == 204
    r6 = await client.get("/api/v1/assistant/conversations", headers=auth["_authz"])
    assert r6.json() == []


@pytest.mark.asyncio
async def test_chat_disabled_mode_returns_409(client, db_session):
    _, auth = await _setup(client, db_session, "us165-off", mode="disabled")
    r = await client.post(
        "/api/v1/assistant/chat",
        headers=auth["_authz"],
        json={"message": "Hola"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_chat_cross_user_conversation_404(client, db_session, monkeypatch):
    _, auth_a = await _setup(client, db_session, "us165-a")
    _, auth_b = await _setup(client, db_session, "us165-b")
    from app.api.v1.endpoints import assistant as mod

    monkeypatch.setattr(
        mod, "generate_for_tenant", _stub_reply({"message": "ok", "actions": []})
    )
    r = await client.post(
        "/api/v1/assistant/chat", headers=auth_a["_authz"], json={"message": "Hi"}
    )
    conv_id = r.json()["conversation_id"]
    # El usuario B no puede ver la conversación de A.
    r2 = await client.get(
        f"/api/v1/assistant/conversations/{conv_id}", headers=auth_b["_authz"]
    )
    assert r2.status_code == 404
