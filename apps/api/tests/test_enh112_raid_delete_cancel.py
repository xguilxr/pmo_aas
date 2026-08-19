"""ENH-112 — Borrar / cancelar tickets de RAID, Lecciones y Cambios.

- Riesgos / Incidentes / Lecciones: soft-delete (DELETE → 204, desaparece
  de la lista).
- Cambios: soft-delete (borrar) Y cancelar (status='cancelled', queda
  visible). Cualquier miembro del proyecto puede hacerlo.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    r = await client.post("/api/v1/projects", json={
        "name": "P1", "description": "d", "type": "innovacion", "priority": 3,
        "organization_id": org_id, "pm_id": pm_id,
    }, headers=auth["_authz"])
    proj_id = r.json()["id"]
    ra = await client.post("/api/v1/areas", json={"name": "Default Area", "organization_id": org_id}, headers=auth["_authz"])
    area_id = ra.json()["id"]
    await client.put(
        f"/api/v1/admin/areas/{area_id}/assignments",
        json={"scopes": [{"project_id": proj_id}]},
        headers=auth["_authz"],
    )
    return t, auth, proj_id, area_id


@pytest.mark.asyncio
async def test_delete_risk_removes_from_list(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={"title": "R1", "probability": 3, "impact": 3, "area_id": area_id},
        headers=auth["_authz"],
    )
    rid = r.json()["id"]
    d = await client.delete(f"/api/v1/risks/{rid}", headers=auth["_authz"])
    assert d.status_code == 204
    lst = await client.get(f"/api/v1/projects/{proj_id}/risks", headers=auth["_authz"])
    assert all(x["id"] != rid for x in lst.json())


@pytest.mark.asyncio
async def test_delete_issue_removes_from_list(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={"title": "I1", "type": "action", "area_id": area_id},
        headers=auth["_authz"],
    )
    iid = r.json()["id"]
    d = await client.delete(f"/api/v1/issues/{iid}", headers=auth["_authz"])
    assert d.status_code == 204
    lst = await client.get(f"/api/v1/projects/{proj_id}/issues", headers=auth["_authz"])
    assert all(x["id"] != iid for x in lst.json())
    # detalle ya no accesible
    detail = await client.get(f"/api/v1/issues/{iid}", headers=auth["_authz"])
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_delete_lesson_removes_from_list(client, db_session):
    _, auth, proj_id, _area = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/lessons",
        json={"title": "L1", "category": "improvement"},
        headers=auth["_authz"],
    )
    lid = r.json()["id"]
    d = await client.delete(f"/api/v1/lessons/{lid}", headers=auth["_authz"])
    assert d.status_code == 204
    lst = await client.get(f"/api/v1/lessons?project_id={proj_id}", headers=auth["_authz"])
    assert all(x["id"] != lid for x in lst.json())


@pytest.mark.asyncio
async def test_cancel_change_keeps_visible(client, db_session):
    _, auth, proj_id, _area = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/change-requests",
        json={"title": "CR", "type": "scope"},
        headers=auth["_authz"],
    )
    cid = r.json()["id"]
    c = await client.post(f"/api/v1/change-requests/{cid}/cancel", headers=auth["_authz"])
    assert c.status_code == 200
    assert c.json()["status"] == "cancelled"
    # sigue visible en la lista (cancelar preserva trazabilidad)
    lst = await client.get(f"/api/v1/projects/{proj_id}/change-requests", headers=auth["_authz"])
    assert any(x["id"] == cid and x["status"] == "cancelled" for x in lst.json())
    # cancelar de nuevo → 409
    again = await client.post(f"/api/v1/change-requests/{cid}/cancel", headers=auth["_authz"])
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_delete_change_removes_from_list(client, db_session):
    _, auth, proj_id, _area = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/change-requests",
        json={"title": "CR2", "type": "cost"},
        headers=auth["_authz"],
    )
    cid = r.json()["id"]
    d = await client.delete(f"/api/v1/change-requests/{cid}", headers=auth["_authz"])
    assert d.status_code == 204
    lst = await client.get(f"/api/v1/projects/{proj_id}/change-requests", headers=auth["_authz"])
    assert all(x["id"] != cid for x in lst.json())
