"""US-NEW-039 — Reporte de Seguimiento de Actividades."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.ai import Report
from app.models.modules import Issue
from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="seg-a"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _seed_project(db_session, tenant, folio="SP-0001"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        phase="execution",
        health_status="green",
        budget=Decimal("1000"),
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.mark.asyncio
async def test_usnew039_generate_and_groups(client, db_session):
    t, auth = await _admin(client, db_session)
    p = await _seed_project(db_session, t)
    cut = date(2026, 4, 20)
    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()

    # Tarea vencida (hace 3 días)
    db_session.add(
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="Tarea vencida",
            status="in_progress", progress=30,
            end_date=cut - timedelta(days=3),
            owner_id=me["id"],
        )
    )
    # Tarea en curso (hoy, no vencida)
    db_session.add(
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="Tarea en curso",
            status="in_progress", progress=10, end_date=cut,
            owner_id=me["id"],
        )
    )
    # Tarea próxima (en 5 días)
    db_session.add(
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="Tarea futura",
            status="not_started", progress=0,
            end_date=cut + timedelta(days=5),
            owner_id=me["id"],
        )
    )
    # Acción vencida sin responsable
    db_session.add(
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="ACT-1",
            title="Acción sin owner", type="action", status="open",
            reported_at=datetime.now(timezone.utc),
            committed_date=cut - timedelta(days=5),
        )
    )
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/seguimiento",
        json={"cut_off_date": cut.isoformat(), "window_days": 14},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert "Reporte_Seguimiento_SP-0001_2026-04-20.pdf" in r.headers.get(
        "content-disposition", ""
    )


@pytest.mark.asyncio
async def test_usnew039_persists_snapshot(client, db_session):
    t, auth = await _admin(client, db_session, slug="seg-b")
    p = await _seed_project(db_session, t, folio="SP-0002")

    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/seguimiento", headers=auth["_authz"],
    )
    assert r.status_code == 200

    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(Report).where(
                Report.tenant_id == str(t.id),
                Report.project_id == str(p.id),
                Report.generator == "seguimiento",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    sections = rows[0].sections
    assert "counts" in sections
    assert "groups_overdue" in sections
    assert "groups_in_progress" in sections
    assert "groups_upcoming" in sections


@pytest.mark.asyncio
async def test_usnew039_redownload_uses_snapshot(client, db_session):
    t, auth = await _admin(client, db_session, slug="seg-c")
    p = await _seed_project(db_session, t, folio="SP-0003")

    await client.post(
        f"/api/v1/projects/{p.id}/reports/seguimiento", headers=auth["_authz"],
    )
    from sqlalchemy import select

    report = (
        await db_session.execute(
            select(Report).where(
                Report.tenant_id == str(t.id),
                Report.project_id == str(p.id),
                Report.generator == "seguimiento",
            )
        )
    ).scalar_one()

    dl = await client.get(
        f"/api/v1/reports/{report.id}/seguimiento/download",
        headers=auth["_authz"],
    )
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_usnew039_cross_tenant_404(client, db_session):
    t_a, auth_a = await _admin(client, db_session, slug="seg-ta")
    _, auth_b = await _admin(client, db_session, slug="seg-tb")
    p = await _seed_project(db_session, t_a, folio="SP-AAA")
    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/seguimiento", headers=auth_b["_authz"],
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_usnew039_empty_project_no_crash(client, db_session):
    t, auth = await _admin(client, db_session, slug="seg-empty")
    p = await _seed_project(db_session, t, folio="SP-E")
    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/seguimiento",
        json={"cut_off_date": "2026-04-20"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")
