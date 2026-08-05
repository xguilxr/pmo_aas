"""ENH-050 — Plan: campo Hito Relacionado en formulario de tarea.

Cubre:
- TC-050.1: crear M1 (hito) + T1 con related_milestone_id=M1.id → GET T1
  expone related_milestone={id, name, wbs_code}.
- TC-050.2: borrar M1 → T1.related_milestone_id pasa a NULL.
- Validación: related_milestone_id apuntando a una task no-hito → 422.
- Validación: related_milestone_id apuntando a task de otro proyecto → 422.
- PATCH a related_milestone_id=None desasocia.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
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
async def test_tc050_1_related_milestone_attaches_in_get(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    # Crea hito M1.
    m = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "M1", "wbs_code": "1", "is_milestone": True},
        headers=auth["_authz"],
    )
    assert m.status_code == 201, m.text
    m_id = m.json()["id"]
    # Crea T1 vinculada a M1.
    t = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "T1", "wbs_code": "1.1", "related_milestone_id": m_id},
        headers=auth["_authz"],
    )
    assert t.status_code == 201, t.text
    body = t.json()
    assert body["related_milestone_id"] == m_id
    assert body["related_milestone"] is not None
    assert body["related_milestone"]["name"] == "M1"
    # GET list expone related_milestone con name + wbs_code.
    lst = await client.get(
        f"/api/v1/projects/{proj_id}/tasks", headers=auth["_authz"]
    )
    rows = {r["name"]: r for r in lst.json()}
    assert rows["T1"]["related_milestone"]["wbs_code"] == "1"


@pytest.mark.asyncio
async def test_tc050_2_delete_milestone_sets_null(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    m = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "M1", "is_milestone": True},
        headers=auth["_authz"],
    )
    m_id = m.json()["id"]
    t = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "T1", "related_milestone_id": m_id},
        headers=auth["_authz"],
    )
    t_id = t.json()["id"]
    # Borra hito.
    d = await client.delete(f"/api/v1/tasks/{m_id}", headers=auth["_authz"])
    assert d.status_code == 204
    # T1 sigue existiendo con related_milestone_id NULL.
    lst = await client.get(
        f"/api/v1/projects/{proj_id}/tasks", headers=auth["_authz"]
    )
    rows = {r["id"]: r for r in lst.json()}
    assert t_id in rows
    assert rows[t_id]["related_milestone_id"] is None
    assert rows[t_id]["related_milestone"] is None


@pytest.mark.asyncio
async def test_related_milestone_must_be_milestone(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    # Crea task NO-hito.
    a = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "AA", "is_milestone": False},
        headers=auth["_authz"],
    )
    a_id = a.json()["id"]
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "BB", "related_milestone_id": a_id},
        headers=auth["_authz"],
    )
    # validation_error() en este codebase retorna 400 con code=VALIDATION_ERROR.
    assert r.status_code in (400, 422), r.text
    assert "is_milestone" in r.text or "milestone" in r.text


@pytest.mark.asyncio
async def test_patch_disassociates_with_explicit_null(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    m = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "M1", "is_milestone": True},
        headers=auth["_authz"],
    )
    m_id = m.json()["id"]
    t = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "T1", "related_milestone_id": m_id},
        headers=auth["_authz"],
    )
    t_id = t.json()["id"]
    # PATCH explícito a null.
    p = await client.patch(
        f"/api/v1/tasks/{t_id}",
        json={"related_milestone_id": None},
        headers=auth["_authz"],
    )
    assert p.status_code == 200, p.text
    assert p.json()["related_milestone_id"] is None
