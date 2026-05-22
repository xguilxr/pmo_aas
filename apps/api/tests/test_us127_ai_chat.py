"""US-127 — Chat IA conversacional del Report Builder (EP020).

TC-221 (IA llama add_section con id válido), TC-222 (PM puede revertir
— validamos que el endpoint devuelva las acciones para el frontend),
TC-223 (fallback entre modelos — el modo `disabled` devuelve 409).
"""
from __future__ import annotations

import json

import pytest

from app.models.report_section import ReportSection
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    enable_tenant_ai,
    login,
)


async def _seed_min_catalog(db):
    for code, name in [
        ("S-01", "Portada"),
        ("S-09", "Hitos"),
        ("S-11", "Riesgos"),
        ("S-16", "Críticos"),
    ]:
        db.add(
            ReportSection(
                code=code,
                name=name,
                category="HDR",
                level=3,
                data_shape={},
                parameters_schema={},
                composition_mode_default="A",
                supports_ia=False,
                enabled=True,
            )
        )
    await db.flush()


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
    await enable_tenant_ai(db_session, t, mode=mode)
    await _seed_min_catalog(db_session)
    await db_session.commit()
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_tc221_chat_parses_add_section(client, db_session, monkeypatch):
    """TC-221 — la respuesta del modelo se parsea y add_section se
    valida contra el catálogo."""
    _, auth = await _setup(client, db_session, "us127-add")

    async def _stub_generate(*args, **kwargs):
        from app.services.ai.provider import AIResult
        # Forzamos JSON canónico para emular respuesta del modelo.
        payload = {
            "message": "Agrego hitos al canvas.",
            "actions": [{"type": "add_section", "code": "S-09"}],
        }
        return AIResult(
            text=json.dumps(payload),
            model="stub",
            tokens_in=10,
            tokens_out=20,
            duration_ms=5,
        )

    from app.api.v1.endpoints import report_builder_chat as mod
    monkeypatch.setattr(mod, "generate_for_tenant", _stub_generate)

    r = await client.post(
        "/api/v1/report-builder/ai-chat",
        headers=auth["_authz"],
        json={
            "user_message": "Agrega los hitos próximos",
            "canvas_codes": ["S-01"],
            "composition_mode": "A",
            "history": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"].startswith("Agrego")
    assert body["actions"] == [{"type": "add_section", "code": "S-09", "index": None, "to": None, "params": None}]


@pytest.mark.asyncio
async def test_tc222_actions_revertible_format(client, db_session, monkeypatch):
    """TC-222 — el endpoint devuelve la lista de actions completa para
    que el frontend la persista y pueda revertir.
    """
    _, auth = await _setup(client, db_session, "us127-rev")

    async def _stub_generate(*args, **kwargs):
        from app.services.ai.provider import AIResult
        payload = {
            "message": "Reordeno",
            "actions": [
                {"type": "reorder_section", "from": 1, "to": 0},
                {"type": "update_section_params", "index": 0, "params": {"top_n": 5}},
            ],
        }
        return AIResult(text=json.dumps(payload), model="stub", tokens_in=1, tokens_out=1, duration_ms=1)

    from app.api.v1.endpoints import report_builder_chat as mod
    monkeypatch.setattr(mod, "generate_for_tenant", _stub_generate)

    r = await client.post(
        "/api/v1/report-builder/ai-chat",
        headers=auth["_authz"],
        json={
            "user_message": "Pon los críticos arriba",
            "canvas_codes": ["S-01", "S-16"],
            "composition_mode": "A",
        },
    )
    assert r.status_code == 200
    actions = r.json()["actions"]
    assert len(actions) == 2
    types = [a["type"] for a in actions]
    assert "reorder_section" in types
    assert "update_section_params" in types


@pytest.mark.asyncio
async def test_tc223_disabled_returns_409(client, db_session):
    """TC-223 — tenant con IA deshabilitada → 409 (no fallback silencioso)."""
    _, auth = await _setup(client, db_session, "us127-off", mode="disabled")
    r = await client.post(
        "/api/v1/report-builder/ai-chat",
        headers=auth["_authz"],
        json={"user_message": "hi", "canvas_codes": []},
    )
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["code"] == "AI_DISABLED"


@pytest.mark.asyncio
async def test_invalid_action_type_filtered(client, db_session, monkeypatch):
    """El parser descarta tipos de action no permitidos."""
    _, auth = await _setup(client, db_session, "us127-filter")

    async def _stub_generate(*args, **kwargs):
        from app.services.ai.provider import AIResult
        payload = {
            "message": "test",
            "actions": [
                {"type": "delete_project"},  # NO permitido
                {"type": "add_section", "code": "S-09"},
            ],
        }
        return AIResult(text=json.dumps(payload), model="stub", tokens_in=1, tokens_out=1, duration_ms=1)

    from app.api.v1.endpoints import report_builder_chat as mod
    monkeypatch.setattr(mod, "generate_for_tenant", _stub_generate)

    r = await client.post(
        "/api/v1/report-builder/ai-chat",
        headers=auth["_authz"],
        json={"user_message": "test", "canvas_codes": []},
    )
    assert r.status_code == 200
    actions = r.json()["actions"]
    assert len(actions) == 1
    assert actions[0]["type"] == "add_section"
