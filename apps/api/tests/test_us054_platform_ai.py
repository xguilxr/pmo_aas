"""US-054 — platform-level AI defaults editable por superadmin.

BUG-053 (2026-05-08): los tests de Ollama (TC-04, TC-05) y los campos
ollama_base_url/ollama_model/ai_timeout_sec se eliminaron junto con el
provider. Se mantiene la cobertura de auth + roundtrip de ai_mode +
groq_model.
"""
from __future__ import annotations

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _superadmin(client, db_session):
    t = await create_tenant(db_session, slug="sa-ai", name="sa-ai")
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="superadmin_ai",
        email="super@ai.example.com", password="Str0ng-Admin-1!",
        is_superadmin=True, roles=[role],
    )
    return await login(client, "superadmin_ai", "Str0ng-Admin-1!")


async def _regular_admin(client, db_session):
    t = await create_tenant(db_session, slug="tenant-ai-reg", name="reg")
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin_reg",
        email="admin_reg@ai.example.com", password="Str0ng-Admin-1!",
        roles=[role],
    )
    return await login(client, "admin_reg", "Str0ng-Admin-1!")


@pytest.mark.asyncio
async def test_tc_us054_01_superadmin_can_read_defaults(client, db_session):
    auth = await _superadmin(client, db_session)
    r = await client.get("/api/v1/superadmin/ai/defaults", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_mode"] is None
    env = body["env"]
    assert env["ai_mode"] in ("disabled", "platform", "byo")


@pytest.mark.asyncio
async def test_tc_us054_02_superadmin_patch_roundtrip(client, db_session):
    auth = await _superadmin(client, db_session)
    patch_body = {
        "ai_mode": "platform",
        "groq_model": "llama-3.3-70b-versatile",
    }
    r = await client.patch(
        "/api/v1/superadmin/ai/defaults", json=patch_body, headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_mode"] == "platform"
    assert body["groq_model"] == "llama-3.3-70b-versatile"

    r2 = await client.get("/api/v1/superadmin/ai/defaults", headers=auth["_authz"])
    assert r2.json()["groq_model"] == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_tc_us054_03_regular_admin_forbidden(client, db_session):
    auth = await _regular_admin(client, db_session)
    r = await client.get("/api/v1/superadmin/ai/defaults", headers=auth["_authz"])
    assert r.status_code == 403
    r2 = await client.patch(
        "/api/v1/superadmin/ai/defaults", json={"ai_mode": "disabled"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 403
