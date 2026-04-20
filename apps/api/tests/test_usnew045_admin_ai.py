"""US-NEW-045 — Config y smoke del proveedor IA local (Cloudflare Tunnel)."""
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from app.services.ai_secrets import decrypt_secret, encrypt_secret, mask_secret
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="ai-a"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


def test_usnew045_encrypt_decrypt_roundtrip():
    plain = "super-secret-token-abc123"
    enc = encrypt_secret(plain)
    assert enc.startswith("enc::")
    assert plain not in enc
    assert decrypt_secret(enc) == plain


def test_usnew045_mask_secret():
    assert mask_secret("abcdef1234") == "••••••1234"
    assert mask_secret("abcd") == "••••"
    assert mask_secret("") == ""


@pytest.mark.asyncio
async def test_usnew045_get_empty_config(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.get("/api/v1/admin/ai/ollama", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is False
    assert body["base_url"] is None
    assert body["cf_access_client_secret_masked"] is None


@pytest.mark.asyncio
async def test_usnew045_patch_persists_encrypted(client, db_session):
    t, auth = await _admin(client, db_session, slug="ai-b")
    r = await client.patch(
        "/api/v1/admin/ai/ollama",
        json={
            "base_url": "https://ollama.example.com",
            "model": "qwen2.5:7b-instruct-q4_K_M",
            "timeout_sec": 60,
            "cf_access_client_id": "client-id-123",
            "cf_access_client_secret": "shhh-secret-value-xyz",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is True
    assert body["base_url"] == "https://ollama.example.com"
    assert body["cf_access_client_id"] == "client-id-123"
    # El secret masked NO es el plaintext
    assert body["cf_access_client_secret_masked"] is not None
    assert "shhh" not in body["cf_access_client_secret_masked"]

    # Verifica en BD que se guardó cifrado
    await db_session.refresh(t)
    fresh = (
        await db_session.execute(select(Tenant).where(Tenant.id == t.id))
    ).scalar_one()
    persisted = fresh.settings["ai"]["ollama"]["cf_access_client_secret_encrypted"]
    assert persisted.startswith("enc::")
    assert "shhh" not in persisted
    assert decrypt_secret(persisted) == "shhh-secret-value-xyz"


@pytest.mark.asyncio
async def test_usnew045_clear_secret(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-c")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={
            "base_url": "https://ollama.example.com",
            "cf_access_client_id": "x",
            "cf_access_client_secret": "old",
        },
        headers=auth["_authz"],
    )
    r = await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"clear_secret": True},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["cf_access_client_secret_masked"] is None


@pytest.mark.asyncio
async def test_usnew045_test_connection_not_configured(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-d")
    r = await client.post(
        "/api/v1/admin/ai/test-connection",
        json={"provider": "ollama"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["code"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_usnew045_test_connection_ok_mocked(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-e")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={
            "base_url": "https://ollama.example.com",
            "model": "qwen2.5:7b-instruct-q4_K_M",
            "cf_access_client_id": "x",
            "cf_access_client_secret": "y",
        },
        headers=auth["_authz"],
    )

    mock_response = httpx.Response(
        200,
        json={
            "models": [
                {"name": "qwen2.5:7b-instruct-q4_K_M"},
                {"name": "llama3:latest"},
            ]
        },
        request=httpx.Request("GET", "https://ollama.example.com/api/tags"),
    )

    async def _fake_get(self, url, *args, **kwargs):  # noqa: ANN001
        return mock_response

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        r = await client.post(
            "/api/v1/admin/ai/test-connection",
            json={"provider": "ollama"},
            headers=auth["_authz"],
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["tags_count"] == 2
    assert body["model_present"] is True
    assert body["latency_ms"] is not None


@pytest.mark.asyncio
async def test_usnew045_test_connection_timeout(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-f")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"base_url": "https://ollama.example.com"},
        headers=auth["_authz"],
    )

    async def _fake_get(self, url, *args, **kwargs):  # noqa: ANN001
        raise httpx.TimeoutException("timeout")

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        r = await client.post(
            "/api/v1/admin/ai/test-connection",
            json={"provider": "ollama"},
            headers=auth["_authz"],
        )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["code"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_usnew045_test_connection_http_error(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-g")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"base_url": "https://ollama.example.com"},
        headers=auth["_authz"],
    )

    async def _fake_get(self, url, *args, **kwargs):  # noqa: ANN001
        return httpx.Response(
            401,
            text="forbidden",
            request=httpx.Request("GET", "https://ollama.example.com/api/tags"),
        )

    with patch.object(httpx.AsyncClient, "get", new=_fake_get):
        r = await client.post(
            "/api/v1/admin/ai/test-connection",
            json={"provider": "ollama"},
            headers=auth["_authz"],
        )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["code"] == "HTTP_ERROR"
    assert "401" in body["error"]


@pytest.mark.asyncio
async def test_usnew045_non_admin_forbidden(client, db_session):
    tenant, auth_admin = await _admin(client, db_session, slug="ai-rbac")
    await create_user(
        db_session, tenant=tenant, username="member",
        email="m@ai-rbac.example.com", password="Str0ng-m-1!",
    )
    member = await login(client, "member", "Str0ng-m-1!")
    r = await client.get("/api/v1/admin/ai/ollama", headers=member["_authz"])
    assert r.status_code == 403
    r2 = await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"model": "x"},
        headers=member["_authz"],
    )
    assert r2.status_code == 403
