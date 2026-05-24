"""US-140 — persistencia de reports al exportar PDF del builder.

Verifica:
- POST /report-builder/templates/{id}/export crea row en `reports`
  con `generator='builder'`, `html_content` poblado, `sections`
  con snapshot JSON.
- POST /reports/{id}/regenerate-pdf devuelve PDF desde el snapshot.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.ai import Report
from app.models.area import Area
from app.models.organization import Organization
from app.models.project import Project
from app.models.report_builder_template import ReportBuilderTemplate
from app.models.report_section import ReportSection
from app.models.task import Task
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    login,
)


async def _seed(client, db_session, slug):
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
    org = Organization(tenant_id=t.id, name="Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    area = Area(tenant_id=t.id, organization_id=org.id, name="A")
    db_session.add(area)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-140",
        name="Persist",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    db_session.add(
        ReportSection(
            code="S-01",
            name="Portada",
            category="HDR",
            level=3,
            data_shape={},
            parameters_schema={},
            composition_mode_default="A",
            supports_ia=False,
            enabled=True,
        )
    )
    tpl = ReportBuilderTemplate(
        tenant_id=str(t.id),
        code="T-PERSIST",
        name="Persist Template",
        level=3,
        composition_mode="A",
        section_codes=["S-01"],
        default_parameters={},
        is_seed=False,
    )
    db_session.add(tpl)
    today = date(2026, 6, 1)
    db_session.add(
        Task(
            tenant_id=str(t.id),
            project_id=p.id,
            name="T",
            status="in_progress",
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=5),
            duration_days=10,
            progress=50,
            area_id=area.id,
        )
    )
    await db_session.flush()
    await db_session.commit()
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, p, tpl, auth


@pytest.mark.asyncio
async def test_export_persists_report_row(client, db_session, monkeypatch):
    """El export PDF crea una row en `reports` con generator='builder'."""
    import app.services.pdf_renderer as pdf_mod

    monkeypatch.setattr(
        pdf_mod, "html_to_pdf", lambda html: b"%PDF-1.4\nstub\n%%EOF"
    )
    _t, p, tpl, auth = await _seed(client, db_session, "us140-persist")

    r = await client.post(
        f"/api/v1/report-builder/templates/{tpl.id}/export?format=pdf",
        headers=auth["_authz"],
        json={"project_id": str(p.id), "level": 3, "window_days": 14},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"

    # Buscar la row persistida.
    rows = (
        await db_session.execute(
            select(Report).where(Report.project_id == str(p.id))
        )
    ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.generator == "builder"
    assert row.title.startswith("Persist Template")
    assert "P-140" in row.title or "T-PERSIST" in row.title
    assert row.html_content.startswith("<!doctype html>") or row.html_content.startswith("<html")
    # El snapshot tiene la sección S-01.
    assert "sections" in row.sections
    assert "S-01" in row.sections.get("sections", {})


@pytest.mark.asyncio
async def test_regenerate_pdf_returns_blob(client, db_session, monkeypatch):
    """POST /reports/{id}/regenerate-pdf devuelve PDF desde el snapshot."""
    import app.services.pdf_renderer as pdf_mod

    monkeypatch.setattr(
        pdf_mod, "html_to_pdf", lambda html: b"%PDF-1.4\nstub\n%%EOF"
    )
    _t, p, tpl, auth = await _seed(client, db_session, "us140-regen")

    # Primero export para crear la row.
    r1 = await client.post(
        f"/api/v1/report-builder/templates/{tpl.id}/export?format=pdf",
        headers=auth["_authz"],
        json={"project_id": str(p.id), "level": 3, "window_days": 14},
    )
    assert r1.status_code == 200

    row = (
        await db_session.execute(
            select(Report).where(Report.project_id == str(p.id))
        )
    ).scalar_one()

    r2 = await client.post(
        f"/api/v1/reports/{row.id}/regenerate-pdf",
        headers=auth["_authz"],
    )
    assert r2.status_code == 200, r2.text
    assert r2.headers["content-type"] == "application/pdf"
    assert r2.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_regenerate_pdf_rejects_non_builder(client, db_session):
    """Reports operacionales no aceptan regenerate-pdf."""
    t, p, _tpl, auth = await _seed(client, db_session, "us140-reject")
    # Crear un report manual (no builder).
    rep = Report(
        tenant_id=str(t.id),
        project_id=str(p.id),
        title="Operativo",
        sections={},
        recipients=[],
        status="draft",
        generated_by_ai=False,
        generator="manual",
        cut_off_date=None,
        html_content="",
    )
    db_session.add(rep)
    await db_session.commit()

    r = await client.post(
        f"/api/v1/reports/{rep.id}/regenerate-pdf",
        headers=auth["_authz"],
    )
    assert r.status_code == 422  # business_rule
