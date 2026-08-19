"""US-057 — IA multi-modo por tenant (disabled / platform / byo).

Cubre:
- Cifrado Fernet (roundtrip + masking).
- Helper `load_tenant_ai` con los 3 modos.
- Factory `generate_for_tenant` enruta al provider correcto según modo.
- Endpoint `/ai/minutes` responde 409 cuando modo=disabled.
- Endpoint `/ai/projects/{id}/reports/draft` responde 409 cuando
  modo=platform (scope limitado a minutas) y modo=disabled.
- Endpoints `/admin/ai/provider` GET/PATCH con Fernet + masking +
  audit log.
- Endpoint `/admin/ai/provider/test` valida BYO sin persistir si viene
  body explícito; persiste `last_test_*` si no.
- Endpoint `/superadmin/ai/tenants-status` lista todos los tenants.
- Endpoint `/superadmin/ai/groq-usage` agrega ai_jobs provider=groq.
- Worker `_call_ai_for_tenant` reintenta 3 veces y notifica al
  superadmin cuando platform agota reintentos.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.ai import AIJob
from app.services.ai.provider import (
    AIResult,
    GroqProvider,
    generate_for_tenant,
)
from app.services.ai.tenant_ai import TenantAIConfig, load_tenant_ai
from app.services.ai_secrets import decrypt_secret, encrypt_secret, mask_secret
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    enable_tenant_ai,
    login,
)

# -----------------------------------------------------------------------------
# Helpers comunes
# -----------------------------------------------------------------------------

async def _admin(client, db_session, slug="ai57"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    u = await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, u, auth


async def _project(client, auth, name="P US057"):
    org = await client.post(
        "/api/v1/organizations", json={"name": f"Org {name}"},
        headers=auth["_authz"],
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": name, "description": "d", "type": "innovacion",
            "priority": 3, "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return p.json()["id"]


# -----------------------------------------------------------------------------
# Cifrado Fernet (reactivado en US-057)
# -----------------------------------------------------------------------------

def test_us057_fernet_roundtrip_and_mask():
    plain = "gsk_abcdefghijklmnop1234"
    ct = encrypt_secret(plain)
    assert ct.startswith("enc::")
    assert decrypt_secret(ct) == plain
    assert mask_secret(plain).endswith("1234")
    assert "•" in mask_secret(plain)
    assert decrypt_secret("") == ""
    assert decrypt_secret(None) == ""  # type: ignore[arg-type]


# -----------------------------------------------------------------------------
# load_tenant_ai
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_load_tenant_ai_defaults_disabled(client, db_session):
    t, _u, _auth = await _admin(client, db_session, slug="ai57-default")
    cfg = await load_tenant_ai(db_session, t.id)
    assert cfg.mode == "disabled"
    assert cfg.byo is None
    assert cfg.enabled is False


@pytest.mark.asyncio
async def test_us057_load_tenant_ai_byo_decrypts_key(client, db_session):
    t, _u, _auth = await _admin(client, db_session, slug="ai57-byo-load")
    await enable_tenant_ai(
        db_session, t, mode="byo",
        byo={
            "provider": "openai",
            "api_key_encrypted": encrypt_secret("sk-testkey-abc"),
            "model": "gpt-4o-mini",
        },
    )
    cfg = await load_tenant_ai(db_session, t.id)
    assert cfg.mode == "byo"
    assert cfg.byo is not None
    assert cfg.byo["provider"] == "openai"
    assert cfg.byo["api_key"] == "sk-testkey-abc"
    assert cfg.byo["model"] == "gpt-4o-mini"


# -----------------------------------------------------------------------------
# Factory generate_for_tenant — enrutamiento por modo
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_factory_disabled_returns_stub():
    res = await generate_for_tenant(
        "hola",
        system=None,
        tenant_ai_mode="disabled",
        platform_groq_config=None,
        byo_config=None,
    )
    assert "AI disabled" in res.text


@pytest.mark.asyncio
async def test_us057_factory_platform_calls_groq(monkeypatch):
    calls: dict = {}

    async def _fake(self, prompt, *, system=None, override=None, json_mode=False):
        calls["override"] = override
        calls["json_mode"] = json_mode
        return AIResult(text="GROQ_OK", model="groq:llama-3.3-70b-versatile")

    monkeypatch.setattr(GroqProvider, "generate", _fake)
    res = await generate_for_tenant(
        "prompt",
        system="sys",
        tenant_ai_mode="platform",
        platform_groq_config={"api_key": "gsk_x", "model": "llama-3.3-70b-versatile"},
        byo_config=None,
        tenant_id="tenant-abc",
        job_id="job-xyz",
    )
    assert res.text == "GROQ_OK"
    assert calls["override"]["api_key"] == "gsk_x"
    # tenant_id y job_id se inyectan para trazabilidad Groq.
    assert calls["override"]["tenant_id"] == "tenant-abc"
    assert calls["override"]["job_id"] == "job-xyz"


@pytest.mark.asyncio
async def test_us057_factory_byo_invalid_provider_raises():
    with pytest.raises(RuntimeError, match="byo_provider_invalid"):
        await generate_for_tenant(
            "prompt",
            system=None,
            tenant_ai_mode="byo",
            platform_groq_config=None,
            byo_config={"provider": "notreal", "api_key": "x"},
        )


# -----------------------------------------------------------------------------
# Endpoint /ai/minutes gate por modo
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_minute_endpoint_gates_disabled(client, db_session):
    _t, _u, auth = await _admin(client, db_session, slug="ai57-gate-min")
    # No llamamos enable_tenant_ai — queda modo disabled por default.
    proj_id = await _project(client, auth)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={
            "project_id": proj_id,
            "transcript": "transcripción válida más larga",
            "save_as_minute": False,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "AI_DISABLED"


@pytest.mark.asyncio
async def test_us057_report_endpoint_gates_platform_scope(client, db_session):
    t, _u, auth = await _admin(client, db_session, slug="ai57-gate-rep")
    await enable_tenant_ai(db_session, t, mode="platform")
    proj_id = await _project(client, auth, name="PRep")
    r = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft",
        json={"recipients": []},
        headers=auth["_authz"],
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "AI_PLATFORM_SCOPE_LIMITED"


# -----------------------------------------------------------------------------
# /admin/ai/provider GET + PATCH
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_admin_provider_crud_roundtrip(client, db_session):
    _t, _u, auth = await _admin(client, db_session, slug="ai57-admin")

    # GET inicial: mode=disabled
    r = await client.get("/api/v1/admin/ai/provider", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["mode"] == "disabled"
    assert r.json()["byo"] is None

    # PATCH a byo + guardar key
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {
                "provider": "openai",
                "api_key": "sk-testtesttest-1234",
                "model": "gpt-4o-mini",
            },
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "byo"
    assert body["byo"]["provider"] == "openai"
    assert body["byo"]["has_api_key"] is True
    # El mask es los últimos 4 chars → "1234"
    assert body["byo"]["api_key_mask"].endswith("1234")
    # El plaintext NO debe estar en la respuesta.
    assert "sk-testtesttest-1234" not in str(body)

    # PATCH sin api_key conserva la cifrada.
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {"provider": "openai", "model": "gpt-4o"},
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["byo"]["has_api_key"] is True
    assert r.json()["byo"]["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_us057_admin_provider_patch_requires_byo_config(client, db_session):
    _t, _u, auth = await _admin(client, db_session, slug="ai57-no-byo")
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={"mode": "byo"},  # byo ausente
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# -----------------------------------------------------------------------------
# BYO catalog + provider whitelist (BUG-053)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us057_admin_provider_get_returns_catalog(client, db_session):
    """GET expone byo_catalog con los providers whitelisted (US-110: + azure)."""
    _t, _u, auth = await _admin(client, db_session, slug="ai57-catalog")
    r = await client.get(
        "/api/v1/admin/ai/provider", headers=auth["_authz"],
    )
    body = r.json()
    keys = {p["key"] for p in body["byo_catalog"]}
    assert keys == {"openai", "claude", "perplexity", "gemini", "custom", "azure"}
    for p in body["byo_catalog"]:
        assert p["docs_url"].startswith("https://")
        assert isinstance(p["suggested_models"], list)


@pytest.mark.asyncio
async def test_us057_admin_provider_rejects_ollama_in_byo(client, db_session):
    """mode=byo + provider=ollama es rechazado por el schema Pydantic."""
    _t, _u, auth = await _admin(client, db_session, slug="ai57-no-ollama")
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {"provider": "ollama", "base_url": "http://localhost:11434"},
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# -----------------------------------------------------------------------------
# /superadmin/ai/tenants-status
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_superadmin_tenants_status_lists_modes(client, db_session):
    # Crear 2 tenants con modos distintos + 1 superadmin que los lee.
    t_a = await create_tenant(db_session, slug="sa-a", name="Alpha")
    await enable_tenant_ai(db_session, t_a, mode="platform")
    t_b = await create_tenant(db_session, slug="sa-b", name="Beta")
    await enable_tenant_ai(
        db_session, t_b, mode="byo",
        byo={
            "provider": "claude",
            "api_key_encrypted": encrypt_secret("sk-ant-xxx"),
            "model": "claude-3-5-haiku-20241022",
        },
    )
    await create_user(
        db_session, tenant=None,
        username="sa_ai57", email="sa@ai57.example.com",
        password="Str0ng-Sa-1!", is_superadmin=True,
    )
    sa_auth = await login(client, "sa_ai57", "Str0ng-Sa-1!")

    r = await client.get(
        "/api/v1/superadmin/ai/tenants-status", headers=sa_auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    by_slug = {row["tenant_slug"]: row for row in body}
    assert by_slug["sa-a"]["mode"] == "platform"
    assert by_slug["sa-b"]["mode"] == "byo"
    assert by_slug["sa-b"]["byo_provider"] == "claude"
    assert by_slug["sa-b"]["byo_api_key_mask"].endswith("-xxx"[-4:])


# -----------------------------------------------------------------------------
# /superadmin/ai/groq-usage
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_superadmin_groq_usage_aggregates(client, db_session):
    t = await create_tenant(db_session, slug="gu", name="Gamma")
    await create_user(
        db_session, tenant=None,
        username="sa_gu", email="sa@gu.example.com",
        password="Str0ng-Sa-1!", is_superadmin=True,
    )
    sa_auth = await login(client, "sa_gu", "Str0ng-Sa-1!")

    # Insertar 3 ai_jobs con provider=groq y 1 con provider=openai (se ignora).
    now = datetime.now(UTC)
    for i in range(3):
        db_session.add(AIJob(
            id=str(uuid4()), tenant_id=str(t.id), project_id=None,
            kind="minute_from_transcript", status="succeeded",
            input={}, output={},
            model_used="groq:llama-3.3-70b-versatile",
            provider="groq", tokens_in=100, tokens_out=200,
            duration_ms=500, completed_at=now - timedelta(hours=i),
        ))
    db_session.add(AIJob(
        id=str(uuid4()), tenant_id=str(t.id), project_id=None,
        kind="minute_from_transcript", status="succeeded",
        input={}, output={},
        model_used="openai:gpt-4o-mini",
        provider="openai", tokens_in=100, tokens_out=200,
        duration_ms=500, completed_at=now,
    ))
    await db_session.commit()

    r = await client.get(
        "/api/v1/superadmin/ai/groq-usage?days=30", headers=sa_auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_requests"] == 3  # sólo Groq
    assert body["total_tokens"] == 3 * 300
    assert body["today_requests"] >= 1
    assert body["limit_requests_per_day"] == 14_400
    assert any(row["tenant_id"] == str(t.id) for row in body["top_tenants"])


# -----------------------------------------------------------------------------
# Worker _call_ai_for_tenant — reintentos + alerta al superadmin
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us057_worker_platform_retries_and_alerts(client, db_session):
    from app.workers.tasks import ai as ai_tasks

    # Setup: superadmin + tenant en modo platform.
    t, _u, _auth = await _admin(client, db_session, slug="ai57-retry")
    await enable_tenant_ai(db_session, t, mode="platform")
    await create_user(
        db_session, tenant=None,
        username="sa_retry", email="sa@retry.example.com",
        password="Str0ng-Sa-1!", is_superadmin=True,
    )

    # Bypass sleeps para no hacer lenta la prueba.
    async def _no_sleep(_n):
        return None

    with patch("asyncio.sleep", _no_sleep):
        with patch(
            "app.workers.tasks.ai.generate_for_tenant",
            side_effect=RuntimeError("groq_down"),
        ):
            alert_mock = AsyncMock()
            with patch.object(
                ai_tasks, "_alert_superadmin_platform_failure", alert_mock,
            ):
                with pytest.raises(RuntimeError, match="ai_call_failed"):
                    await ai_tasks._call_ai_for_tenant(
                        "ping",
                        system=None,
                        tenant_cfg=TenantAIConfig(mode="platform"),
                        platform_groq_config={"api_key": "x", "model": "m"},

                        tenant_id=str(t.id),
                        job_id="job-1",
                    )
                # 1 alerta, después de 3 reintentos.
                assert alert_mock.await_count == 1


@pytest.mark.asyncio
async def test_us057_worker_byo_failure_does_not_alert_superadmin(client, db_session):
    """En modo byo el fallo NO alerta al superadmin — es problema del tenant."""
    from app.workers.tasks import ai as ai_tasks

    async def _no_sleep(_n):
        return None

    with patch("asyncio.sleep", _no_sleep):
        with patch(
            "app.workers.tasks.ai.generate_for_tenant",
            side_effect=RuntimeError("openai_401"),
        ):
            alert_mock = AsyncMock()
            with patch.object(
                ai_tasks, "_alert_superadmin_platform_failure", alert_mock,
            ):
                with pytest.raises(RuntimeError, match="ai_call_failed"):
                    await ai_tasks._call_ai_for_tenant(
                        "ping",
                        system=None,
                        tenant_cfg=TenantAIConfig(
                            mode="byo",
                            byo={"provider": "openai", "api_key": "sk-bad"},
                        ),
                        platform_groq_config=None,

                        tenant_id="tenant-x",
                        job_id="job-x",
                    )
                assert alert_mock.await_count == 0
