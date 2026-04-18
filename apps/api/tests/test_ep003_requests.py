"""EP003 — Project Requests tests."""
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
    # crear org para usar en requests
    r = await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    return t, auth, org_id


def _request_body(org_id: str) -> dict:
    return {
        "title": "Nuevo CRM",
        "description": "Implementar CRM",
        "objective": "Aumentar ventas",
        "organization_id": org_id,
        "business_unit": "Sales",
        "department": "Ventas",
        "sponsor": "CMO",
        "benefits": "Mejor conversión",
        "budget": "1000000.00",
        "scope": "Nacional México",
    }


# TC-043
@pytest.mark.asyncio
async def test_tc043_create_request_happy_path(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["folio"].startswith("SOL-")
    assert body["folio"].endswith("-001")
    assert body["status"] == "in_review"


# TC-047 filter by status
@pytest.mark.asyncio
async def test_tc047_filter_by_status(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r1 = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    assert r1.status_code == 201
    r2 = await client.get("/api/v1/project-requests?status=in_review", headers=auth["_authz"])
    assert r2.status_code == 200
    assert any(x["folio"] == r1.json()["folio"] for x in r2.json())
    r3 = await client.get("/api/v1/project-requests?status=approved", headers=auth["_authz"])
    assert all(x["status"] == "approved" for x in r3.json())


# TC-049 reject without comment
@pytest.mark.asyncio
async def test_tc049_reject_without_comment(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    rev = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "reject"},
        headers=auth["_authz"],
    )
    assert rev.status_code == 400


# TC-050 approve already approved → 409
@pytest.mark.asyncio
async def test_tc050_double_approve(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    a1 = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    assert a1.status_code == 200
    a2 = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    assert a2.status_code == 409
    assert a2.json()["detail"]["code"] == "STATE_TRANSITION"


# TC-051 needs_info -> edit -> resubmit
@pytest.mark.asyncio
async def test_tc051_needs_info_resubmit(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    need = await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "needs_info", "comment": "Falta alcance"},
        headers=auth["_authz"],
    )
    assert need.status_code == 200
    assert need.json()["status"] == "needs_info"
    ed = await client.patch(
        f"/api/v1/project-requests/{req_id}",
        json={"scope": "MX + LATAM"},
        headers=auth["_authz"],
    )
    assert ed.status_code == 200
    rs = await client.post(f"/api/v1/project-requests/{req_id}/resubmit", headers=auth["_authz"])
    assert rs.status_code == 200
    assert rs.json()["status"] == "in_review"


# TC-052 create project from approved
@pytest.mark.asyncio
async def test_tc052_create_project_from_request(client, db_session):
    t, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    # obtener el admin user id
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    cp = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    assert cp.status_code == 200, cp.text
    body = cp.json()
    assert body["folio"].startswith("PRJ-")
    assert not body["idempotent"]


# TC-053 create project from in_review
@pytest.mark.asyncio
async def test_tc053_create_project_from_in_review(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    cp = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    assert cp.status_code == 422


# TC-054 idempotency
@pytest.mark.asyncio
async def test_tc054_create_project_idempotent(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pm_id = me.json()["id"]
    a = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    b = await client.post(
        f"/api/v1/project-requests/{req_id}/create-project",
        json={"pm_id": pm_id},
        headers=auth["_authz"],
    )
    assert a.json()["project_id"] == b.json()["project_id"]
    assert b.json()["idempotent"] is True


# TC-055 cannot edit approved
@pytest.mark.asyncio
async def test_tc055_cannot_edit_approved(client, db_session):
    _, auth, org_id = await _setup(client, db_session)
    r = await client.post("/api/v1/project-requests", json=_request_body(org_id), headers=auth["_authz"])
    req_id = r.json()["id"]
    await client.post(
        f"/api/v1/project-requests/{req_id}/review",
        json={"decision": "approve"},
        headers=auth["_authz"],
    )
    ed = await client.patch(
        f"/api/v1/project-requests/{req_id}",
        json={"title": "Other"},
        headers=auth["_authz"],
    )
    assert ed.status_code == 409
