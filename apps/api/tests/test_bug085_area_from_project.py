"""BUG-085 — crear área desde un proyecto deriva el organization_id del
proyecto y auto-crea el AreaAssignment del scope (propagación)."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1", "description": "d", "type": "innovation",
            "priority": 3, "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return t, auth, r.json()["id"], org_id


# TC-085.1 — crear área con project_id (sin organization_id) → 201,
# org derivado del proyecto, visible en by-project y asignable a RAID.
@pytest.mark.asyncio
async def test_tc085_1_create_area_from_project(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)

    r = await client.post(
        "/api/v1/areas",
        json={"name": "Compras", "project_id": proj_id},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    area = r.json()
    assert area["organization_id"] == org_id  # derivado del proyecto

    # Visible en la cascada del proyecto (auto-assignment).
    by_proj = await client.get(
        f"/api/v1/admin/areas/by-project/{proj_id}", headers=auth["_authz"]
    )
    assert by_proj.status_code == 200
    assert any(a["id"] == area["id"] for a in by_proj.json())

    # Asignable a un riesgo del proyecto (pasa _validate_area).
    rk = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo en área nueva", "probability": 3, "impact": 3,
            "area_id": area["id"],
        },
        headers=auth["_authz"],
    )
    assert rk.status_code == 201, rk.text


# TC-085.2 — área creada a nivel organización se propaga a los proyectos
# hijos (visible vía by-project por la cascada org).
@pytest.mark.asyncio
async def test_tc085_2_org_area_propagates_to_children(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)

    r = await client.post(
        "/api/v1/areas",
        json={"name": "Legal", "organization_id": org_id},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    area = r.json()

    by_proj = await client.get(
        f"/api/v1/admin/areas/by-project/{proj_id}", headers=auth["_authz"]
    )
    assert any(a["id"] == area["id"] for a in by_proj.json()), (
        "área de org debe propagarse al proyecto hijo"
    )


# TC-085.3 — sin scope alguno → 400 (validation_error).
@pytest.mark.asyncio
async def test_tc085_3_requires_scope(client, db_session):
    _, auth, _proj_id, _org_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/areas", json={"name": "Sin scope"}, headers=auth["_authz"]
    )
    assert r.status_code == 400


# TC-085.4 — project_id inexistente → 400.
@pytest.mark.asyncio
async def test_tc085_4_bad_project(client, db_session):
    _, auth, _proj_id, _org_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/areas",
        json={"name": "Xx", "project_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth["_authz"],
    )
    assert r.status_code == 400
