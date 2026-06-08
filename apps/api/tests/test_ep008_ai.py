"""EP008 — AI cascade tests."""
import pytest

from app.services.ai.provider import chunk_text
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    enable_tenant_ai,
    login,
)


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    # US-057: habilitar IA en modo `byo` (openai stubbed) para que tanto minutas
    # como draft-report pasen el gate del endpoint. Los providers están
    # stubbed en conftest, así que la llamada devuelve el stub.
    await enable_tenant_ai(
        db_session,
        t,
        mode="byo",
        byo={"provider": "openai", "api_key_encrypted": "stub-key", "model": "stub"},
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={"name": "PAI", "description": "d", "type": "innovation", "priority": 3,
              "organization_id": org_id, "pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    proj_id = p.json()["id"]
    # US-064: area default para que los POST de risks/issues pasen la
    # validación Pydantic.
    # ENH-078: catálogo tenant + assignment al proyecto.
    ra = await client.post(
        "/api/v1/areas",
        json={"name": "Default Area", "organization_id": org_id},
        headers=auth["_authz"],
    )
    aid = ra.json()["id"]
    await client.put(
        f"/api/v1/admin/areas/{aid}/assignments",
        json={"scopes": [{"project_id": proj_id}]},
        headers=auth["_authz"],
    )
    return t, auth, proj_id, aid


# TC-112 chunking con overlap
def test_tc112_chunk_overlap():
    text = "a" * 20000
    chunks = chunk_text(text, max_tokens=1000, overlap_tokens=100)
    assert len(chunks) > 1
    # Overlap check: cada chunk excepto el último comparte contenido con el siguiente
    for i in range(len(chunks) - 1):
        assert chunks[i][-100:] in chunks[i + 1] or chunks[i + 1].startswith(chunks[i][-400:-100])


# TC-113 (US-051 refactor) dispatch devuelve 202 + job_id queued
@pytest.mark.asyncio
async def test_tc113_generate_minute_dispatches(client, db_session, monkeypatch):
    from app.workers.tasks import ai as ai_tasks

    captured: dict = {}

    def fake_delay(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(ai_tasks.generate_minute_task, "delay", fake_delay)

    _, auth, proj_id, _area_id = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={
            "project_id": proj_id,
            "transcript": "PM: Hola a todos. Hoy revisamos avance.\nAna: Listo los riesgos.\n",
            "save_as_minute": True,
            "title": "Kickoff IA",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    assert body["job_id"]
    assert captured["job_id"] == body["job_id"]
    assert captured["tenant_id"]
    assert captured["project_id"] == proj_id
    assert captured["save_as_minute"] is True


# TC-116 transcript > 5 MB → 413
@pytest.mark.asyncio
async def test_tc116_transcript_too_large(client, db_session):
    _, auth, proj_id, _area_id = await _setup(client, db_session)
    huge = "a" * (5 * 1024 * 1024 + 1)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_id, "transcript": huge, "save_as_minute": False},
        headers=auth["_authz"],
    )
    assert r.status_code == 413


# TC-117 (US-051) draft report dispatch + ejecución task produce report
@pytest.mark.asyncio
async def test_tc117_draft_report_dispatches_and_runs(client, db_session, monkeypatch):
    from app.workers.tasks import ai as ai_tasks

    captured: dict = {}

    def fake_delay(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(ai_tasks.draft_report_task, "delay", fake_delay)

    _, auth, proj_id, area_id = await _setup(client, db_session)
    for p, i in [(5, 5), (3, 2), (4, 4)]:
        await client.post(
            f"/api/v1/projects/{proj_id}/risks",
            json={"title": f"R-{p}x{i}", "probability": p, "impact": i, "area_id": area_id},
            headers=auth["_authz"],
        )
    r = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft",
        json={"recipients": ["stakeholder@acme.example.com"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    job_id = body["job_id"]

    # ejecuta la task con los args que capturamos
    await ai_tasks._run_report(**captured)

    j = await client.get(f"/api/v1/ai/jobs/{job_id}", headers=auth["_authz"])
    assert j.status_code == 200
    assert j.json()["status"] == "succeeded"
    assert j.json()["output"]["report_id"]


async def _draft_and_run(client, auth, proj_id, monkeypatch):
    """Dispatch + ejecución sincrónica de la task. Devuelve report_id."""
    from app.workers.tasks import ai as ai_tasks
    captured: dict = {}
    monkeypatch.setattr(
        ai_tasks.draft_report_task, "delay", lambda **k: captured.update(k),
    )
    r = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft", json={}, headers=auth["_authz"],
    )
    assert r.status_code == 202
    await ai_tasks._run_report(**captured)
    j = await client.get(
        f"/api/v1/ai/jobs/{r.json()['job_id']}", headers=auth["_authz"],
    )
    return j.json()["output"]["report_id"]


# TC-118 send sin recipients
@pytest.mark.asyncio
async def test_tc118_send_empty_recipients(client, db_session, monkeypatch):
    _, auth, proj_id, _area_id = await _setup(client, db_session)
    rep_id = await _draft_and_run(client, auth, proj_id, monkeypatch)
    r = await client.post(
        f"/api/v1/ai/reports/{rep_id}/send",
        json={"recipients": []},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-120 send ok
@pytest.mark.asyncio
async def test_tc120_send_ok(client, db_session, monkeypatch):
    _, auth, proj_id, _area_id = await _setup(client, db_session)
    rep_id = await _draft_and_run(client, auth, proj_id, monkeypatch)
    s = await client.post(
        f"/api/v1/ai/reports/{rep_id}/send",
        json={"recipients": ["a@b.com"]},
        headers=auth["_authz"],
    )
    assert s.status_code == 200
    assert s.json()["ok"] is True
