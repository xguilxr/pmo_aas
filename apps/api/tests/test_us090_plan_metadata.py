"""US-090 — Plan: outline_level + duration auto + predecessors/successors.

Cubre:
- TC-090.1: wbs `1.2.3` → outline_level=3.
- TC-090.2: start=01-01, end=01-05 → duration_days=5 (inclusivo).
- TC-090.3: rango > 21 días → 422.
- TC-090.4: A.predecessors=[B.wbs] → GET B.successors incluye A.wbs.
- TC-090.5: A.predecessors=[B] + B.predecessors=[A] → 422 (cycle).
- Predecessor inexistente → 422.
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
async def test_tc090_1_outline_level_from_wbs(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={"name": "T1", "wbs": "1.2.3"},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["outline_level"] == 3


@pytest.mark.asyncio
async def test_tc090_2_duration_from_dates_inclusive(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={
            "name": "T1",
            "wbs": "1",
            "start_date": "2026-01-01",
            "end_date": "2026-01-05",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["duration_days"] == 5


@pytest.mark.asyncio
async def test_tc090_3_duration_max_21_rejects(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={
            "name": "T1",
            "start_date": "2026-01-01",
            "end_date": "2026-02-15",
        },
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 422), r.text
    assert "21" in r.text


@pytest.mark.asyncio
async def test_tc090_4_successors_synced_from_predecessors(client, db_session):
    auth, proj = await _setup(client, db_session)
    # B sin predecessors.
    b = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={"name": "Bee", "wbs": "1"},
        headers=auth["_authz"],
    )
    assert b.status_code == 201
    # A apunta a B.
    a = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={"name": "Alpha", "wbs": "2", "predecessors": ["1"]},
        headers=auth["_authz"],
    )
    assert a.status_code == 201, a.text
    # GET list: B.successors debe contener "2" (wbs de A).
    lst = await client.get(
        f"/api/v1/projects/{proj}/tasks", headers=auth["_authz"]
    )
    by_name = {r["name"]: r for r in lst.json()}
    assert by_name["Bee"]["successors"] == ["2"]
    assert by_name["Alpha"]["predecessors"] == ["1"]


@pytest.mark.asyncio
async def test_tc090_5_cycle_rejects(client, db_session):
    auth, proj = await _setup(client, db_session)
    a = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={"name": "Alpha", "wbs": "1"},
        headers=auth["_authz"],
    )
    b = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={"name": "Bee", "wbs": "2", "predecessors": ["1"]},
        headers=auth["_authz"],
    )
    assert b.status_code == 201, b.text
    # Ahora intento cerrar el ciclo: A.predecessors=[B.wbs="2"].
    a_id = a.json()["id"]
    r = await client.patch(
        f"/api/v1/tasks/{a_id}",
        json={"predecessors": ["2"]},
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 422), r.text
    assert "cic" in r.text.lower() or "cycle" in r.text.lower()


@pytest.mark.asyncio
async def test_predecessor_unknown_wbs_rejects(client, db_session):
    auth, proj = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj}/tasks",
        json={"name": "T1", "wbs": "1", "predecessors": ["999"]},
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 422), r.text
