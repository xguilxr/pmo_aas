"""ENH-101 — projects.status_rag declarative RAG field."""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup_project(client, db_session) -> tuple[dict, str]:
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
    body = {
        "name": "Proyecto RAG",
        "description": "ENH-101",
        "type": "innovation",
        "priority": 3,
        "organization_id": org_id,
        "pm_id": pm_id,
    }
    p = await client.post("/api/v1/projects", json=body, headers=auth["_authz"])
    assert p.status_code == 201, p.text
    return auth, p.json()["id"]


@pytest.mark.asyncio
async def test_enh101_default_is_null(client, db_session):
    auth, pid = await _setup_project(client, db_session)
    r = await client.get(f"/api/v1/projects/{pid}", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json().get("status_rag") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["green", "amber", "red"])
async def test_enh101_patch_valid_persists(client, db_session, value):
    auth, pid = await _setup_project(client, db_session)
    r = await client.patch(
        f"/api/v1/projects/{pid}",
        json={"status_rag": value},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["status_rag"] == value

    g = await client.get(f"/api/v1/projects/{pid}", headers=auth["_authz"])
    assert g.json()["status_rag"] == value


@pytest.mark.asyncio
async def test_enh101_patch_invalid_returns_422(client, db_session):
    auth, pid = await _setup_project(client, db_session)
    r = await client.patch(
        f"/api/v1/projects/{pid}",
        json={"status_rag": "yellow"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_enh101_patch_can_clear_to_null(client, db_session):
    auth, pid = await _setup_project(client, db_session)
    # primero seteamos
    await client.patch(
        f"/api/v1/projects/{pid}",
        json={"status_rag": "red"},
        headers=auth["_authz"],
    )
    # luego limpiamos con explicit null
    r = await client.patch(
        f"/api/v1/projects/{pid}",
        json={"status_rag": None},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["status_rag"] is None


@pytest.mark.asyncio
async def test_enh101_audit_log_on_change(client, db_session):
    auth, pid = await _setup_project(client, db_session)
    r = await client.patch(
        f"/api/v1/projects/{pid}",
        json={"status_rag": "amber"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "project.status_rag.set",
                AuditLog.entity_id == pid,
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    last = rows[-1]
    assert last.details.get("after") == "amber"
