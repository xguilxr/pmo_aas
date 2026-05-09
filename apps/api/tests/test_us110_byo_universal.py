"""US-110 — BYO universal (custom OpenAI-compatible) + Azure OpenAI.

Cubre:
- Provider whitelist incluye `custom` y `azure`.
- `custom` exige `acknowledge_security=True` para guardar (CA3).
- `azure` exige `base_url` (resource endpoint) + `deployment_name` (CA5/CA6).
- BYOConfigRead expone deployment, api_version, rate_limit_rpm,
  daily_token_limit y acknowledge_security (CA4).
- `_ping_byo_provider` para `azure` arma URL Azure y usa header api-key.
- `_ping_byo_provider` para `custom` falla con HTTP_ERROR cuando el
  endpoint regresa 401 (TC-110.3).
- `tenant_ai.load_tenant_ai` propaga deployment + api_version + límites.
- `AzureProvider.generate` consulta el deployment correcto (TC-110.2).
- Catálogo BYO público incluye `azure` y `custom` con metadata UX.
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.api.v1.endpoints import admin_ai as admin_ai_mod

# Capturar referencia REAL antes de que conftest._stub_ai_providers reemplace
# el atributo `_ping_byo_provider` del módulo con un stub ok=True.
from app.api.v1.endpoints.admin_ai import _ping_byo_provider as _real_ping
from app.services.ai.byo_catalog import catalog_for_api
from app.services.ai.provider import (
    _PROVIDERS,
    BYO_PROVIDERS,
    AzureProvider,
)
from app.services.ai.tenant_ai import load_tenant_ai
from app.services.ai_secrets import encrypt_secret
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    enable_tenant_ai,
    login,
)

# Capturar generate REAL de AzureProvider antes que conftest._stub_ai_providers
# lo reemplace con el stub DisabledProvider.
_AZURE_GENERATE = AzureProvider.generate


async def _admin(client, db_session, slug="ai110"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


# -----------------------------------------------------------------------------
# Whitelist + catálogo público
# -----------------------------------------------------------------------------

def test_us110_whitelist_includes_custom_and_azure():
    assert "custom" in BYO_PROVIDERS
    assert "azure" in BYO_PROVIDERS
    assert "azure" in _PROVIDERS


def test_us110_catalog_exposes_azure_and_custom_metadata():
    keys = {entry["key"]: entry for entry in catalog_for_api()}
    assert "azure" in keys
    assert keys["azure"].get("requires_azure_fields") is True
    assert keys["azure"]["base_url_hint"].startswith("https://")
    assert "custom" in keys
    assert keys["custom"].get("requires_security_ack") is True
    assert "responsable de la seguridad" in keys["custom"]["security_warning"]


# -----------------------------------------------------------------------------
# PATCH endpoint
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us110_patch_custom_requires_security_ack(client, db_session):
    """Provider=custom sin acknowledge_security → 422 BYO_SECURITY_ACK_REQUIRED."""
    _t, auth = await _admin(client, db_session, slug="ai110-ack-fail")
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {
                "provider": "custom",
                "api_key": "sk-customkey-1234",
                "base_url": "https://api.together.xyz/v1",
                "model": "meta-llama/Llama-3-70b-chat-hf",
            },
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail.get("code") == "BYO_SECURITY_ACK_REQUIRED"


@pytest.mark.asyncio
async def test_us110_patch_custom_with_ack_persists_limits(client, db_session):
    """Provider=custom con ack=True guarda + persiste rate/token limits."""
    _t, auth = await _admin(client, db_session, slug="ai110-ack-ok")
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {
                "provider": "custom",
                "api_key": "sk-customkey-1234",
                "base_url": "https://api.together.xyz/v1",
                "model": "meta-llama/Llama-3-70b-chat-hf",
                "acknowledge_security": True,
                "rate_limit_rpm": 60,
                "daily_token_limit": 500_000,
            },
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["byo"]["provider"] == "custom"
    assert body["byo"]["base_url"] == "https://api.together.xyz/v1"
    assert body["byo"]["acknowledge_security"] is True
    assert body["byo"]["rate_limit_rpm"] == 60
    assert body["byo"]["daily_token_limit"] == 500_000


@pytest.mark.asyncio
async def test_us110_patch_azure_requires_deployment(client, db_session):
    _t, auth = await _admin(client, db_session, slug="ai110-az-no-dep")
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {
                "provider": "azure",
                "api_key": "az-key-1234",
                "base_url": "https://my-resource.openai.azure.com",
            },
        },
        headers=auth["_authz"],
    )
    # Pydantic validator dispara 422 antes de llegar al ack check.
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_us110_patch_azure_full_payload_persists(client, db_session):
    """TC-110.2: configurar Azure OpenAI con deployment → reporte funciona."""
    _t, auth = await _admin(client, db_session, slug="ai110-az-ok")
    r = await client.patch(
        "/api/v1/admin/ai/provider",
        json={
            "mode": "byo",
            "byo": {
                "provider": "azure",
                "api_key": "az-key-1234",
                "base_url": "https://my-resource.openai.azure.com",
                "deployment_name": "gpt-4o-prod",
                "api_version": "2024-02-15-preview",
                "model": "gpt-4o",
                "rate_limit_rpm": 30,
            },
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["byo"]["provider"] == "azure"
    assert body["byo"]["deployment_name"] == "gpt-4o-prod"
    assert body["byo"]["api_version"] == "2024-02-15-preview"
    assert body["byo"]["rate_limit_rpm"] == 30


@pytest.mark.asyncio
async def test_us110_patch_test_failure_blocks_save(client, db_session):
    """TC-110.3: API key inválida → error claro pre-save (test-before-save)."""
    _t, auth = await _admin(client, db_session, slug="ai110-test-fail")

    async def _fail_ping(*_args, **_kwargs):
        return admin_ai_mod.TestConnectionResult(
            ok=False, latency_ms=12,
            error="HTTP 401: invalid api key", code="HTTP_ERROR",
        )

    with patch.object(admin_ai_mod, "_ping_byo_provider", _fail_ping):
        r = await client.patch(
            "/api/v1/admin/ai/provider",
            json={
                "mode": "byo",
                "byo": {
                    "provider": "custom",
                    "api_key": "sk-bad",
                    "base_url": "https://api.example.com/v1",
                    "acknowledge_security": True,
                },
            },
            headers=auth["_authz"],
        )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "BYO_TEST_FAILED"
    assert "401" in (detail.get("ping_error") or "")


# -----------------------------------------------------------------------------
# tenant_ai.load_tenant_ai propagation
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us110_load_tenant_ai_propagates_azure_fields(client, db_session):
    t, _auth = await _admin(client, db_session, slug="ai110-load-az")
    await enable_tenant_ai(
        db_session, t, mode="byo",
        byo={
            "provider": "azure",
            "api_key_encrypted": encrypt_secret("az-key-xyz"),
            "model": "gpt-4o",
            "base_url": "https://r.openai.azure.com",
            "deployment_name": "gpt-4o-prod",
            "api_version": "2024-02-15-preview",
            "rate_limit_rpm": 60,
            "daily_token_limit": 1_000_000,
        },
    )
    cfg = await load_tenant_ai(db_session, t.id)
    assert cfg.mode == "byo"
    assert cfg.byo is not None
    assert cfg.byo["provider"] == "azure"
    assert cfg.byo["deployment_name"] == "gpt-4o-prod"
    assert cfg.byo["api_version"] == "2024-02-15-preview"
    assert cfg.byo["rate_limit_rpm"] == 60
    assert cfg.byo["daily_token_limit"] == 1_000_000


# -----------------------------------------------------------------------------
# _ping_byo_provider Azure branch
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us110_ping_azure_builds_correct_url(monkeypatch):
    """Azure ping debe POSTear a {endpoint}/openai/deployments/.../chat/completions."""
    captured: dict = {}

    class _MockClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json

            class _Resp:
                status_code = 200
                text = "ok"

                def json(self):
                    return {}

            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await _real_ping(
        "azure", "az-key", model=None,
        base_url="https://my-r.openai.azure.com",
        deployment_name="gpt-4o-prod",
        api_version="2024-02-15-preview",
    )
    assert result.ok is True
    assert "openai/deployments/gpt-4o-prod/chat/completions" in captured["url"]
    assert "api-version=2024-02-15-preview" in captured["url"]
    assert captured["headers"]["api-key"] == "az-key"
    assert "Authorization" not in captured["headers"]


@pytest.mark.asyncio
async def test_us110_ping_azure_missing_deployment_short_circuits():
    result = await _real_ping(
        "azure", "az-key", model=None,
        base_url="https://my-r.openai.azure.com",
    )
    assert result.ok is False
    assert result.code == "NO_DEPLOYMENT"


# -----------------------------------------------------------------------------
# AzureProvider.generate
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_us110_azure_provider_generate_uses_deployment(monkeypatch):
    captured: dict = {}

    class _Resp:
        status_code = 200
        text = "ok"

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "azure pong"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7},
            }

    class _MockClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await _AZURE_GENERATE(
        AzureProvider(),
        "ping",
        system="sys",
        override={
            "api_key": "az-key",
            "base_url": "https://my-r.openai.azure.com",
            "deployment_name": "gpt-4o-prod",
            "api_version": "2024-02-15-preview",
            "tenant_id": "tenant-x",
        },
    )
    assert result.text == "azure pong"
    assert result.model == "azure:gpt-4o-prod"
    assert result.tokens_in == 5
    assert result.tokens_out == 7
    assert "openai/deployments/gpt-4o-prod" in captured["url"]
    # System message + user prompt llegan en messages.
    assert any(m["role"] == "system" for m in captured["json"]["messages"])
    assert any(m["role"] == "user" for m in captured["json"]["messages"])


@pytest.mark.asyncio
async def test_us110_azure_provider_missing_deployment_raises():
    with pytest.raises(RuntimeError, match="azure_no_deployment_name"):
        await _AZURE_GENERATE(
            AzureProvider(),
            "x",
            override={
                "api_key": "k",
                "base_url": "https://r.openai.azure.com",
            },
        )
