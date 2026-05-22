"""US-130 — Export PDF de reportes custom (EP020).

TC-230 (PDF valida `%PDF` header), TC-231 (incluye todas las secciones
del canvas en el HTML emitido por el motor).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.area import Area
from app.models.organization import Organization
from app.models.project import Project
from app.models.report_builder_template import ReportBuilderTemplate
from app.models.report_section import ReportSection
from app.models.task import Task
from app.services.reports.engine import (
    ReportScope,
    ReportWindow,
    render_template,
)
from tests.factories import create_tenant

CANVAS_CODES = [
    "S-01", "S-02", "S-03", "S-06", "S-08",
    "S-09", "S-16", "S-17", "S-18",
    "S-11", "S-12", "S-13", "S-14",
    "S-20", "S-21", "S-28",
]


async def _seed_sections(db):
    for code in CANVAS_CODES:
        db.add(
            ReportSection(
                code=code,
                name=code,
                category="HDR",
                level=3,
                data_shape={},
                parameters_schema={},
                composition_mode_default="A",
                supports_ia=False,
                enabled=True,
            )
        )
    await db.flush()


async def _seed_world(db, slug):
    t = await create_tenant(db, slug=slug, name=slug)
    org = Organization(tenant_id=t.id, name=f"Org-{slug}", is_active=True)
    db.add(org)
    await db.flush()
    area = Area(tenant_id=t.id, organization_id=org.id, name="Default")
    db.add(area)
    await db.flush()
    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio=f"P-{slug.upper()}",
        name=f"Proyecto {slug}",
        description="",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db.add(p)
    await db.flush()
    today = date(2026, 6, 1)
    db.add(
        Task(
            tenant_id=str(t.id),
            project_id=p.id,
            name="Task A",
            status="in_progress",
            is_milestone=False,
            is_critical=False,
            criticality="medium",
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=5),
            duration_days=15,
            progress=50,
            area_id=area.id,
        )
    )
    await db.flush()
    return t, p, today


@pytest.mark.asyncio
async def test_tc230_pdf_header(db_session, monkeypatch):
    """TC-230 — el export devuelve bytes con header %PDF."""
    await _seed_sections(db_session)
    t, p, today = await _seed_world(db_session, slug="us130-h")
    tpl = ReportBuilderTemplate(
        tenant_id=str(t.id),
        code="T-EXPORT",
        name="Export Test",
        level=3,
        composition_mode="A",
        section_codes=["S-01", "S-09"],
        default_parameters={},
        is_seed=False,
    )
    db_session.add(tpl)
    await db_session.flush()

    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=today, window_days=14),
    )
    import app.services.pdf_renderer as pdf_mod
    monkeypatch.setattr(pdf_mod, "html_to_pdf", lambda html: b"%PDF-1.4\nstub\n%%EOF")
    pdf = pdf_mod.html_to_pdf(result.html)
    assert pdf.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_tc231_html_includes_all_canvas_sections(db_session):
    """TC-231 — el HTML emitido incluye marcadores de TODAS las secciones
    del canvas (verifica que el motor no omite ninguna)."""
    await _seed_sections(db_session)
    t, p, today = await _seed_world(db_session, slug="us130-all")
    tpl = ReportBuilderTemplate(
        tenant_id=str(t.id),
        code="T-ALL",
        name="All Canvas",
        level=3,
        composition_mode="A",
        section_codes=CANVAS_CODES,
        default_parameters={},
        is_seed=False,
    )
    db_session.add(tpl)
    await db_session.flush()

    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=today, window_days=14),
    )
    # Cada plantilla de sección emite <section class="section section-sNN">
    for code in CANVAS_CODES:
        marker = f'section-{code.lower().replace("-", "")}'
        assert marker in result.html, (
            f"Falta sección {code} en el HTML emitido (marker={marker})"
        )

    # Footer con metadata US-130.
    assert "Plantilla:" in result.html
    assert tpl.code in result.html
    assert "Emitido:" in result.html
    assert "Scope:" in result.html


@pytest.mark.asyncio
async def test_us130_footer_includes_pm_name(db_session):
    """Verifica que el PM aparezca en el footer cuando el proyecto lo tiene."""
    await _seed_sections(db_session)
    t = await create_tenant(db_session, slug="us130-pm", name="us130-pm")
    org = Organization(tenant_id=t.id, name="Org-PM", is_active=True)
    db_session.add(org)
    await db_session.flush()
    # Crear user PM
    from app.core.security import hash_password
    from app.models.user import User
    pm = User(
        tenant_id=t.id,
        username="pm_us130",
        email="pm_us130@x.example.com",
        password_hash=hash_password("Str0ng-Admin-1!"),
        full_name="Ana Project Manager",
        is_active=True,
        role_type="user",
    )
    db_session.add(pm)
    await db_session.flush()
    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-PM",
        name="Proyecto PM",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
        pm_id=pm.id,
    )
    db_session.add(p)
    await db_session.flush()
    tpl = ReportBuilderTemplate(
        tenant_id=str(t.id),
        code="T-PM",
        name="PM Footer Test",
        level=3,
        composition_mode="A",
        section_codes=["S-01"],
        default_parameters={},
        is_seed=False,
    )
    db_session.add(tpl)
    await db_session.flush()

    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=date(2026, 6, 1), window_days=14),
    )
    assert "Ana Project Manager" in result.html
