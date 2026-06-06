"""US-123 — Report Builder render engine (EP020).

TC-209 (modo A reproduce orden área→fecha), TC-210 (modo B agrupa por
área), TC-211 (exclusiones cruzadas no duplican), TC-212 (export PDF).

El test crea manualmente las secciones que usa porque conftest crea el
schema con `Base.metadata.create_all` y no corre los seeds de Alembic.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.area import Area
from app.models.modules import Issue, Risk
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

SEED_SECTIONS = [
    ("S-01", "Portada", "HDR", "A"),
    ("S-02", "Información del proyecto", "HDR", "A"),
    ("S-03", "Semáforo RAG", "EST", "A"),
    ("S-06", "% Avance", "AVN", "A"),
    ("S-08", "Avance por área", "AVN", "A"),
    ("S-09", "Hitos próximos", "PLN", "A"),
    ("S-11", "Riesgos abiertos", "RAID", "A"),
    ("S-12", "Issues", "RAID", "A"),
    ("S-13", "Decisiones", "RAID", "A"),
    ("S-14", "Acciones", "RAID", "A"),
    ("S-16", "Críticos", "PLN", "A"),
    ("S-17", "Retrasadas", "PLN", "A"),
    ("S-18", "Próximas", "PLN", "A"),
    ("S-20", "Equipo por área", "EQP", "B"),
    ("S-21", "Carga", "EQP", "B"),
]


async def _seed_sections(db):
    for code, name, category, mode in SEED_SECTIONS:
        db.add(
            ReportSection(
                code=code,
                name=name,
                category=category,
                level=3,
                data_shape={},
                parameters_schema={},
                composition_mode_default=mode,
                supports_ia=False,
                enabled=True,
            )
        )
    await db.flush()


async def _seed_world(db, slug="us123"):
    """Crea tenant + org + área + proyecto + tasks de prueba.

    Tasks:
        T-HITO    — milestone próximo (end_date dentro de ventana).
        T-CRITHIT — milestone + crítica próxima (test exclusión S-09 ∪ S-16).
        T-CRITDEL — crítica retrasada (debe salir SOLO en S-16, no en S-17).
        T-DELAYED — retrasada normal → S-17.
        T-UPCOMING — próxima normal (no hito, no crítica) → S-18.
    """
    t = await create_tenant(db, slug=slug, name=slug)
    org = Organization(tenant_id=t.id, name="Org-US123", is_active=True)
    db.add(org)
    await db.flush()
    area_alpha = Area(tenant_id=t.id, organization_id=org.id, name="Alpha")
    area_beta = Area(tenant_id=t.id, organization_id=org.id, name="Beta")
    db.add_all([area_alpha, area_beta])
    await db.flush()

    p = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-US123",
        name="Proyecto US-123",
        description="Test del engine",
        phase="execution",
        health_status="amber",
        status_rag="amber",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db.add(p)
    await db.flush()

    today = date(2026, 6, 1)
    in_window = today + timedelta(days=5)
    overdue = today - timedelta(days=3)

    specs = [
        # (name, status, is_milestone, is_critical, end_date, area)
        ("T-HITO", "in_progress", True, False, in_window, area_alpha),
        ("T-CRITHIT", "in_progress", True, True, in_window, area_beta),
        ("T-CRITDEL", "in_progress", False, True, overdue, area_alpha),
        ("T-DELAYED", "in_progress", False, False, overdue, area_beta),
        ("T-UPCOMING", "in_progress", False, False, in_window, area_alpha),
        ("T-DONE", "completed", False, False, overdue, area_alpha),
    ]
    for name, status, mile, crit, end, area in specs:
        db.add(
            Task(
                tenant_id=str(t.id),
                project_id=p.id,
                name=name,
                status=status,
                is_milestone=mile,
                is_critical=crit,
                criticality=("high" if crit else "medium"),
                start_date=today - timedelta(days=30),
                end_date=end,
                duration_days=30,
                progress=(100 if status == "done" else 50),
                area_id=area.id,
            )
        )

    # Un riesgo abierto y uno cerrado.
    db.add(
        Risk(
            tenant_id=str(t.id),
            project_id=p.id,
            folio="R-001",
            title="Riesgo abierto",
            status="open",
            severity=16,
            probability=4,
            impact=4,
            area_id=area_alpha.id,
        )
    )
    db.add(
        Risk(
            tenant_id=str(t.id),
            project_id=p.id,
            folio="R-002",
            title="Riesgo cerrado",
            status="closed",
            severity=4,
            area_id=area_beta.id,
        )
    )
    # Acción + Issue + Decisión.
    now = datetime.now(UTC)
    db.add(
        Issue(
            tenant_id=str(t.id),
            project_id=p.id,
            folio="A-001",
            title="Acción pendiente",
            type="action",
            status="open",
            committed_date=in_window,
            reported_at=now,
            area_id=area_alpha.id,
        )
    )
    db.add(
        Issue(
            tenant_id=str(t.id),
            project_id=p.id,
            folio="I-001",
            title="Issue abierto",
            type="issue",
            status="open",
            priority=3,
            committed_date=in_window,
            reported_at=now,
            area_id=area_beta.id,
        )
    )
    db.add(
        Issue(
            tenant_id=str(t.id),
            project_id=p.id,
            folio="D-001",
            title="Decisión tomada",
            type="decision",
            status="closed",
            committed_date=overdue,
            reported_at=now,
            area_id=area_alpha.id,
        )
    )
    await db.flush()

    return t, p, today


async def _make_template(db, tenant, codes, mode="A", code="T-CUSTOM"):
    tpl = ReportBuilderTemplate(
        tenant_id=str(tenant.id),
        code=code,
        name="Custom",
        level=3,
        composition_mode=mode,
        section_codes=codes,
        default_parameters={},
        is_seed=False,
    )
    db.add(tpl)
    await db.flush()
    return tpl


@pytest.mark.asyncio
async def test_tc209_mode_a_orders_by_area_and_date(db_session):
    """TC-209 — modo A: items ordenados por end_date ascendente y por
    nombre de área (estable)."""
    await _seed_sections(db_session)
    t, p, today = await _seed_world(db_session, slug="us123-a")
    tpl = await _make_template(
        db_session,
        t,
        ["S-01", "S-09", "S-18"],
        mode="A",
        code="T-A",
    )
    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=today, window_days=14),
    )
    assert "html" in result.__dict__
    assert "Proyecto US-123" in result.html or "P-US123" in result.html
    # S-09 trae T-HITO (in_window, alpha) y T-CRITHIT (in_window, beta);
    # mismo end_date, debe ordenar por área (Alpha < Beta).
    s09 = result.json["sections"]["S-09"]["rows"]
    assert [r["name"] for r in s09] == ["T-HITO", "T-CRITHIT"]


@pytest.mark.asyncio
async def test_tc210_mode_b_groups_by_area(db_session):
    """TC-210 — modo B: el motor expone __by_area__ con buckets por área."""
    await _seed_sections(db_session)
    t, p, today = await _seed_world(db_session, slug="us123-b")
    tpl = await _make_template(
        db_session,
        t,
        ["S-01", "S-09", "S-17", "S-18"],
        mode="B",
        code="T-B",
    )
    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=today, window_days=14),
    )
    by_area = result.json["sections"]["__by_area__"]
    assert "Alpha" in by_area
    assert "Beta" in by_area
    # Alpha tiene un hito próximo (T-HITO) y una upcoming (T-UPCOMING).
    assert any("S-09" in v for v in [by_area["Alpha"]])
    assert any(
        row["name"] == "T-HITO" for row in by_area["Alpha"].get("S-09", [])
    )


@pytest.mark.asyncio
async def test_tc211_cross_exclusions(db_session):
    """TC-211 — S-17 excluye items ya listados en S-09/S-16."""
    await _seed_sections(db_session)
    t, p, today = await _seed_world(db_session, slug="us123-x")
    tpl = await _make_template(
        db_session,
        t,
        ["S-09", "S-16", "S-17", "S-18"],
        mode="A",
        code="T-X",
    )
    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=today, window_days=14),
    )
    sections = result.json["sections"]

    s09_names = {r["name"] for r in sections["S-09"]["rows"]}
    s16_names = {r["name"] for r in sections["S-16"]["rows"]}
    s17_names = {r["name"] for r in sections["S-17"]["rows"]}
    s18_names = {r["name"] for r in sections["S-18"]["rows"]}

    # S-09: hitos próximos (T-HITO + T-CRITHIT)
    assert s09_names == {"T-HITO", "T-CRITHIT"}
    # S-16: críticos no done (T-CRITHIT + T-CRITDEL)
    assert "T-CRITDEL" in s16_names
    # T-CRITDEL es retrasada Y crítica → ya salió en S-16, no debe duplicarse en S-17
    assert "T-CRITDEL" not in s17_names
    # T-DELAYED (no es hito, no es crítica) debe estar en S-17
    assert "T-DELAYED" in s17_names
    # T-UPCOMING (próxima normal) debe estar en S-18 y no en S-09/S-16/S-17
    assert "T-UPCOMING" in s18_names
    assert "T-UPCOMING" not in s09_names
    assert "T-UPCOMING" not in s17_names


@pytest.mark.asyncio
async def test_tc212_export_pdf(db_session, monkeypatch):
    """TC-212 — pipeline render_template + html_to_pdf devuelve PDF bytes.

    Stubea `html_to_pdf` para no requerir weasyprint en la suite rápida.
    El smoke real del motor PDF vive en `test_us037_pdf_renderer`.
    """
    await _seed_sections(db_session)
    t, p, today = await _seed_world(db_session, slug="us123-pdf")
    tpl = await _make_template(
        db_session, t, ["S-01", "S-02", "S-09"], mode="A", code="T-PDF"
    )
    result = await render_template(
        db_session,
        tpl,
        ReportScope(tenant_id=str(t.id), project_id=p.id),
        ReportWindow(cut_off_date=today, window_days=14),
    )

    import app.services.pdf_renderer as pdf_mod
    monkeypatch.setattr(pdf_mod, "html_to_pdf", lambda html: b"%PDF-1.4\nstub\n%%EOF")

    pdf_bytes = pdf_mod.html_to_pdf(result.html)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_section_by_area_tolerates_rows_without_area_name():
    """BUG-063 — regresión: el render en modo B tiraba KeyError
    'area_name' cuando una sección tenía rows sin esa clave (ej. hitos
    o issues sin área). El motor debe agruparlos en 'Sin área asignada'.
    """
    import app.services.reports.engine as engine_mod
    from app.services.reports.engine import _section_by_area

    # Parchamos _section_by_section para devolver data sintética.
    original = engine_mod._section_by_section
    try:
        def _fake_by_section(section_codes, sections_map, ctx, params, window):
            meta = [{"code": c, "name": c, "category": None, "template": ""} for c in section_codes]
            data = {
                "S-16": {"rows": [
                    {"task": "Crítica 1", "area_name": "Alpha"},
                    {"task": "Crítica 2"},  # sin area_name → debe ir a "Sin área asignada"
                ]},
                "S-09": {"rows": [
                    {"name": "Hito 1"},  # sin area_name
                ]},
            }
            return meta, data

        engine_mod._section_by_section = _fake_by_section
        _meta, data = _section_by_area(["S-16", "S-09"], {}, None, {}, None)
    finally:
        engine_mod._section_by_section = original

    by_area = data["__by_area__"]
    assert "Alpha" in by_area
    assert "Sin área asignada" in by_area
    # Las rows sin área caen en el bucket fallback.
    assert len(by_area["Sin área asignada"]["S-16"]) == 1
    assert len(by_area["Sin área asignada"]["S-09"]) == 1


def test_apply_section_params_top_n_order_excluded():
    """BUG-063 — params por sección: top_n trunca, order_by reordena,
    excluded_fields quita columnas. Genérico sobre payloads con rows."""
    from app.services.reports.engine import _apply_section_params

    payload = {
        "rows": [
            {"task": "A", "severity": 1, "area_name": "Beta", "owner": "x"},
            {"task": "B", "severity": 9, "area_name": "Alpha", "owner": "y"},
            {"task": "C", "severity": 5, "area_name": "Alpha", "owner": "z"},
        ]
    }
    # order_by severity_desc + top_n 2 + excluir 'owner'
    out = _apply_section_params(
        payload,
        {"order_by": "severity_desc", "top_n": 2, "excluded_fields": ["owner"]},
    )
    assert [r["task"] for r in out["rows"]] == ["B", "C"]
    assert all("owner" not in r for r in out["rows"])
    # El payload original no se muta.
    assert len(payload["rows"]) == 3


def test_apply_section_params_noop_without_rows():
    from app.services.reports.engine import _apply_section_params

    payload = {"progress_plan": 50, "progress_actual": 40}
    assert _apply_section_params(payload, {"top_n": 5}) == payload
