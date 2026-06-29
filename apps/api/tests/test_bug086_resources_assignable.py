"""BUG-086 — recursos (actores) asignados a un área del proyecto deben ser
asignables como responsables en RAID (eligible-actors + by-project/actors)."""
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
    proj_id = r.json()["id"]
    a = await client.post(
        "/api/v1/areas",
        json={"name": "Infra", "project_id": proj_id},
        headers=auth["_authz"],
    )
    return t, auth, proj_id, a.json()["id"]


# TC-086.1 — un actor con area_id directo (sin team/user/lead) a un área
# visible del proyecto aparece en by-project/actors y eligible-actors.
@pytest.mark.asyncio
async def test_area_direct_actor_is_assignable(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    # Recurso cargado directo al área (caso que antes quedaba excluido).
    ac = await client.post(
        "/api/v1/actors",
        json={"name": "Recurso Infra", "area_id": area_id},
        headers=auth["_authz"],
    )
    assert ac.status_code == 201, ac.text
    actor_id = ac.json()["id"]

    by_proj = await client.get(
        f"/api/v1/admin/areas/by-project/{proj_id}/actors", headers=auth["_authz"]
    )
    assert by_proj.status_code == 200
    assert any(a["id"] == actor_id for a in by_proj.json()), (
        "recurso de área del proyecto debe ser asignable (by-project/actors)"
    )

    eligible = await client.get(
        f"/api/v1/projects/{proj_id}/eligible-actors", headers=auth["_authz"]
    )
    assert eligible.status_code == 200
    assert any(a["id"] == actor_id for a in eligible.json()), (
        "recurso de área del proyecto debe aparecer en eligible-actors"
    )

    # Y es asignable como responsable de un riesgo (owner_actor_id).
    rk = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo", "probability": 2, "impact": 2,
            "area_id": area_id, "owner_actor_id": actor_id,
        },
        headers=auth["_authz"],
    )
    assert rk.status_code == 201, rk.text
    assert rk.json()["owner_actor_id"] == actor_id
