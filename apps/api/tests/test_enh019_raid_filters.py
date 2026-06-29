"""ENH-019 — filtros avanzados en endpoints tenant/risks y tenant/issues."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.modules import Issue, Risk
from app.models.organization import Organization
from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="raid-filters"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _project(db_session, tenant, *, folio="P-R01"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.mark.asyncio
async def test_enh019_tenant_risks_status_filter(client, db_session):
    t, auth = await _admin(client, db_session, slug="raid-risks-status")
    p = await _project(db_session, t, folio="P-R10")
    db_session.add_all(
        [
            Risk(
                tenant_id=str(t.id), project_id=p.id, folio="RIS-1",
                title="Abierto alto", status="open", severity=20,
                probability=5, impact=4,
            ),
            Risk(
                tenant_id=str(t.id), project_id=p.id, folio="RIS-2",
                title="Cerrado", status="resolved", severity=10,
                probability=2, impact=5,
            ),
        ]
    )
    await db_session.commit()

    r_all = await client.get("/api/v1/tenant/risks", headers=auth["_authz"])
    assert r_all.status_code == 200
    assert len(r_all.json()) == 2

    r_open = await client.get(
        "/api/v1/tenant/risks?status=open", headers=auth["_authz"]
    )
    assert r_open.status_code == 200
    body = r_open.json()
    assert len(body) == 1
    assert body[0]["folio"] == "RIS-1"


@pytest.mark.asyncio
async def test_enh019_tenant_risks_severity_min_filter(client, db_session):
    t, auth = await _admin(client, db_session, slug="raid-risks-sev")
    p = await _project(db_session, t, folio="P-R11")
    db_session.add_all(
        [
            Risk(
                tenant_id=str(t.id), project_id=p.id, folio="RIS-H",
                title="Alto", status="open", severity=20,
                probability=5, impact=4,
            ),
            Risk(
                tenant_id=str(t.id), project_id=p.id, folio="RIS-M",
                title="Medio", status="open", severity=8,
                probability=2, impact=4,
            ),
            Risk(
                tenant_id=str(t.id), project_id=p.id, folio="RIS-L",
                title="Bajo", status="open", severity=3,
                probability=1, impact=3,
            ),
        ]
    )
    await db_session.commit()

    r = await client.get(
        "/api/v1/tenant/risks?severity_min=13", headers=auth["_authz"]
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["folio"] == "RIS-H"


@pytest.mark.asyncio
async def test_enh019_tenant_issues_status_and_priority(client, db_session):
    t, auth = await _admin(client, db_session, slug="raid-issues-prio")
    p = await _project(db_session, t, folio="P-R12")
    db_session.add_all(
        [
            Issue(
                tenant_id=str(t.id), project_id=p.id, folio="INC-1",
                title="Acción alta abierta", type="action", status="open",
                priority=4, reported_at=datetime.now(UTC),
            ),
            Issue(
                tenant_id=str(t.id), project_id=p.id, folio="INC-2",
                title="Acción baja abierta", type="action", status="open",
                priority=1, reported_at=datetime.now(UTC),
            ),
            Issue(
                tenant_id=str(t.id), project_id=p.id, folio="INC-3",
                title="Acción alta cerrada", type="action", status="resolved",
                priority=5, reported_at=datetime.now(UTC),
            ),
        ]
    )
    await db_session.commit()

    # status + priority_min combinados
    r = await client.get(
        "/api/v1/tenant/issues?status=open&priority_min=3", headers=auth["_authz"]
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["folio"] == "INC-1"


@pytest.mark.asyncio
async def test_enh019_severity_min_out_of_range_rejected(client, db_session):
    t, auth = await _admin(client, db_session, slug="raid-sev-oor")
    await _project(db_session, t, folio="P-R13")
    # severity range 1..25 → 0 y 26 deben rechazarse
    r0 = await client.get(
        "/api/v1/tenant/risks?severity_min=0", headers=auth["_authz"]
    )
    assert r0.status_code == 422
    r26 = await client.get(
        "/api/v1/tenant/risks?severity_min=26", headers=auth["_authz"]
    )
    assert r26.status_code == 422
