"""US-179 — estados RAID a 4 + detención (on_hold)."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1", "description": "d", "type": "innovacion",
            "priority": 3, "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    proj_id = r.json()["id"]
    a = await client.post(
        "/api/v1/areas",
        json={"name": "Infra", "project_id": proj_id},
        headers=auth["_authz"],
    )
    return t, auth, proj_id, a.json()["id"]


# TC-179.1 — on_hold sin razón → 422.
@pytest.mark.asyncio
async def test_on_hold_requires_reason(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo detenido", "probability": 3, "impact": 3,
            "area_id": area_id, "status": "on_hold",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-179.2 — on_hold con razón + dependencia → 201, since seteado + embeds.
@pytest.mark.asyncio
async def test_on_hold_with_reason_and_dependency(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo detenido", "probability": 3, "impact": 3,
            "area_id": area_id, "status": "on_hold",
            "on_hold_reason": "Espera presupuesto",
            "on_hold_area_id": area_id,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "on_hold"
    assert body["on_hold_reason"] == "Espera presupuesto"
    assert body["on_hold_since"] is not None
    assert body["on_hold_area"] == {"id": area_id, "name": "Infra"}


# TC-179.3 — transición de issue a on_hold y de vuelta limpia el since.
@pytest.mark.asyncio
async def test_issue_on_hold_toggle(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={"title": "Acción", "type": "action", "area_id": area_id},
        headers=auth["_authz"],
    )
    iid = r.json()["id"]
    assert r.json()["status"] == "open"

    # → on_hold sin razón falla.
    bad = await client.patch(
        f"/api/v1/issues/{iid}", json={"status": "on_hold"},
        headers=auth["_authz"],
    )
    assert bad.status_code == 422

    # → on_hold con razón ok.
    ok = await client.patch(
        f"/api/v1/issues/{iid}",
        json={"status": "on_hold", "on_hold_reason": "Bloqueado por proveedor"},
        headers=auth["_authz"],
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["on_hold_since"] is not None

    # → in_progress limpia el since.
    back = await client.patch(
        f"/api/v1/issues/{iid}", json={"status": "in_progress"},
        headers=auth["_authz"],
    )
    assert back.status_code == 200
    assert back.json()["on_hold_since"] is None


# TC-179.4 — los 4 estados son válidos; los legacy ya no.
@pytest.mark.asyncio
async def test_only_four_statuses(client, db_session):
    _, auth, proj_id, area_id = await _setup(client, db_session)
    for s in ("open", "in_progress", "resolved"):
        r = await client.post(
            f"/api/v1/projects/{proj_id}/issues",
            json={"title": f"I {s}", "type": "issue", "area_id": area_id, "status": s},
            headers=auth["_authz"],
        )
        assert r.status_code == 201, (s, r.text)
    bad = await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={"title": "Legacy", "type": "issue", "area_id": area_id, "status": "identified"},
        headers=auth["_authz"],
    )
    assert bad.status_code == 422
