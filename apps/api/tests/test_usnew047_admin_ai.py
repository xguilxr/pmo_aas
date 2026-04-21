"""US-NEW-047 — Config y smoke del proveedor IA local (Tailscale).

Historia:
- US-NEW-045 (2026-04-20): cobertura original con CF-Access headers.
- US-NEW-047 (2026-04-21): refactor a Tailscale. Se eliminan los tests
  de persistencia de `cf_access_client_secret_encrypted`. Los de
  encrypt/decrypt/mask quedan con marker `legacy` porque el módulo
  sigue existiendo solo para leer secrets archivados (ver
  `app/services/ai_secrets.py` — DEPRECATED).
"""
from unittest.mock import patch

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


@pytest.mark.legacy
def test_legacy_fernet_roundtrip():
    """Encrypt/decrypt roundtrip — legacy flujo CF-Access (US-NEW-045).

    Se mantiene para que `auth_legacy.*` de tenants con secrets archivados
    se pueda seguir descifrando si se requiere consulta. No se usa en el
    flujo Tailscale (US-NEW-047+).
    """
    plain = "super-secret-token-abc123"
    enc = encrypt_secret(plain)
    assert enc.startswith("enc::")
    assert plain not in enc
    assert decrypt_secret(enc) == plain


@pytest.mark.legacy
def test_legacy_mask_secret():
    assert mask_secret("abcdef1234") == "••••••1234"
    assert mask_secret("abcd") == "••••"
    assert mask_secret("") == ""


@pytest.mark.asyncio
async def test_usnew047_get_empty_config(client, db_session):
    _, auth = await _admin(client, db_session)
    r = await client.get("/api/v1/admin/ai/ollama", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is False
    assert body["base_url"] is None
    # Campos CF-Access ya no forman parte del shape.
    assert "cf_access_client_id" not in body
    assert "cf_access_client_secret_masked" not in body


@pytest.mark.asyncio
async def test_usnew047_patch_persists_tailscale_config(client, db_session):
    t, auth = await _admin(client, db_session, slug="ai-b")
    r = await client.patch(
        "/api/v1/admin/ai/ollama",
        json={
            "base_url": "http://ollama-host.test.ts.net:11434",
            "model": "qwen2.5:7b-instruct-q4_K_M",
            "timeout_sec": 60,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configured"] is True
    assert body["base_url"] == "http://ollama-host.test.ts.net:11434"
    assert body["model"] == "qwen2.5:7b-instruct-q4_K_M"
    assert body["timeout_sec"] == 60

    # BD: la rama activa no contiene campos CF-Access
    await db_session.refresh(t)
    fresh = (
        await db_session.execute(select(Tenant).where(Tenant.id == t.id))
    ).scalar_one()
    persisted = fresh.settings["ai"]["ollama"]
    assert persisted["base_url"] == "http://ollama-host.test.ts.net:11434"
    assert "cf_access_client_id" not in persisted
    assert "cf_access_client_secret_encrypted" not in persisted


@pytest.mark.asyncio
async def test_usnew047_patch_archives_legacy_cf_access(client, db_session):
    """Si el tenant tiene config CF-Access legacy en BD, el PATCH la archiva
    bajo `auth_legacy.*` y deja limpia la rama activa."""
    t, auth = await _admin(client, db_session, slug="ai-legacy")
    merged = dict(t.settings or {})
    merged["ai"] = {
        "ollama": {
            "base_url": "https://ollama.old.example.com",
            "cf_access_client_id": "legacy-id",
            "cf_access_client_secret_encrypted": "enc::legacy-ciphertext",
        }
    }
    t.settings = merged
    await db_session.commit()

    r = await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"base_url": "http://ollama-host.test.ts.net:11434"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text

    await db_session.refresh(t)
    fresh = (
        await db_session.execute(select(Tenant).where(Tenant.id == t.id))
    ).scalar_one()
    cfg = fresh.settings["ai"]["ollama"]
    # Rama activa limpia
    assert cfg["base_url"] == "http://ollama-host.test.ts.net:11434"
    assert "cf_access_client_id" not in cfg
    assert "cf_access_client_secret_encrypted" not in cfg
    # Archivo legacy presente
    assert cfg["auth_legacy"]["cf_access_client_id"] == "legacy-id"
    assert cfg["auth_legacy"]["cf_access_client_secret_encrypted"] == "enc::legacy-ciphertext"


@pytest.mark.asyncio
async def test_usnew047_test_connection_not_configured(client, db_session):
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
async def test_usnew047_test_connection_ok_no_auth_headers(client, db_session):
    """El GET /api/tags del test-connection NO debe mandar headers CF-Access."""
    _, auth = await _admin(client, db_session, slug="ai-e")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={
            "base_url": "http://ollama-host.test.ts.net:11434",
            "model": "qwen2.5:7b-instruct-q4_K_M",
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
        request=httpx.Request(
            "GET", "http://ollama-host.test.ts.net:11434/api/tags"
        ),
    )

    captured_headers: dict[str, str] = {}

    async def _fake_get(self, url, *args, **kwargs):  # noqa: ANN001
        for k, v in self.headers.items():
            captured_headers[k.lower()] = v
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

    # Verificación clave: NO debe haber headers CF-Access-*
    assert "cf-access-client-id" not in captured_headers
    assert "cf-access-client-secret" not in captured_headers


@pytest.mark.asyncio
async def test_usnew047_test_connection_timeout(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-f")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"base_url": "http://ollama-host.test.ts.net:11434"},
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
async def test_usnew047_test_connection_http_error(client, db_session):
    _, auth = await _admin(client, db_session, slug="ai-g")
    await client.patch(
        "/api/v1/admin/ai/ollama",
        json={"base_url": "http://ollama-host.test.ts.net:11434"},
        headers=auth["_authz"],
    )

    async def _fake_get(self, url, *args, **kwargs):  # noqa: ANN001
        return httpx.Response(
            502,
            text="bad gateway",
            request=httpx.Request(
                "GET", "http://ollama-host.test.ts.net:11434/api/tags"
            ),
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
    assert "502" in body["error"]


@pytest.mark.asyncio
async def test_usnew047_non_admin_forbidden(client, db_session):
    tenant, _auth_admin = await _admin(client, db_session, slug="ai-rbac")
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
