"""US-176 — reorden manual del plan (tasks.position) vía /tasks/{id}/move."""
from __future__ import annotations

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={"name": "Proyecto", "description": "d", "type": "bau", "priority": 3,
              "organization_id": org.json()["id"], "pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


async def _names(client, auth, proj_id):
    r = await client.get(f"/api/v1/projects/{proj_id}/tasks", headers=auth["_authz"])
    return [t["name"] for t in r.json()]


@pytest.mark.asyncio
async def test_move_reorders_plan(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    ids = {}
    for name, wbs_code in [("Tarea A", "1"), ("Tarea B", "2"), ("Tarea C", "3")]:
        r = await client.post(
            f"/api/v1/projects/{proj_id}/tasks",
            json={"name": name, "wbs_code": wbs_code},
            headers=auth["_authz"],
        )
        assert r.status_code == 201, r.text
        ids[name] = r.json()["id"]

    # Orden inicial por WBS.
    assert await _names(client, auth, proj_id) == ["Tarea A", "Tarea B", "Tarea C"]

    # Mover C justo después de A → A, C, B.
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/{ids['Tarea C']}/move",
        json={"after_id": ids["Tarea A"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert await _names(client, auth, proj_id) == ["Tarea A", "Tarea C", "Tarea B"]

    # Mover A al inicio (after_id=None) — ya está primero, sigue igual.
    await client.post(
        f"/api/v1/projects/{proj_id}/tasks/{ids['Tarea A']}/move",
        json={"after_id": None},
        headers=auth["_authz"],
    )
    assert await _names(client, auth, proj_id) == ["Tarea A", "Tarea C", "Tarea B"]

    # Mover A después de B → C, B, A.
    await client.post(
        f"/api/v1/projects/{proj_id}/tasks/{ids['Tarea A']}/move",
        json={"after_id": ids["Tarea B"]},
        headers=auth["_authz"],
    )
    assert await _names(client, auth, proj_id) == ["Tarea C", "Tarea B", "Tarea A"]
