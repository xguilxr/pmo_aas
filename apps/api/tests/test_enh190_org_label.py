"""ENH-190 — Per-tenant configurable UI label (org_label).

Solo afecta el texto "Organización/Organizaciones" vs
"Portafolio/Portafolios" en el frontend. Cero cambios de
schema/rutas/APIs sobre la entidad Organization.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


@pytest.mark.asyncio
async def test_org_label_defaults_to_organizations(client, db_session):
    """TC-1: sin configurar, el settings GET y el branding público
    devuelven el default "organizations"."""
    _, auth = await _admin(client, db_session)

    r = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["settings"]["org_label"] == "organizations"

    b = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
    assert b.status_code == 200
    assert b.json()["org_label"] == "organizations"


@pytest.mark.asyncio
async def test_patch_org_label_persists_and_propagates_to_branding(client, db_session):
    """TC-2: PATCH admin/settings persiste "portfolios"; el GET de
    settings y el endpoint público de branding lo reflejan."""
    _, auth = await _admin(client, db_session, slug="clientco")

    r = await client.patch(
        "/api/v1/admin/settings",
        json={"org_label": "portfolios"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["org_label"] == "portfolios"

    g = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert g.status_code == 200
    assert g.json()["settings"]["org_label"] == "portfolios"

    b = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
    assert b.status_code == 200
    assert b.json()["org_label"] == "portfolios"


@pytest.mark.asyncio
async def test_patch_org_label_rejects_invalid_value(client, db_session):
    """TC-3: un valor fuera de {"organizations", "portfolios"} es rechazado."""
    _, auth = await _admin(client, db_session, slug="badco")

    r = await client.patch(
        "/api/v1/admin/settings",
        json={"org_label": "clients"},
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 422)

    # Setting doesn't get persisted / doesn't fall back silently to
    # the invalid value.
    g = await client.get("/api/v1/admin/settings", headers=auth["_authz"])
    assert g.json()["settings"]["org_label"] == "organizations"
