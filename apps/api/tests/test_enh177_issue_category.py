"""ENH-177 — category para issues (acciones/incidencias/decisiones).

La columna existe y el read la expone; el PATCH la actualiza.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.modules import Issue
from tests.factories import create_admin_role, create_tenant, create_user, login


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
    return auth, p.json()["id"], str(t.id)


@pytest.mark.asyncio
async def test_issue_category_read_and_patch(client, db_session):
    auth, proj_id, tenant_id = await _setup(client, db_session)

    issue = Issue(
        tenant_id=tenant_id, project_id=str(proj_id), folio="INC-2026-001",
        title="Acción X", type="action", category="Operativo",
        status="open", reported_at=datetime.now(UTC), comments=[],
    )
    db_session.add(issue)
    await db_session.commit()

    # Read expone category.
    r = await client.get(f"/api/v1/issues/{issue.id}", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    assert r.json()["category"] == "Operativo"

    # PATCH actualiza category.
    r2 = await client.patch(
        f"/api/v1/issues/{issue.id}",
        json={"category": "Estratégico"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["category"] == "Estratégico"
