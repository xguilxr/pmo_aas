"""US-031 — Upload y display del logo del tenant en chrome."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.core.config import settings
from tests.factories import create_admin_role, create_tenant, create_user, login

# 1x1 PNG (smallest valid PNG)
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc\xff"
    b"\xff?\x03\x00\x08\xfc\x02\xfe\xa7\xad\xde\x8c\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def _admin(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com", password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _non_admin(client, db_session, tenant, username="member"):
    await create_user(
        db_session, tenant=tenant, username=username,
        email=f"{username}@{tenant.slug}.example.com", password="Str0ng-User-1!",
    )
    return await login(client, username, "Str0ng-User-1!")


def _cleanup(tenant_id: str) -> None:
    base = Path(settings.STORAGE_PATH) / "tenants" / str(tenant_id)
    if base.exists():
        for f in base.iterdir():
            f.unlink(missing_ok=True)
        base.rmdir()


@pytest.mark.asyncio
async def test_us031_upload_png_sets_logo_url(client, db_session):
    # BUG-068: el logo se guarda como data-URL base64 en DB (no como serve URL).
    import base64

    t, auth = await _admin(client, db_session, slug="logo-ok")
    try:
        r = await client.post(
            "/api/v1/admin/tenant/logo",
            files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
            headers=auth["_authz"],
        )
        assert r.status_code == 200, r.text
        logo_url = r.json()["logo_url"]
        assert logo_url.startswith("data:image/png;base64,")
        # El data-URL decodifica al PNG original.
        b64 = logo_url.split(",", 1)[1]
        assert base64.b64decode(b64) == PNG_BYTES

        info = await client.get("/api/v1/admin/tenant", headers=auth["_authz"])
        assert info.json()["logo_url"] == logo_url
    finally:
        _cleanup(str(t.id))


@pytest.mark.asyncio
async def test_us031_upload_rejects_oversized(client, db_session):
    t, auth = await _admin(client, db_session, slug="logo-big")
    try:
        huge = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 10)
        r = await client.post(
            "/api/v1/admin/tenant/logo",
            files={"file": ("big.png", io.BytesIO(huge), "image/png")},
            headers=auth["_authz"],
        )
        assert r.status_code == 413, r.text
    finally:
        _cleanup(str(t.id))


@pytest.mark.asyncio
async def test_us031_upload_rejects_bad_mime(client, db_session):
    t, auth = await _admin(client, db_session, slug="logo-exe")
    try:
        r = await client.post(
            "/api/v1/admin/tenant/logo",
            files={"file": ("m.exe", io.BytesIO(b"MZ\x90"), "application/x-msdownload")},
            headers=auth["_authz"],
        )
        assert r.status_code == 400, r.text
    finally:
        _cleanup(str(t.id))


@pytest.mark.asyncio
async def test_us031_non_admin_cannot_upload(client, db_session):
    t, _admin_auth = await _admin(client, db_session, slug="logo-rbac")
    user_auth = await _non_admin(client, db_session, t)
    r = await client.post(
        "/api/v1/admin/tenant/logo",
        files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=user_auth["_authz"],
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_us031_cross_tenant_serve_blocked(client, db_session):
    t_a, auth_a = await _admin(client, db_session, slug="logo-a")
    t_b, _ = await _admin(client, db_session, slug="logo-b")
    try:
        up = await client.post(
            "/api/v1/admin/tenant/logo",
            files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
            headers=auth_a["_authz"],
        )
        assert up.status_code == 200
        # Admin de tenant A intenta pegarle al logo de tenant B
        r = await client.get(
            f"/api/v1/branding/tenants/{t_b.id}/logo", headers=auth_a["_authz"],
        )
        assert r.status_code == 404
    finally:
        _cleanup(str(t_a.id))
        _cleanup(str(t_b.id))


@pytest.mark.asyncio
async def test_us031_delete_logo(client, db_session):
    t, auth = await _admin(client, db_session, slug="logo-del")
    try:
        await client.post(
            "/api/v1/admin/tenant/logo",
            files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
            headers=auth["_authz"],
        )
        r = await client.delete("/api/v1/admin/tenant/logo", headers=auth["_authz"])
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        assert r.json()["logo_url"] is None
        # Serve ahora 404
        r2 = await client.get(
            f"/api/v1/branding/tenants/{t.id}/logo", headers=auth["_authz"],
        )
        assert r2.status_code == 404
    finally:
        _cleanup(str(t.id))


@pytest.mark.asyncio
async def test_us031_me_tenant_branding(client, db_session):
    t, auth = await _admin(client, db_session, slug="branding-me")
    try:
        r = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
        assert r.status_code == 200
        body = r.json()
        assert body["tenant_name"] == "branding-me"
        assert body["tenant_slug"] == "branding-me"
        assert body["logo_url"] is None

        await client.post(
            "/api/v1/admin/tenant/logo",
            files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
            headers=auth["_authz"],
        )
        r2 = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
        assert r2.json()["logo_url"].startswith("data:image/png;base64,")
    finally:
        _cleanup(str(t.id))


@pytest.mark.asyncio
async def test_us031_overwrite_replaces_logo(client, db_session):
    """BUG-068: subir un WEBP después de un PNG reemplaza el data-URL."""
    t, auth = await _admin(client, db_session, slug="logo-swap")
    await client.post(
        "/api/v1/admin/tenant/logo",
        files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=auth["_authz"],
    )
    # Contenido no importa — validamos el MIME header
    await client.post(
        "/api/v1/admin/tenant/logo",
        files={"file": ("logo.webp", io.BytesIO(b"RIFF....WEBP"), "image/webp")},
        headers=auth["_authz"],
    )
    info = await client.get("/api/v1/admin/tenant", headers=auth["_authz"])
    assert info.json()["logo_url"].startswith("data:image/webp;base64,")
