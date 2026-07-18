"""US-192 — salud del portafolio: evaluaciones bulk para el reporte."""
from __future__ import annotations

import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


@pytest.mark.asyncio
async def test_portfolio_health_evaluations(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    pids = []
    for name in ("P-A", "P-B"):
        p = await client.post(
            "/api/v1/projects",
            json={
                "name": name, "description": "d", "type": "bau", "priority": 3,
                "organization_id": org.json()["id"], "pm_id": me.json()["id"],
            },
            headers=auth["_authz"],
        )
        pids.append(p.json()["id"])

    for pid, overall in zip(pids, ("green", "red"), strict=False):
        r = await client.post(
            f"/api/v1/projects/{pid}/health-evaluations",
            json={
                "evaluated_at": "2026-07-15",
                "overall": overall,
                "note": "Bloqueo de presupuesto con el sponsor."
                if overall != "green"
                else None,
            },
            headers=auth["_authz"],
        )
        assert r.status_code == 201, r.text

    resp = await client.get(
        "/api/v1/dashboard/health-evaluations", headers=auth["_authz"]
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["rows"]
    assert {r["project_id"] for r in rows} == set(pids)
    assert {r["overall"] for r in rows} == {"green", "red"}
