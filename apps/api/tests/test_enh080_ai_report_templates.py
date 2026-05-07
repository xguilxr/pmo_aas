"""ENH-080 — Plantillas reusables de reporte IA.

Cubre:
- TC-080.1: POST template + GET list → retorna entry creada.
- TC-080.2: DELETE template → GET list ya no la incluye.
- TC-080.3: Cross-project / cross-tenant access devuelve 404.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup_project(client, db_session):
    t = await create_tenant(db_session)
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
async def test_enh080_create_and_list_template(client, db_session):
    auth, proj = await _setup_project(client, db_session)
    payload = {
        "name": "Reporte semanal QBR",
        "base": "custom",
        "config": {
            "include_kpis": True,
            "include_tasks": False,
            "include_raid": True,
            "include_milestones": True,
            "free_notes": "Foco en hitos Q2",
            "criticalities": ["high"],
        },
    }
    r = await client.post(
        f"/api/v1/projects/{proj}/ai-report-templates",
        json=payload,
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    tpl = r.json()
    assert tpl["name"] == "Reporte semanal QBR"
    assert tpl["base"] == "custom"
    assert tpl["config"]["include_kpis"] is True
    assert tpl["config"]["criticalities"] == ["high"]

    listing = await client.get(
        f"/api/v1/projects/{proj}/ai-report-templates", headers=auth["_authz"]
    )
    assert listing.status_code == 200
    rows = listing.json()
    assert any(it["id"] == tpl["id"] for it in rows)


@pytest.mark.asyncio
async def test_enh080_delete_template(client, db_session):
    auth, proj = await _setup_project(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/ai-report-templates",
        json={"name": "T1", "base": "avance", "config": {}},
        headers=auth["_authz"],
    )
    tpl_id = r.json()["id"]
    d = await client.delete(
        f"/api/v1/ai-report-templates/{tpl_id}", headers=auth["_authz"]
    )
    assert d.status_code == 204
    listing = await client.get(
        f"/api/v1/projects/{proj}/ai-report-templates", headers=auth["_authz"]
    )
    assert all(it["id"] != tpl_id for it in listing.json())


@pytest.mark.asyncio
async def test_enh080_cross_tenant_returns_404(client, db_session):
    """Una plantilla de otro tenant no debe poder borrarse / cargarse."""
    auth_a, _ = await _setup_project(client, db_session)

    # Tenant B con su propio admin
    tb = await create_tenant(db_session, slug="beta", name="Beta")
    admin_role_b = await create_admin_role(db_session, tb)
    await create_user(
        db_session,
        tenant=tb,
        username="adminb",
        email="adminb@beta.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role_b],
    )
    auth_b = await login(client, "adminb", "Str0ng-Admin-1!")
    org_b = await client.post(
        "/api/v1/organizations", json={"name": "OrgB"}, headers=auth_b["_authz"]
    )
    me_b = await client.get("/api/v1/auth/me", headers=auth_b["_authz"])
    pb = await client.post(
        "/api/v1/projects",
        json={
            "name": "PB",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org_b.json()["id"],
            "pm_id": me_b.json()["id"],
        },
        headers=auth_b["_authz"],
    )
    proj_b = pb.json()["id"]
    r = await client.post(
        f"/api/v1/projects/{proj_b}/ai-report-templates",
        json={"name": "TB", "base": "avance", "config": {}},
        headers=auth_b["_authz"],
    )
    tpl_b_id = r.json()["id"]

    d = await client.delete(
        f"/api/v1/ai-report-templates/{tpl_b_id}", headers=auth_a["_authz"]
    )
    assert d.status_code == 404
