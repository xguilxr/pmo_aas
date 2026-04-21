"""US-054 — platform-level AI defaults editable por superadmin."""
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


# TC-US054-01 — superadmin lee defaults (row singleton seedeada).
@pytest.mark.asyncio
async def test_tc_us054_01_superadmin_can_read_defaults(client, db_session):
    auth = await _superadmin(client, db_session)
    r = await client.get("/api/v1/superadmin/ai/defaults", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    # Row seedeada por la migración queda con todos NULL.
    assert body["ai_mode"] is None
    assert body["ollama_base_url"] is None
    assert body["ollama_model"] is None
    assert body["ai_timeout_sec"] is None
    # El snapshot del env siempre viene lleno.
    env = body["env"]
    assert env["ai_mode"]
    assert env["ollama_base_url"]
    assert env["ollama_model"]
    assert env["ai_timeout_sec"] >= 5


# TC-US054-02 — superadmin actualiza defaults y la lectura siguiente los refleja.
@pytest.mark.asyncio
async def test_tc_us054_02_superadmin_patch_roundtrip(client, db_session):
    auth = await _superadmin(client, db_session)
    patch_body = {
        "ai_mode": "ollama",
        "ollama_base_url": "http://ollama-host.taile4df9d.ts.net:11434",
        "ollama_model": "qwen2.5:7b-instruct-q4_K_M",
        "ai_timeout_sec": 500,
    }
    r = await client.patch(
        "/api/v1/superadmin/ai/defaults", json=patch_body, headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_mode"] == "ollama"
    assert body["ollama_base_url"] == "http://ollama-host.taile4df9d.ts.net:11434"
    assert body["ollama_model"] == "qwen2.5:7b-instruct-q4_K_M"
    assert body["ai_timeout_sec"] == 500

    # Reload confirms persistence.
    r2 = await client.get("/api/v1/superadmin/ai/defaults", headers=auth["_authz"])
    assert r2.json()["ai_timeout_sec"] == 500


# TC-US054-03 — admin normal (no superadmin) recibe 403.
@pytest.mark.asyncio
async def test_tc_us054_03_regular_admin_forbidden(client, db_session):
    auth = await _regular_admin(client, db_session)
    r = await client.get("/api/v1/superadmin/ai/defaults", headers=auth["_authz"])
    assert r.status_code == 403
    r2 = await client.patch(
        "/api/v1/superadmin/ai/defaults", json={"ai_timeout_sec": 300},
        headers=auth["_authz"],
    )
    assert r2.status_code == 403


# TC-US054-04 — resolve_ollama_config: tenant gana sobre platform.
@pytest.mark.asyncio
async def test_tc_us054_04_tenant_override_wins(db_session):
    from app.models.platform_settings import PlatformAISettings, PLATFORM_SETTINGS_ID
    from app.services.ai.platform_config import resolve_ollama_config

    row = await db_session.get(PlatformAISettings, PLATFORM_SETTINGS_ID)
    if row is None:
        row = PlatformAISettings(id=PLATFORM_SETTINGS_ID)
        db_session.add(row)
    row.ollama_base_url = "http://platform-ollama:11434"
    row.ollama_model = "platform-model"
    row.ai_timeout_sec = 200
    await db_session.flush()

    tenant_cfg = {
        "base_url": "http://tenant-ollama:11434",
        "model": "tenant-model",
        "timeout_sec": 100,
    }
    merged = await resolve_ollama_config(db_session, tenant_cfg)
    assert merged is not None
    assert merged["base_url"] == "http://tenant-ollama:11434"
    assert merged["model"] == "tenant-model"
    assert merged["timeout_sec"] == 100


# TC-US054-05 — resolve_ollama_config: platform gana sobre env cuando no hay tenant.
@pytest.mark.asyncio
async def test_tc_us054_05_platform_beats_env(db_session):
    from app.models.platform_settings import PlatformAISettings, PLATFORM_SETTINGS_ID
    from app.services.ai.platform_config import resolve_ollama_config

    row = await db_session.get(PlatformAISettings, PLATFORM_SETTINGS_ID)
    if row is None:
        row = PlatformAISettings(id=PLATFORM_SETTINGS_ID)
        db_session.add(row)
    row.ollama_base_url = "http://platform-level:11434"
    row.ollama_model = "platform-model"
    row.ai_timeout_sec = 333
    await db_session.flush()

    merged = await resolve_ollama_config(db_session, None)
    assert merged is not None
    assert merged["base_url"] == "http://platform-level:11434"
    assert merged["model"] == "platform-model"
    assert merged["timeout_sec"] == 333
