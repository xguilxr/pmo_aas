"""BUG-084 — fecha de creación (reported_at) respetada al crear + fecha
compromiso (committed_date) se guarda y se puede limpiar."""
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


# TC-084.1 — reported_at del form se respeta (no se fuerza "hoy").
@pytest.mark.asyncio
async def test_reported_at_respected_on_create(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={
            "title": "Acción de ayer", "type": "action", "area_id": area_id,
            "reported_at": "2026-06-28T00:00:00Z",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["reported_at"].startswith("2026-06-28")


# TC-084.2 — committed_date se guarda al crear y al actualizar; y se limpia.
@pytest.mark.asyncio
async def test_committed_date_roundtrip_and_clear(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={
            "title": "Acción", "type": "action", "area_id": area_id,
            "committed_date": "2026-07-01",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    iid = r.json()["id"]
    assert r.json()["committed_date"] == "2026-07-01"

    # Update a otra fecha → persiste.
    u = await client.patch(
        f"/api/v1/issues/{iid}", json={"committed_date": "2026-08-15"},
        headers=auth["_authz"],
    )
    assert u.status_code == 200
    assert u.json()["committed_date"] == "2026-08-15"

    # Limpiar (null) → se borra (BUG-084: exclude_unset).
    c = await client.patch(
        f"/api/v1/issues/{iid}", json={"committed_date": None},
        headers=auth["_authz"],
    )
    assert c.status_code == 200, c.text
    assert c.json()["committed_date"] is None


# TC-084.3 — risk due_date (F. Compromiso) round-trip + clear.
@pytest.mark.asyncio
async def test_risk_due_date_roundtrip_and_clear(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo", "probability": 2, "impact": 2,
            "area_id": area_id, "due_date": "2026-07-10",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["due_date"] == "2026-07-10"

    c = await client.patch(
        f"/api/v1/risks/{rid}", json={"due_date": None}, headers=auth["_authz"]
    )
    assert c.status_code == 200
    assert c.json()["due_date"] is None
