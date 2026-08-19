"""US-033 — Panel de organización con recursos reales."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _member(client, db_session, tenant, username="member"):
    await create_user(
        db_session, tenant=tenant, username=username,
        email=f"{username}@{tenant.slug}.example.com", password="Str0ng-User-1!",
    )
    return await login(client, username, "Str0ng-User-1!")


@pytest.mark.asyncio
async def test_us033_panel_happy_path(client, db_session):
    _, auth = await _admin(client, db_session, slug="panel-a")

    org = await client.post(
        "/api/v1/organizations",
        json={"name": "Org A", "industry": "IT", "country": "MX"},
        headers=auth["_authz"],
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["id"]

    pf = await client.post(
        f"/api/v1/organizations/{org_id}/portfolios",
        json={"name": "Cartera-1"},
        headers=auth["_authz"],
    )
    assert pf.status_code == 201, pf.text
    pf_id = pf.json()["id"]

    prog = await client.post(
        "/api/v1/programs",
        json={"name": "Prog-1", "organization_id": org_id, "portfolio_id": pf_id},
        headers=auth["_authz"],
    )
    assert prog.status_code == 201, prog.text
    prog_id = prog.json()["id"]

    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()
    proj = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto-1", "description": "desc", "type": "innovation",
            "priority": 3, "organization_id": org_id, "program_id": prog_id,
            "pm_id": me["id"], "budget": "1000",
        },
        headers=auth["_authz"],
    )
    assert proj.status_code == 201, proj.text

    r = await client.get(
        f"/api/v1/organizations/{org_id}/panel", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == org_id
    assert data["name"] == "Org A"
    assert data["is_active"] is True
    # US-199 — la jerarquía del panel es portafolio ⊃ programa (ADR-037).
    assert len(data["portfolios"]) == 1
    assert data["portfolios"][0]["name"] == "Cartera-1"
    assert [p["name"] for p in data["portfolios"][0]["programs"]] == ["Prog-1"]
    assert data["portfolios"][0]["active_project_count"] == 1
    assert len(data["programs"]) == 1
    assert data["programs"][0]["name"] == "Prog-1"
    assert data["programs"][0]["active_project_count"] == 1
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "Proyecto-1"
    assert data["projects"][0]["pm_id"] == me["id"]
    assert data["projects"][0]["pm_name"] == me.get("full_name")
    assert len(data["users"]) == 1
    assert data["users"][0]["role"] == "pm"


@pytest.mark.asyncio
async def test_us033_panel_non_admin_can_read(client, db_session):
    tenant, admin_auth = await _admin(client, db_session, slug="panel-b")
    user_auth = await _member(client, db_session, tenant)

    org = await client.post(
        "/api/v1/organizations",
        json={"name": "Org B"},
        headers=admin_auth["_authz"],
    )
    assert org.status_code == 201
    org_id = org.json()["id"]

    # Un user sin permisos admin puede leer el panel (auth-only)
    r = await client.get(
        f"/api/v1/organizations/{org_id}/panel", headers=user_auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Org B"


@pytest.mark.asyncio
async def test_us033_panel_cross_tenant_404(client, db_session):
    _, auth_a = await _admin(client, db_session, slug="panel-c")
    _, auth_b = await _admin(client, db_session, slug="panel-d")

    org = await client.post(
        "/api/v1/organizations",
        json={"name": "Org-C"},
        headers=auth_a["_authz"],
    )
    assert org.status_code == 201
    org_id = org.json()["id"]

    r = await client.get(
        f"/api/v1/organizations/{org_id}/panel", headers=auth_b["_authz"]
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_us033_panel_empty_org(client, db_session):
    _, auth = await _admin(client, db_session, slug="panel-e")
    org = await client.post(
        "/api/v1/organizations",
        json={"name": "Org-E"},
        headers=auth["_authz"],
    )
    assert org.status_code == 201
    org_id = org.json()["id"]

    r = await client.get(
        f"/api/v1/organizations/{org_id}/panel", headers=auth["_authz"]
    )
    assert r.status_code == 200
    body = r.json()
    assert body["portfolios"] == []
    assert body["programs"] == []
    assert body["projects"] == []
    assert body["users"] == []
