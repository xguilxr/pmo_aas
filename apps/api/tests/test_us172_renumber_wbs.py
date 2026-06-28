"""US-172 — renumerado jerárquico y único del WBS.

Resuelve WBS duplicados/libres preservando orden visual + profundidad, y
remapea predecesoras al nuevo esquema.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.task import Task
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
    return auth, p.json()["id"], str(t.id)


@pytest.mark.asyncio
async def test_renumber_resolves_duplicates_and_hierarchy(client, db_session):
    auth, proj_id, tenant_id = await _setup(client, db_session)

    # Sembramos un árbol con un LEAF duplicado ("1.1" dos veces) y created_at
    # ascendente para que el desempate sea determinista.
    base = datetime(2026, 6, 1, tzinfo=UTC)
    seeds = [
        ("1", 0, "Fase A"),
        ("1.1", 1, "A.1"),
        ("1.1", 1, "A.2 (WBS duplicado)"),
        ("2", 0, "Fase B"),
        ("2.1", 1, "B.1"),
    ]
    for i, (wbs, lvl, name) in enumerate(seeds):
        db_session.add(Task(
            tenant_id=tenant_id, project_id=str(proj_id), name=name,
            wbs=wbs, outline_level=lvl, status="not_started", source="manual",
            created_at=base + timedelta(minutes=i),
        ))
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/renumber-wbs", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["renumbered"] == 5

    rows = await client.get(f"/api/v1/projects/{proj_id}/tasks", headers=auth["_authz"])
    wbs_list = [t["wbs"] for t in rows.json()]
    # Todos únicos.
    assert len(wbs_list) == len(set(wbs_list))
    # Jerarquía esperada: 1, 1.1, 1.2, 2, 2.1.
    assert sorted(wbs_list) == sorted(["1", "1.1", "1.2", "2", "2.1"])


@pytest.mark.asyncio
async def test_renumber_remaps_predecessors(client, db_session):
    auth, proj_id, tenant_id = await _setup(client, db_session)
    # 'B' (wbs "5") depende de 'A' (wbs "3"); tras renumerar deben quedar
    # consecutivos y la predecesora apuntar al nuevo WBS de A.
    db_session.add(Task(
        tenant_id=tenant_id, project_id=str(proj_id), name="A",
        wbs="3", outline_level=0, status="not_started", source="manual",
    ))
    db_session.add(Task(
        tenant_id=tenant_id, project_id=str(proj_id), name="B",
        wbs="5", outline_level=0, status="not_started", source="manual",
        predecessors=["3"],
    ))
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks/renumber-wbs", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text

    rows = (await client.get(
        f"/api/v1/projects/{proj_id}/tasks", headers=auth["_authz"]
    )).json()
    by_name = {t["name"]: t for t in rows}
    assert by_name["A"]["wbs"] == "1"
    assert by_name["B"]["wbs"] == "2"
    # La predecesora de B se remapeó del viejo "3" al nuevo "1".
    assert by_name["B"]["predecessors"] == ["1"]
