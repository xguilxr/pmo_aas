"""ENH-120 — tab Proyectos en /pmo/reports: filtra drafts + enriquece folio/tipo/período.

Verifica que `GET /tenant/reports`:
- Por default excluye reportes en `status='draft'`.
- Con `?include_drafts=true` los incluye.
- Cada row trae `folio` (RPT-<id corto>), `report_type` (derivado de `generator`)
  y `period` (del modelo).
"""
from __future__ import annotations

import pytest

from app.models.ai import Report
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
        "/api/v1/organizations", json={"name": "OrgENH120"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "PENH120", "description": "d", "type": "innovation",
            "priority": 3, "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return t, auth, p.json()["id"]


@pytest.mark.asyncio
async def test_enh120_filters_drafts_by_default(client, db_session):
    t, auth, project_id = await _setup(client, db_session)
    # Crea 2 reportes: uno draft, uno sent.
    db_session.add(Report(
        tenant_id=str(t.id), project_id=project_id, title="Borrador",
        sections={}, status="draft", generator="manual",
    ))
    db_session.add(Report(
        tenant_id=str(t.id), project_id=project_id, title="Enviado",
        sections={}, status="sent", generator="builder", period="2w",
    ))
    await db_session.commit()

    r = await client.get("/api/v1/tenant/reports", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    rows = r.json()
    titles = [row["title"] for row in rows]
    assert "Enviado" in titles
    assert "Borrador" not in titles


@pytest.mark.asyncio
async def test_enh120_include_drafts_returns_all(client, db_session):
    t, auth, project_id = await _setup(client, db_session)
    db_session.add(Report(
        tenant_id=str(t.id), project_id=project_id, title="Draft Visible",
        sections={}, status="draft", generator="manual",
    ))
    await db_session.commit()

    r = await client.get(
        "/api/v1/tenant/reports?include_drafts=true", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    titles = [row["title"] for row in r.json()]
    assert "Draft Visible" in titles


@pytest.mark.asyncio
async def test_enh120_enriches_folio_and_report_type(client, db_session):
    t, auth, project_id = await _setup(client, db_session)
    rep = Report(
        tenant_id=str(t.id), project_id=project_id, title="Quincenal",
        sections={}, status="sent", generator="builder", period="2w",
    )
    db_session.add(rep)
    await db_session.commit()
    await db_session.refresh(rep)

    r = await client.get("/api/v1/tenant/reports", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    rows = r.json()
    row = next(r for r in rows if r["title"] == "Quincenal")
    assert row["folio"].startswith("RPT-")
    assert row["folio"].endswith(str(rep.id)[:8].upper())
    assert row["report_type"] == "Builder"
    assert row["period"] == "2w"
    assert row["project_folio"]
    assert row["project_name"] == "PENH120"
