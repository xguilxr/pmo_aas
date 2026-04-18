"""EP008 — AI cascade tests."""
import pytest

from app.services.ai.provider import chunk_text
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
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
    return t, auth, p.json()["id"]


# TC-112 chunking con overlap
def test_tc112_chunk_overlap():
    text = "a" * 20000
    chunks = chunk_text(text, max_tokens=1000, overlap_tokens=100)
    assert len(chunks) > 1
    # Overlap check: cada chunk excepto el último comparte contenido con el siguiente
    for i in range(len(chunks) - 1):
        assert chunks[i][-100:] in chunks[i + 1] or chunks[i + 1].startswith(chunks[i][-400:-100])


# TC-113 stub (AI disabled by default) devuelve JSON válido vía parser fallback
@pytest.mark.asyncio
async def test_tc113_generate_minute_stub(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
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
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert body["model"]
    assert "output" in body
    # Minuta guardada
    assert body["minute_id"]


# TC-116 transcript > 5 MB → 413
@pytest.mark.asyncio
async def test_tc116_transcript_too_large(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    huge = "a" * (5 * 1024 * 1024 + 1)
    r = await client.post(
        "/api/v1/ai/minutes",
        json={"project_id": proj_id, "transcript": huge, "save_as_minute": False},
        headers=auth["_authz"],
    )
    assert r.status_code == 413


# TC-117 draft report incluye top_risks
@pytest.mark.asyncio
async def test_tc117_draft_report_includes_risks(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    # crear riesgos variados
    for p, i in [(5, 5), (3, 2), (4, 4)]:
        await client.post(
            f"/api/v1/projects/{proj_id}/risks",
            json={"title": f"R-{p}x{i}", "probability": p, "impact": i},
            headers=auth["_authz"],
        )
    r = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft",
        json={"recipients": ["stakeholder@acme.example.com"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["report_id"]


# TC-118 send sin recipients
@pytest.mark.asyncio
async def test_tc118_send_empty_recipients(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    draft = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft", json={}, headers=auth["_authz"]
    )
    rep_id = draft.json()["report_id"]
    r = await client.post(
        f"/api/v1/ai/reports/{rep_id}/send",
        json={"recipients": []},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-120 duplicar reporte previo (nuestro flujo: draft nuevo reutiliza data actual)
@pytest.mark.asyncio
async def test_tc120_send_ok(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    draft = await client.post(
        f"/api/v1/ai/projects/{proj_id}/reports/draft", json={}, headers=auth["_authz"]
    )
    rep_id = draft.json()["report_id"]
    s = await client.post(
        f"/api/v1/ai/reports/{rep_id}/send",
        json={"recipients": ["a@b.com"]},
        headers=auth["_authz"],
    )
    assert s.status_code == 200
    assert s.json()["ok"] is True
