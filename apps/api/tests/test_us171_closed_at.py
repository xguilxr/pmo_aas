"""US-171 — fecha de cierre (closed_at) + lógica de atraso para cerradas.

- Una tarea NO completada con end_date < hoy → retrasada.
- Una tarea completada se considera retrasada SOLO si closed_at > end_date.
- El endpoint auto-setea closed_at = hoy al completar sin fecha, y permite
  editarla (p.ej. a una fecha en plazo para una tarea registrada tarde).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models.task import Task
from app.services.operational_reports import _is_completed_late, _is_delayed
from tests.factories import create_admin_role, create_tenant, create_user, login


def _t(**kw) -> Task:
    return Task(name="t", **kw)


def test_is_delayed_open_task_past_end():
    today = date(2026, 6, 28)
    assert _is_delayed(_t(end_date=date(2026, 6, 1), status="in_progress", progress=10), today)


def test_is_delayed_completed_on_time_not_delayed():
    today = date(2026, 6, 28)
    # cerrada antes/igual a la fecha fin → ni Atrasada ni Completada con atraso.
    t = _t(end_date=date(2026, 6, 20), status="completed", progress=100,
           closed_at=date(2026, 6, 18))
    assert _is_delayed(t, today) is False
    assert _is_completed_late(t) is False


def test_us177_completed_late_is_not_atrasada_but_completed_late():
    # US-177: una completada que cerró tarde NO es "Atrasada" (rojo); es
    # "Completada con atraso" (amarillo).
    today = date(2026, 6, 28)
    t = _t(end_date=date(2026, 6, 20), status="completed", progress=100,
           closed_at=date(2026, 6, 25))
    assert _is_delayed(t, today) is False
    assert _is_completed_late(t) is True


def test_is_delayed_completed_without_closed_at_not_delayed():
    today = date(2026, 6, 28)
    t = _t(end_date=date(2026, 6, 1), status="completed", progress=100, closed_at=None)
    assert _is_delayed(t, today) is False
    assert _is_completed_late(t) is False


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


@pytest.mark.asyncio
async def test_complete_autosets_closed_at_and_editable(client, db_session):
    auth, proj_id = await _setup(client, db_session)
    end = (date.today() - timedelta(days=5)).isoformat()
    r = await client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"name": "Tarea", "wbs": "1", "end_date": end, "status": "not_started"},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    assert r.json()["closed_at"] is None

    # Completar sin closed_at → auto-set a hoy.
    r2 = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "completed"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["closed_at"] == date.today().isoformat()

    # Editar closed_at a una fecha en plazo (registrada tarde pero cerrada a tiempo).
    on_time = (date.today() - timedelta(days=7)).isoformat()
    r3 = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"closed_at": on_time},
        headers=auth["_authz"],
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["closed_at"] == on_time
