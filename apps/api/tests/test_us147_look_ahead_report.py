"""US-147 — Endpoint reporte Look-ahead.

Verifica que `POST /projects/{id}/reports/look-ahead`:
- Filtra tasks por start/end dentro de la ventana.
- Excluye tasks con `end_date < hoy`.
- Persiste Report con `generator='look_ahead'`.
- Soporta units days|weeks|months.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.ai import Report
from app.models.task import Task
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    login,
)


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "OrgLA"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "PLA147", "description": "d", "type": "innovation",
            "priority": 3, "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return t, auth, p.json()["id"]


@pytest.mark.asyncio
async def test_look_ahead_filters_window_and_persists(client, db_session):
    t, auth, project_id = await _setup(client, db_session)
    today = datetime.now(UTC).date()
    # Tasks de prueba:
    # 1. Vencida — excluida.
    # 2. Empieza dentro de 5 días — INCLUIDA con window=2 semanas.
    # 3. Termina en 8 días — INCLUIDA.
    # 4. Empieza en 60 días — EXCLUIDA con window=2 semanas.
    tasks = [
        Task(
            tenant_id=str(t.id), project_id=project_id,
            name="Vencida", start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=2), progress=50, status="in_progress",
        ),
        Task(
            tenant_id=str(t.id), project_id=project_id,
            name="Empieza pronto", start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=20), progress=0, status="not_started",
        ),
        Task(
            tenant_id=str(t.id), project_id=project_id,
            name="Termina pronto", start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=8), progress=80, status="in_progress",
        ),
        Task(
            tenant_id=str(t.id), project_id=project_id,
            name="Lejana", start_date=today + timedelta(days=60),
            end_date=today + timedelta(days=80), progress=0, status="not_started",
        ),
    ]
    for tk in tasks:
        db_session.add(tk)
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{project_id}/reports/look-ahead",
        json={"window_value": 2, "window_unit": "weeks"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"

    # Verifica que se persistió el Report.
    from sqlalchemy import select
    rep = (
        await db_session.execute(
            select(Report).where(
                Report.project_id == project_id,
                Report.generator == "look_ahead",
            )
        )
    ).scalar_one()
    sections = rep.sections or {}
    task_names = [tk["name"] for tk in sections.get("tasks", [])]
    assert "Empieza pronto" in task_names
    assert "Termina pronto" in task_names
    assert "Vencida" not in task_names
    assert "Lejana" not in task_names


@pytest.mark.asyncio
async def test_look_ahead_unit_months(client, db_session):
    t, auth, project_id = await _setup(client, db_session)
    today = datetime.now(UTC).date()
    db_session.add(Task(
        tenant_id=str(t.id), project_id=project_id,
        name="En 40 días", start_date=today + timedelta(days=40),
        end_date=today + timedelta(days=50), status="not_started",
    ))
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{project_id}/reports/look-ahead",
        json={"window_value": 2, "window_unit": "months"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    from sqlalchemy import select
    rep = (
        await db_session.execute(
            select(Report).where(Report.generator == "look_ahead")
        )
    ).scalar_one()
    names = [tk["name"] for tk in rep.sections["tasks"]]
    assert "En 40 días" in names


@pytest.mark.asyncio
async def test_look_ahead_default_window(client, db_session):
    _, auth, project_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{project_id}/reports/look-ahead",
        headers=auth["_authz"],
    )
    # default = 2 weeks. Sin tasks, debe devolver PDF válido.
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
