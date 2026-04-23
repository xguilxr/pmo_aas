"""US-038 — Reporte de Avance de Proyecto (Python, BD, PDF)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.ai import Report
from app.models.modules import ChangeRequest, Issue, Risk
from app.models.organization import Organization
from app.models.project import Project
from app.models.task import Task
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="avance-a"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


async def _seed_project(db_session, tenant, *, folio="P-0001"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="Descripción del proyecto",
        phase="execution",
        health_status="yellow",
        budget=Decimal("10000"),
        actual_budget=Decimal("4500"),
        progress=45,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.mark.asyncio
async def test_us038_generate_and_pdf(client, db_session):
    t, auth = await _admin(client, db_session)
    p = await _seed_project(db_session, t)
    cut = date(2026, 4, 20)

    # Tareas: 2 completadas, 1 in_progress, 1 not_started, 1 milestone cumplido
    db_session.add_all([
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T1",
            status="done", progress=100, end_date=cut - timedelta(days=3),
        ),
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T2",
            status="in_progress", progress=50,
        ),
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="T3",
            status="not_started", progress=0,
        ),
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="Hito alfa",
            is_milestone=True, status="done", progress=100,
            end_date=cut - timedelta(days=5),
        ),
        Task(
            tenant_id=str(t.id), project_id=str(p.id), name="Hito beta",
            is_milestone=True, status="not_started", progress=0,
            end_date=cut + timedelta(days=10),
        ),
    ])
    # Riesgos
    db_session.add_all([
        Risk(
            tenant_id=str(t.id), project_id=p.id, folio="RIS-1",
            title="Riesgo alto", status="identified", severity=20,
            probability=4, impact=5,
        ),
        Risk(
            tenant_id=str(t.id), project_id=p.id, folio="RIS-2",
            title="Riesgo cerrado", status="closed", severity=25,
            probability=5, impact=5,
        ),
    ])
    # AIDs
    db_session.add_all([
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="INC-1",
            title="Acción vencida", type="action", status="open",
            priority=3, reported_at=datetime.now(timezone.utc),
            committed_date=cut - timedelta(days=5),
        ),
        Issue(
            tenant_id=str(t.id), project_id=p.id, folio="INC-2",
            title="Acción resuelta", type="action", status="resolved",
            reported_at=datetime.now(timezone.utc),
        ),
    ])
    # Cambio en revisión
    db_session.add(
        ChangeRequest(
            tenant_id=str(t.id), project_id=p.id, folio="CHG-1",
            title="Cambio de alcance", type="scope", status="in_review",
            requested_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/avance",
        json={"cut_off_date": cut.isoformat()},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    # ENH-014: nombre = "Reporte de Avance - {project_name} - {datetime}.pdf"
    disposition = r.headers.get("content-disposition", "")
    assert disposition.startswith("attachment;")
    assert "Reporte de Avance - Proyecto_P-0001 - " in disposition
    assert disposition.rstrip().endswith(".pdf") or ".pdf" in disposition


@pytest.mark.asyncio
async def test_us038_persists_report_row(client, db_session):
    t, auth = await _admin(client, db_session, slug="avance-b")
    p = await _seed_project(db_session, t, folio="P-0002")

    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/avance",
        headers=auth["_authz"],
    )
    assert r.status_code == 200

    # Verifica que el row quedó persistido con generator='avance'
    from sqlalchemy import select

    rows = (
        await db_session.execute(
            select(Report).where(
                Report.tenant_id == str(t.id),
                Report.project_id == str(p.id),
                Report.generator == "avance",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].cut_off_date is not None
    assert "project" in rows[0].sections
    assert rows[0].sections["project"]["folio"] == "P-0002"


@pytest.mark.asyncio
async def test_us038_redownload_uses_snapshot(client, db_session):
    t, auth = await _admin(client, db_session, slug="avance-c")
    p = await _seed_project(db_session, t, folio="P-0003")

    gen = await client.post(
        f"/api/v1/projects/{p.id}/reports/avance",
        headers=auth["_authz"],
    )
    assert gen.status_code == 200

    from sqlalchemy import select

    report = (
        await db_session.execute(
            select(Report).where(
                Report.tenant_id == str(t.id),
                Report.project_id == str(p.id),
                Report.generator == "avance",
            )
        )
    ).scalar_one()

    dl = await client.get(
        f"/api/v1/reports/{report.id}/avance/download",
        headers=auth["_authz"],
    )
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_enh014_avance_preview_inline_disposition(client, db_session):
    """ENH-014: `?inline=true` devuelve Content-Disposition inline para preview."""
    t, auth = await _admin(client, db_session, slug="avance-preview")
    p = await _seed_project(db_session, t, folio="P-0010")

    gen = await client.post(
        f"/api/v1/projects/{p.id}/reports/avance", headers=auth["_authz"],
    )
    assert gen.status_code == 200

    from sqlalchemy import select

    report = (
        await db_session.execute(
            select(Report).where(
                Report.tenant_id == str(t.id),
                Report.project_id == str(p.id),
                Report.generator == "avance",
            )
        )
    ).scalar_one()

    dl = await client.get(
        f"/api/v1/reports/{report.id}/avance/download?inline=true",
        headers=auth["_authz"],
    )
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")
    disposition = dl.headers.get("content-disposition", "")
    assert disposition.startswith("inline;")
    assert "Reporte de Avance - Proyecto_P-0010 - " in disposition


@pytest.mark.asyncio
async def test_us038_cross_tenant_404(client, db_session):
    t_a, auth_a = await _admin(client, db_session, slug="avance-ta")
    t_b, auth_b = await _admin(client, db_session, slug="avance-tb")
    p = await _seed_project(db_session, t_a, folio="P-AAA")
    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/avance",
        headers=auth_b["_authz"],
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_us038_non_admin_cannot_generate(client, db_session):
    t, auth = await _admin(client, db_session, slug="avance-d")
    p = await _seed_project(db_session, t, folio="P-0004")
    # user sin projects:update
    await create_user(
        db_session, tenant=t, username="viewer_d",
        email="viewer@avance-d.example.com", password="Str0ng-User-1!",
    )
    viewer = await login(client, "viewer_d", "Str0ng-User-1!")
    r = await client.post(
        f"/api/v1/projects/{p.id}/reports/avance",
        headers=viewer["_authz"],
    )
    assert r.status_code == 403
