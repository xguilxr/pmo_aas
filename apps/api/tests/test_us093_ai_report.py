"""US-093 — Reportes: creación con IA + preview.

Cubre:
- TC-093.2: ai_mode=disabled → 400 con mensaje claro.
- AI=platform path: stub Groq devuelve HTML; endpoint envuelve con
  meta del proyecto y devuelve `{html, history_id}`.
- save_to_history=true persiste un row en `report_history`.
"""
from unittest.mock import patch

import pytest

from app.services.ai.provider import AIResult
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session, *, ai_mode: str = "disabled"):
    t = await create_tenant(db_session)
    if ai_mode != "disabled":
        # Configurar mode platform en settings.
        t.settings = {"ai": {"mode": ai_mode}}
        await db_session.commit()
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


@pytest.mark.asyncio
async def test_ai_disabled_blocks_endpoint(client, db_session):
    auth, proj = await _setup(client, db_session, ai_mode="disabled")
    r = await client.post(
        f"/api/v1/projects/{proj}/reports/ai-generate",
        json={"base": "avance"},
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 409, 422), r.text
    assert "ai" in r.text.lower() or "disabled" in r.text.lower()


@pytest.mark.asyncio
async def test_ai_platform_returns_html_with_save_to_history(client, db_session):
    auth, proj = await _setup(client, db_session, ai_mode="platform")
    fake = AIResult(
        text="<h2>Resumen</h2><p>El proyecto avanza según lo planeado.</p>",
        model="groq-stub",
        tokens_in=10,
        tokens_out=20,
    )
    async def _fake_generate(*args, **kwargs):
        return fake

    with patch(
        "app.services.ai.provider.generate_for_tenant",
        side_effect=_fake_generate,
    ):
        r = await client.post(
            f"/api/v1/projects/{proj}/reports/ai-generate",
            json={
                "base": "avance",
                "include_kpis": True,
                "include_tasks": True,
                "include_raid": True,
                "include_milestones": False,
                "free_notes": "Foco en hitos de Q2.",
                "save_to_history": True,
            },
            headers=auth["_authz"],
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "Resumen" in body["html"]
    assert body["history_id"] is not None
    # History debe tener entry visible.
    h = await client.get(
        f"/api/v1/projects/{proj}/report-history", headers=auth["_authz"]
    )
    assert h.status_code == 200
    assert any(item["id"] == body["history_id"] for item in h.json())
