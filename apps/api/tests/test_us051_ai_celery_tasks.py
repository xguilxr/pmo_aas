"""US-051 — tasks Celery para generación IA.

Verifica que:
- POST /ai/minutes y POST /ai/projects/{id}/reports/draft ya no ejecutan
  la cascada sincrónicamente: devuelven 202 con job_id queued y
  dispatchan la task al worker.
- Las tasks, cuando corren, persisten el resultado en AIJob y (para
  minutas) crean MeetingMinute. Cuando fallan, marcan status=failed
  con error poblado.
- El polling GET /ai/jobs/{id} respeta aislamiento por tenant.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
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
    p = await client.post(
        "/api/v1/projects",
        json={"name": "PUS051", "description": "d", "type": "innovation", "priority": 3,
              "organization_id": org_id, "pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    return t, auth, p.json()["id"]


@pytest.mark.asyncio
async def test_us051_minutes_dispatch_returns_202_and_queued(
    client, db_session, monkeypatch,
):
    from app.workers.tasks import ai as ai_tasks

    monkeypatch.setattr(
        ai_tasks.generate_minute_task, "delay", lambda **kwargs: None,
    )

    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_id, "transcript": "acta válida larga...", "save_as_minute": False},
        headers=auth["_authz"],
    )
    assert r.status_code == 202
    assert r.headers.get("location", "").startswith("/api/v1/ai/jobs/")
    body = r.json()
    assert body["status"] == "queued"
    assert body["job_id"]

    j = await client.get(f"/api/v1/ai/jobs/{body['job_id']}", headers=auth["_authz"])
    assert j.status_code == 200
    assert j.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_us051_minute_task_success_creates_minute(
    client, db_session, monkeypatch,
):
    from app.workers.tasks import ai as ai_tasks

    captured: dict = {}
    monkeypatch.setattr(
        ai_tasks.generate_minute_task, "delay",
        lambda **kwargs: captured.update(kwargs),
    )

    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={
            "project_id": proj_id,
            "transcript": "PM: Hola. Ana: Riesgos listados. Luis: Entrega el viernes.",
            "save_as_minute": True,
            "title": "Kickoff",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # Corre la task directamente con los args capturados
    await ai_tasks._run_minute(**captured)

    j = await client.get(f"/api/v1/ai/jobs/{job_id}", headers=auth["_authz"])
    data = j.json()
    assert data["status"] == "succeeded"
    assert data["output"]["minute_id"]
    assert data["model"]


@pytest.mark.asyncio
async def test_us051_minute_task_failure_marks_failed(
    client, db_session, monkeypatch,
):
    from app.workers.tasks import ai as ai_tasks

    captured: dict = {}
    monkeypatch.setattr(
        ai_tasks.generate_minute_task, "delay",
        lambda **kwargs: captured.update(kwargs),
    )

    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_id, "transcript": "transcripción válida larga", "save_as_minute": False},
        headers=auth["_authz"],
    )
    job_id = r.json()["job_id"]

    with patch(
        "app.workers.tasks.ai.generate_with_cascade",
        side_effect=RuntimeError("all providers dead"),
    ):
        await ai_tasks._run_minute(**captured)

    j = await client.get(f"/api/v1/ai/jobs/{job_id}", headers=auth["_authz"])
    data = j.json()
    assert data["status"] == "failed"
    assert data["error"]
    assert "all providers dead" in data["error"]


@pytest.mark.asyncio
async def test_us051_job_tenant_isolation(client, db_session, monkeypatch):
    """Un tenant no puede ver job_id de otro tenant."""
    from app.workers.tasks import ai as ai_tasks

    monkeypatch.setattr(
        ai_tasks.generate_minute_task, "delay", lambda **kwargs: None,
    )

    _, auth_a, proj_a = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_a, "transcript": "transcripción A larga", "save_as_minute": False},
        headers=auth_a["_authz"],
    )
    job_id = r.json()["job_id"]

    # Tenant B
    from tests.factories import create_admin_role, create_tenant, create_user, login
    tb = await create_tenant(db_session, slug="tenantb")
    adm_b = await create_admin_role(db_session, tb)
    await create_user(
        db_session, tenant=tb, username="adminb", email="admin@b.example.com",
        password="Str0ng-B-1!", roles=[adm_b],
    )
    auth_b = await login(client, "adminb", "Str0ng-B-1!")

    j = await client.get(f"/api/v1/ai/jobs/{job_id}", headers=auth_b["_authz"])
    assert j.status_code == 404


@pytest.mark.asyncio
async def test_us051_report_dispatch_returns_202(client, db_session, monkeypatch):
    from app.workers.tasks import ai as ai_tasks

    monkeypatch.setattr(
        ai_tasks.draft_report_task, "delay", lambda **kwargs: None,
    )

    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft",
        json={"recipients": ["a@b.com"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 202
    assert r.json()["status"] == "queued"
    assert r.headers.get("location", "").startswith("/api/v1/ai/jobs/")
