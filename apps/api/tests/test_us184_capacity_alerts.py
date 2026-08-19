"""US-184 — Alertas de capacidad.

Cubre (servicio `capacity_alerts` + fast-path):
- TC-184-1: recurso sobreasignado → notificación capacity_overload al PM.
- TC-184-2: dedupe — segundo sweep en la ventana no duplica.
- TC-184-3: recurso NO compartido en >1 proyecto → capacity_solo_specialist.
- TC-184-4: recurso clave en ≥3 proyectos amarillos/rojos →
  capacity_key_resource_risk.
- TC-184-5: fast-path alert_actor_if_overloaded dispara al sobrepasar.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.notification import Notification
from app.models.tenant import Tenant
from app.services.capacity_alerts import (
    CAPACITY_KEY_RESOURCE_RISK,
    CAPACITY_OVERLOAD,
    CAPACITY_SOLO_SPECIALIST,
    alert_actor_if_overloaded,
    sweep_capacity_alerts,
)
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
                "name": f"Proyecto {i + 1}", "description": "US-184",
                "type": "transformacion", "priority": 3,
                "organization_id": org_id, "pm_id": pm_id,
            },
            headers=auth["_authz"],
        )
        project_ids.append(p.json()["id"])
    tenant = (
        await db_session.execute(select(Tenant).where(Tenant.id == str(t.id)))
    ).scalar_one()
    return auth, tenant, pm_id, project_ids


async def _mk_actor(client, auth, name, capacity, **extra):
    r = await client.post(
        "/api/v1/actors",
        json={"name": name, "project_capacity_pct": capacity, **extra},
        headers=auth["_authz"],
    )
    return r.json()["id"]


async def _assign(client, auth, project_id, actor_id, pct, **extra):
    today = date.today()
    body = {
        "actor_id": actor_id,
        "allocation_pct": pct,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=45)).isoformat(),
        **extra,
    }
    r = await client.post(
        f"/api/v1/projects/{project_id}/participations", json=body, headers=auth["_authz"]
    )
    assert r.status_code == 201, r.text


async def _notifs(db, type_):
    return (
        await db.execute(select(Notification).where(Notification.type == type_))
    ).scalars().all()


@pytest.mark.asyncio
async def test_us184_overload_notifies_pm(client, db_session):
    auth, tenant, pm_id, projects = await _setup(client, db_session, n_projects=2)
    a = await _mk_actor(client, auth, "Saturado Uno", 50)
    await _assign(client, auth, projects[0], a, 40)
    await _assign(client, auth, projects[1], a, 35)

    # El fast-path del endpoint ya pudo disparar la alerta al crear la
    # segunda asignación; el sweep no debe duplicarla (dedupe).
    await sweep_capacity_alerts(db_session, tenant)
    await db_session.commit()
    notifs = await _notifs(db_session, CAPACITY_OVERLOAD)
    mine = [n for n in notifs if n.entity_id == a]
    assert len(mine) == 1
    assert str(mine[0].user_id) == pm_id
    assert "Saturado Uno" in mine[0].title
    assert mine[0].link == "/pmo/resources"


@pytest.mark.asyncio
async def test_us184_dedupe_within_window(client, db_session):
    auth, tenant, _, projects = await _setup(client, db_session, n_projects=1)
    a = await _mk_actor(client, auth, "Saturado Dos", 30)
    await _assign(client, auth, projects[0], a, 80)

    await sweep_capacity_alerts(db_session, tenant)
    await db_session.commit()
    created_again = await sweep_capacity_alerts(db_session, tenant)
    await db_session.commit()
    assert created_again == 0
    notifs = [n for n in await _notifs(db_session, CAPACITY_OVERLOAD) if n.entity_id == a]
    assert len(notifs) == 1


@pytest.mark.asyncio
async def test_us184_solo_specialist(client, db_session):
    auth, tenant, _, projects = await _setup(client, db_session, n_projects=2)
    a = await _mk_actor(
        client, auth, "Único Especialista", 100, is_shared_resource=False
    )
    await _assign(client, auth, projects[0], a, 30)
    await _assign(client, auth, projects[1], a, 30)

    await sweep_capacity_alerts(db_session, tenant)
    await db_session.commit()
    notifs = [
        n for n in await _notifs(db_session, CAPACITY_SOLO_SPECIALIST) if n.entity_id == a
    ]
    assert len(notifs) == 1
    assert "NO compartido" in notifs[0].body


@pytest.mark.asyncio
async def test_us184_key_resource_in_troubled_projects(client, db_session):
    auth, tenant, _, projects = await _setup(client, db_session, n_projects=3)
    a = await _mk_actor(client, auth, "Clave Tres", 100, is_key_resource=True)
    for pid in projects:
        await _assign(client, auth, pid, a, 20)
        r = await client.patch(
            f"/api/v1/projects/{pid}/health",
            json={"status": "red", "reason": "Riesgo mayor declarado para test"},
            headers=auth["_authz"],
        )
        assert r.status_code == 200, r.text

    await sweep_capacity_alerts(db_session, tenant)
    await db_session.commit()
    notifs = [
        n
        for n in await _notifs(db_session, CAPACITY_KEY_RESOURCE_RISK)
        if n.entity_id == a
    ]
    assert len(notifs) == 1
    assert "3 proyectos" in notifs[0].title


@pytest.mark.asyncio
async def test_us184_fast_path_alert(client, db_session):
    auth, tenant, _, projects = await _setup(client, db_session, n_projects=1)
    a = await _mk_actor(client, auth, "Rápido Al Rojo", 20)
    # El POST de la participation dispara el fast-path del endpoint.
    await _assign(client, auth, projects[0], a, 60)
    notifs = [n for n in await _notifs(db_session, CAPACITY_OVERLOAD) if n.entity_id == a]
    assert len(notifs) == 1
    # Llamada directa posterior → dedupe, no duplica.
    assert await alert_actor_if_overloaded(db_session, tenant, a) == 0
    # No sobreasignado → no dispara.
    b = await _mk_actor(client, auth, "Tranquilo", 100)
    await _assign(client, auth, projects[0], b, 10)
    assert await alert_actor_if_overloaded(db_session, tenant, b) == 0
