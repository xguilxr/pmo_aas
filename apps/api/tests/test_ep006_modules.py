"""EP006 — Project Modules tests."""
import pytest

from app.core.security import validate_password_policy  # noqa: F401
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
    pm_id = me.json()["id"]
    r = await client.post("/api/v1/projects", json={
        "name": "P1", "description": "d", "type": "innovation", "priority": 3,
        "organization_id": org_id, "pm_id": pm_id,
    }, headers=auth["_authz"])
    proj_id = r.json()["id"]
    return t, auth, proj_id


# TC-082 severity calc
@pytest.mark.asyncio
async def test_tc082_severity_calc(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={"title": "R1", "probability": 5, "impact": 4},
        headers=auth["_authz"],
    )
    assert r.status_code == 201
    assert r.json()["severity"] == 20


# TC-083 severity filter
@pytest.mark.asyncio
async def test_tc083_severity_filter(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    for p, i in [(1, 2), (3, 3), (5, 5)]:
        await client.post(
            f"/api/v1/projects/{proj_id}/risks",
            json={"title": f"R_{p}_{i}", "probability": p, "impact": i},
            headers=auth["_authz"],
        )
    r = await client.get(f"/api/v1/projects/{proj_id}/risks?severity_min=13",
                          headers=auth["_authz"])
    assert r.status_code == 200
    assert all(rr["severity"] >= 13 for rr in r.json())


# TC-085 closure_note required
@pytest.mark.asyncio
async def test_tc085_closure_note_required(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={"title": "Riesgo", "probability": 2, "impact": 2},
        headers=auth["_authz"],
    )
    rid = r.json()["id"]
    bad = await client.patch(
        f"/api/v1/risks/{rid}", json={"status": "closed"}, headers=auth["_authz"]
    )
    assert bad.status_code == 422
    ok = await client.patch(
        f"/api/v1/risks/{rid}",
        json={"status": "closed", "closure_note": "Mitigado"},
        headers=auth["_authz"],
    )
    assert ok.status_code == 200


# TC-086 overdue issues
@pytest.mark.asyncio
async def test_tc086_overdue_issues(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={"title": "I1", "type": "action", "committed_date": "2020-01-01"},
        headers=auth["_authz"],
    )
    r = await client.get(
        f"/api/v1/projects/{proj_id}/issues?overdue=true", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


# TC-088 approve requires permission (viewer cannot)
@pytest.mark.asyncio
async def test_tc088_approve_requires_permission(client, db_session):
    from app.models.role import Role, UserRole

    t, auth, proj_id = await _setup(client, db_session)
    # crear viewer role sin permiso approve
    viewer_role = Role(
        tenant_id=t.id, name="Viewer", description="",
        permissions={"change_requests": ["read", "create"], "projects": ["read"]},
        is_system=False,
    )
    db_session.add(viewer_role)
    await db_session.flush()
    viewer = await create_user(
        db_session, tenant=t, username="viewer", email="viewer@acme.example.com",
        password="Str0ng-View-1!", roles=[viewer_role],
    )
    # Crear change request con admin
    r = await client.post(
        f"/api/v1/projects/{proj_id}/change-requests",
        json={"title": "CR", "type": "scope"},
        headers=auth["_authz"],
    )
    chg_id = r.json()["id"]
    viewer_auth = await login(client, "viewer", "Str0ng-View-1!")
    deny = await client.post(f"/api/v1/change-requests/{chg_id}/approve",
                              headers=viewer_auth["_authz"])
    assert deny.status_code == 403


# TC-089 rejected → approved blocked
@pytest.mark.asyncio
async def test_tc089_rejected_to_approved(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/change-requests",
        json={"title": "CR", "type": "scope"},
        headers=auth["_authz"],
    )
    chg_id = r.json()["id"]
    rej = await client.post(f"/api/v1/change-requests/{chg_id}/reject",
                             headers=auth["_authz"])
    assert rej.status_code == 200
    bad = await client.post(f"/api/v1/change-requests/{chg_id}/approve",
                              headers=auth["_authz"])
    assert bad.status_code == 409


# TC-090 document versioning
@pytest.mark.asyncio
async def test_tc090_doc_versioning(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    doc = {
        "title": "plan", "category": "plan",
        "file_url": "https://r2/bucket/plan.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
    }
    r1 = await client.post(f"/api/v1/projects/{proj_id}/documents", json=doc, headers=auth["_authz"])
    assert r1.status_code == 201
    assert r1.json()["version"] == 1
    r2 = await client.post(f"/api/v1/projects/{proj_id}/documents", json=doc, headers=auth["_authz"])
    assert r2.status_code == 201
    assert r2.json()["version"] == 2


# TC-091 MIME not whitelisted
@pytest.mark.asyncio
async def test_tc091_bad_mime(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/documents",
        json={"title": "bad", "file_url": "http://x",
              "mime_type": "application/x-msdownload", "size_bytes": 100},
        headers=auth["_authz"],
    )
    assert r.status_code == 415


# TC-094 viewer lists lessons cross-project
@pytest.mark.asyncio
async def test_tc094_lessons_cross_project(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    await client.post(
        f"/api/v1/projects/{proj_id}/lessons",
        json={"title": "L1", "category": "success", "tags": ["deploy"]},
        headers=auth["_authz"],
    )
    r = await client.get("/api/v1/lessons?tag=deploy", headers=auth["_authz"])
    assert r.status_code == 200
    rows = r.json()
    assert any(x["title"] == "L1" for x in rows)


# TC-095 convert agreement to issue
@pytest.mark.asyncio
async def test_tc095_convert_agreement(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    mm = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": "Kick-off",
            "meeting_date": "2026-01-15T10:00:00+00:00",
            "agreements": [
                {"description": "Definir scope", "owner_id": None, "due_date": "2026-02-01"}
            ],
        },
        headers=auth["_authz"],
    )
    mm_id = mm.json()["id"]
    r = await client.post(
        f"/api/v1/meeting-minutes/{mm_id}/convert-agreement?agreement_index=0",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["folio"].startswith("INC-")


# TC-097 minute flagged generated_by_ai
@pytest.mark.asyncio
async def test_tc097_minute_generated_by_ai(client, db_session):
    _, auth, proj_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/meeting-minutes",
        json={
            "title": "IA",
            "meeting_date": "2026-02-01T10:00:00+00:00",
            "generated_by_ai": True,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201
    assert r.json()["generated_by_ai"] is True
