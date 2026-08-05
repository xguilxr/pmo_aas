"""US-183 — Motor de saturación de recursos (asignaciones con FTE%).

Caso canónico del diseño (Eli Gomora): capacidad para proyectos 50%,
asignaciones activas 25+15+25=65 → sobreasignación 15 pts → rojo.

Cubre:
- TC-183-1: summary individual (demanda, gap, color) + caso Eli.
- TC-183-2: asignaciones fuera de ventana no cuentan.
- TC-183-3: tentativas no suman demanda (se reportan aparte).
- TC-183-4: /capacity/conflicts lista proyectos en choque + recomendación.
- TC-183-5: dimensión "recursos" del health se activa con FTE% (recurso
  clave sobreasignado → rojo).
- TC-183-6: agregación por función de portafolio.
- TC-183-7: allocation NULL cuenta como sin cuantificar, no como demanda.
"""
from datetime import date, timedelta

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session, *, n_projects: int = 3):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    project_ids = []
    for i in range(n_projects):
        p = await client.post(
            "/api/v1/projects",
            json={
                "name": f"Proyecto {i + 1}",
                "description": "US-183",
                "type": "transformation",
                "priority": 3,
                "organization_id": org_id,
                "pm_id": pm_id,
            },
            headers=auth["_authz"],
        )
        assert p.status_code == 201, p.text
        project_ids.append(p.json()["id"])
    return auth, org_id, project_ids


async def _mk_actor(client, auth, name: str, capacity: float, **extra) -> str:
    r = await client.post(
        "/api/v1/actors",
        json={"name": name, "project_capacity_pct": capacity, **extra},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _assign(client, auth, project_id, actor_id, pct, **extra):
    today = date.today()
    body = {
        "actor_id": actor_id,
        "allocation_pct": pct,
        "start_date": (today - timedelta(days=7)).isoformat(),
        "end_date": (today + timedelta(days=60)).isoformat(),
        **extra,
    }
    r = await client.post(
        f"/api/v1/projects/{project_id}/participations", json=body, headers=auth["_authz"]
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_us183_eli_case_overallocated_red(client, db_session):
    auth, _, projects = await _setup(client, db_session)
    eli = await _mk_actor(
        client, auth, "Eli Gomora", 50,
        resource_type="cliente_negocio", discipline="negocio",
        is_key_resource=True, scarcity_level="alta",
    )
    for pid, pct in zip(projects, (25, 15, 25), strict=False):
        await _assign(client, auth, pid, eli, pct)

    r = await client.get("/api/v1/capacity/summary?window=week", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    rows = [x for x in r.json()["resources"] if x["actor_id"] == eli]
    assert len(rows) == 1
    row = rows[0]
    assert row["capacity_pct"] == 50
    assert row["demand_pct"] == 65
    assert row["gap_pct"] == -15
    assert row["over_pct"] == 15
    assert row["projects_count"] == 3
    assert row["color"] == "red"  # over 15 > red_over default 10


@pytest.mark.asyncio
async def test_us183_out_of_window_not_counted(client, db_session):
    auth, _, projects = await _setup(client, db_session, n_projects=1)
    a = await _mk_actor(client, auth, "Pasado Pisado", 60)
    today = date.today()
    await _assign(
        client, auth, projects[0], a, 80,
        start_date=(today - timedelta(days=90)).isoformat(),
        end_date=(today - timedelta(days=30)).isoformat(),
    )
    r = await client.get("/api/v1/capacity/summary?window=week", headers=auth["_authz"])
    rows = [x for x in r.json()["resources"] if x["actor_id"] == a]
    # Sin demanda en ventana: puede no aparecer o aparecer con demanda 0.
    assert all(x["demand_pct"] == 0 for x in rows)


@pytest.mark.asyncio
async def test_us183_tentative_reported_apart(client, db_session):
    auth, _, projects = await _setup(client, db_session, n_projects=1)
    a = await _mk_actor(client, auth, "Tentativo Pérez", 80)
    await _assign(client, auth, projects[0], a, 40, status="tentativa")
    await _assign(client, auth, projects[0], a, 30)
    r = await client.get("/api/v1/capacity/summary?window=week", headers=auth["_authz"])
    row = next(x for x in r.json()["resources"] if x["actor_id"] == a)
    assert row["demand_pct"] == 30
    assert row["tentative_pct"] == 40
    assert row["color"] == "green"


@pytest.mark.asyncio
async def test_us183_conflicts_with_recommendation(client, db_session):
    auth, _, projects = await _setup(client, db_session)
    a = await _mk_actor(client, auth, "Carlos Mejia", 60, discipline="arquitectura")
    for pid, pct, crit in zip(projects, (40, 35, 30), (True, False, False), strict=False):
        await _assign(client, auth, pid, a, pct, is_critical=crit)

    r = await client.get("/api/v1/capacity/conflicts?window=3weeks", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    conflicts = r.json()["conflicts"]
    mine = next(c for c in conflicts if c["actor_id"] == a)
    assert mine["demand_pct"] == 105
    assert len(mine["projects"]) == 3
    # Recomendación: liberar la asignación no-crítica menor (30%).
    assert "30%" in mine["recommendation"]


@pytest.mark.asyncio
async def test_us183_health_resources_dimension_activates(client, db_session):
    auth, _, projects = await _setup(client, db_session, n_projects=2)
    a = await _mk_actor(client, auth, "Clave Saturado", 40, is_key_resource=True)
    await _assign(client, auth, projects[0], a, 40)
    await _assign(client, auth, projects[1], a, 30)

    r = await client.get(
        f"/api/v1/projects/{projects[0]}/health-detail", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    resources = next(d for d in r.json()["dimensions"] if d["key"] == "resources")
    # Recurso clave sobreasignado (70 vs 40, over 30 > 10) → rojo.
    assert resources["color"] == "red"
    assert resources["metrics"]["key_overloaded"] == 1
    assert any("Clave Saturado" in c["what"] for c in resources["causes"])


@pytest.mark.asyncio
async def test_us183_by_discipline_aggregation(client, db_session):
    auth, _, projects = await _setup(client, db_session, n_projects=1)
    a1 = await _mk_actor(client, auth, "Arq Uno", 50, discipline="arquitectura")
    a2 = await _mk_actor(client, auth, "Arq Dos", 50, discipline="arquitectura")
    await _assign(client, auth, projects[0], a1, 60)
    await _assign(client, auth, projects[0], a2, 20)
    r = await client.get("/api/v1/capacity/summary?window=week", headers=auth["_authz"])
    fn = next(
        x for x in r.json()["by_discipline"] if x["discipline"] == "arquitectura"
    )
    assert fn["capacity_pct"] == 100
    assert fn["demand_pct"] == 80
    assert fn["resources"] == 2
    assert fn["overloaded"] == 1


@pytest.mark.asyncio
async def test_us183_null_allocation_unquantified(client, db_session):
    auth, _, projects = await _setup(client, db_session, n_projects=1)
    a = await _mk_actor(client, auth, "Sin FTE", 70)
    r = await client.post(
        f"/api/v1/projects/{projects[0]}/participations",
        json={"actor_id": a},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    r = await client.get("/api/v1/capacity/summary?window=week", headers=auth["_authz"])
    row = next(x for x in r.json()["resources"] if x["actor_id"] == a)
    assert row["demand_pct"] == 0
    assert row["unquantified_count"] == 1
    assert row["color"] == "green"
