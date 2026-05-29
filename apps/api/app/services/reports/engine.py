"""US-123 — Report Builder render engine (EP020).

Toma una `ReportBuilderTemplate` declarativa (composición de section
codes del catálogo `report_sections`, US-120) más un `scope` y una
`window` temporal, y devuelve:

    {
        "html":          str,            # render HTML completo (Jinja2)
        "json":          dict,           # data estructurada por sección
        "sections_meta": list[dict],     # orden + meta de cada sección
    }

El motor soporta dos modos de composición:

- ``"A"`` / ``"by_section"`` — Modo Avance: secciones secuenciales,
  items ordenados por área→fecha dentro de cada una.
- ``"B"`` / ``"by_area"`` — Modo Seguimiento: el motor agrupa por área
  y dentro de cada área renderiza la lista de secciones aplicables.

Cada section code (S-XX) se asocia a un *builder* (``SECTION_BUILDERS``)
que devuelve un dict con la data calculada. Si no hay builder registrado
para un code (alguna de las 22 secciones aún sin implementación
completa), se devuelve un placeholder con ``status="unimplemented"``;
esto permite que las plantillas seed con secciones aún pendientes
rendericen igual sin romper.

**Exclusiones cruzadas (PLN/RAID):** la lista de hitos próximos (S-09)
y la de tareas críticas (S-16) se calculan primero; S-17 (tareas
retrasadas) y S-18 (próximas a vencer) excluyen los ids que ya hayan
aparecido en S-09/S-16 para que el reporte no las repita.

El export PDF se hace pasando ``result["html"]`` por
:func:`app.services.pdf_renderer.html_to_pdf` (US-130).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.models.area import Area
from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import Issue, Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.report_builder_template import ReportBuilderTemplate
from app.models.report_section import ReportSection
from app.models.task import Task
from app.models.user import User
from app.services.analytics.snapshots import METRIC_FIELDS
from app.services.pdf_renderer import render_html
from app.services.progress_calculator import compute_progress_detailed
from app.services.reports.branding import load_report_branding
from app.services.reports.gantt_renderer import render_gantt_svg
from app.services.reports.svg import gauge_svg

logger = logging.getLogger(__name__)

# Composition mode aliases (epic AC dice "by_section"/"by_area", DB usa
# "A"/"B" por longitud; aceptamos ambos en el input del engine).
_MODE_A = {"A", "by_section"}
_MODE_B = {"B", "by_area"}


@dataclass
class ReportScope:
    """Scope de un reporte. `project_id` es el caso v1.0 (Nivel 3/4)."""

    tenant_id: UUID | str
    project_id: UUID | str | None = None
    organization_id: UUID | str | None = None
    program_id: UUID | str | None = None
    # Nivel del reporte (1=portafolio, 2=org, 3=proyecto, 4=custom).
    level: int = 3
    # BUG-063: filtro de área a nivel reporte. Si está presente, el motor
    # post-filtra las rows de todas las secciones dejando solo las del
    # área seleccionada. None = todas las áreas.
    area_id: UUID | str | None = None


@dataclass
class ReportWindow:
    """Ventana temporal. `cut_off_date` define el "hoy" del reporte."""

    cut_off_date: date
    window_days: int = 14


@dataclass
class RenderResult:
    """Resultado del motor de render. La plantilla PDF consume `html`."""

    html: str
    json: dict[str, Any]
    sections_meta: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_template(
    db: AsyncSession, template_ref: ReportBuilderTemplate | UUID | str
) -> ReportBuilderTemplate:
    if isinstance(template_ref, ReportBuilderTemplate):
        return template_ref
    # Acepta id (UUID-like) o code (seed slug). Si no hay match por id,
    # intenta por code (los seeds siempre tienen code estable como
    # `L3-AVANCE`).
    ref = str(template_ref)
    row = (
        await db.execute(
            select(ReportBuilderTemplate).where(
                ReportBuilderTemplate.id == ref
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await db.execute(
                select(ReportBuilderTemplate).where(
                    ReportBuilderTemplate.code == ref
                )
            )
        ).scalar_one_or_none()
    if row is None:
        raise not_found("Plantilla de reporte")
    return row


async def _load_sections(
    db: AsyncSession, codes: list[str]
) -> dict[str, ReportSection]:
    if not codes:
        return {}
    rows = (
        await db.execute(
            select(ReportSection).where(ReportSection.code.in_(codes))
        )
    ).scalars().all()
    return {r.code: r for r in rows}


def _normalize_mode(mode: str) -> str:
    if mode in _MODE_A:
        return "A"
    if mode in _MODE_B:
        return "B"
    logger.warning("engine: unknown composition_mode %r, defaulting to A", mode)
    return "A"


# ---------------------------------------------------------------------------
# Cross-context shared between section builders
# ---------------------------------------------------------------------------


@dataclass
class _RenderContext:
    """Bag of pre-computed data shared between section builders.

    Se construye una sola vez por render para evitar N+1 queries cuando
    múltiples secciones leen las mismas tareas / risks / issues / áreas.
    """

    project: Project | None
    organization_name: str | None
    program_name: str | None
    pm_name: str | None
    tenant_name: str | None
    # ENH-146 — branding para la banda de marca de los reportes.
    tenant_logo_url: str | None = None
    client_logo_url: str | None = None
    tasks: list[Task] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    areas: dict[str, str] = field(default_factory=dict)
    # US-158 — serie histórica del proyecto (metric_snapshots) para S-05.
    snapshots: list[MetricSnapshot] = field(default_factory=list)
    # Exclusiones cruzadas: ids de tasks/risks/issues que ya aparecieron
    # en secciones anteriores y deben omitirse en S-17/S-18.
    excluded_task_ids: set[str] = field(default_factory=set)
    # Progress calculado (US-121 dispatch por tenant).
    progress_percent: float = 0.0
    progress_method: str = ""
    progress_fallback: str | None = None


async def _build_context(
    db: AsyncSession,
    scope: ReportScope,
) -> _RenderContext:
    project: Project | None = None
    org_name: str | None = None
    prog_name: str | None = None
    pm_name: str | None = None
    tasks: list[Task] = []
    risks: list[Risk] = []
    issues: list[Issue] = []
    areas: dict[str, str] = {}
    progress_pct = 0.0
    progress_method = ""
    progress_fallback: str | None = None

    if scope.project_id:
        pid = str(scope.project_id)
        project = (
            await db.execute(
                select(Project).where(
                    Project.id == pid,
                    Project.tenant_id == str(scope.tenant_id),
                    Project.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if project is None:
            raise not_found("Proyecto")
        org_name = (
            await db.execute(
                select(Organization.name).where(
                    Organization.id == project.organization_id
                )
            )
        ).scalar_one_or_none()
        if project.program_id:
            prog_name = (
                await db.execute(
                    select(Program.name).where(Program.id == project.program_id)
                )
            ).scalar_one_or_none()
        if project.pm_id:
            pm_row = (
                await db.execute(
                    select(User.full_name).where(User.id == project.pm_id)
                )
            ).first()
            pm_name = pm_row[0] if pm_row else None

        tasks = (
            await db.execute(select(Task).where(Task.project_id == pid))
        ).scalars().all()
        risks = (
            await db.execute(
                select(Risk).where(
                    Risk.tenant_id == str(scope.tenant_id),
                    Risk.project_id == pid,
                    Risk.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        issues = (
            await db.execute(
                select(Issue).where(
                    Issue.tenant_id == str(scope.tenant_id),
                    Issue.project_id == pid,
                    Issue.deleted_at.is_(None),
                )
            )
        ).scalars().all()

        area_ids: set[str] = set()
        for t in tasks:
            if t.area_id:
                area_ids.add(str(t.area_id))
        for r in risks:
            if r.area_id:
                area_ids.add(str(r.area_id))
        for i in issues:
            if i.area_id:
                area_ids.add(str(i.area_id))
        if area_ids:
            arows = (
                await db.execute(
                    select(Area.id, Area.name).where(Area.id.in_(area_ids))
                )
            ).all()
            areas = {str(aid): (name or "—") for aid, name in arows}

        result = await compute_progress_detailed(db, pid)
        progress_pct = result.value
        progress_method = result.method
        progress_fallback = result.fallback

        snapshots = (
            await db.execute(
                select(MetricSnapshot)
                .where(
                    MetricSnapshot.tenant_id == str(scope.tenant_id),
                    MetricSnapshot.scope_type == "project",
                    MetricSnapshot.scope_id == pid,
                )
                .order_by(MetricSnapshot.snapshot_date)
            )
        ).scalars().all()
    else:
        snapshots = []

    # ENH-146 — branding (nombre PMO + logos). Antes tenant_name quedaba en
    # None, dejando el running header del PDF en blanco.
    org_id_for_brand = project.organization_id if project else scope.organization_id
    branding = await load_report_branding(db, scope.tenant_id, org_id_for_brand)

    return _RenderContext(
        project=project,
        organization_name=org_name,
        program_name=prog_name,
        pm_name=pm_name,
        tenant_name=branding["tenant_name"],
        tenant_logo_url=branding["tenant_logo_url"],
        client_logo_url=branding["client_logo_url"],
        tasks=tasks,
        risks=risks,
        issues=issues,
        areas=areas,
        snapshots=list(snapshots),
        progress_percent=progress_pct,
        progress_method=progress_method,
        progress_fallback=progress_fallback,
    )


# ---------------------------------------------------------------------------
# Per-section builders
#
# Cada builder recibe (ctx, params, window) y devuelve un dict que va a
# `result.json` y se inyecta en la plantilla Jinja2 de la sección. La
# plantilla vive en `templates/pdf/sections/{code-lower}.html`.
# ---------------------------------------------------------------------------


def _area_label(ctx: _RenderContext, area_id: Any) -> str:
    if not area_id:
        return "Sin área asignada"
    return ctx.areas.get(str(area_id), "—")


def _is_delayed(t: Task, today: date) -> bool:
    if t.end_date is None:
        return False
    if t.status == "done" or (t.progress or 0) >= 100:
        return False
    return t.end_date < today


def _task_to_row(ctx: _RenderContext, t: Task) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "wbs": t.wbs,
        "name": t.name,
        "status": t.status,
        "progress": t.progress or 0,
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "area_name": _area_label(ctx, t.area_id),
        "is_critical": bool(getattr(t, "is_critical", False)),
        "is_milestone": bool(t.is_milestone),
    }


def _build_s01_header(ctx, params, window):
    p = ctx.project
    return {
        "title": (
            f"Reporte — {p.folio}" if p else "Reporte (sin proyecto)"
        ),
        "subtitle": p.name if p else None,
        "organization_name": ctx.organization_name,
        "program_name": ctx.program_name,
        "cut_off_date": window.cut_off_date.isoformat(),
    }


def _build_s02_info(ctx, params, window):
    p = ctx.project
    if not p:
        return {"empty": True}
    return {
        "folio": p.folio,
        "name": p.name,
        "description": p.description,
        "phase": p.phase,
        "type": p.type,
        "priority": p.priority,
        "pm_name": ctx.pm_name,
        "sponsor": p.sponsor,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
    }


def _build_s03_rag(ctx, params, window):
    p = ctx.project
    if not p:
        return {"empty": True}
    return {
        "status_rag": getattr(p, "status_rag", None) or "amber",
        "status_comment": getattr(p, "status_comment", None),
        "health_status": p.health_status,
    }


def _build_s04_summary(ctx, params, window):
    # Resumen ejecutivo: por default usa texto del proyecto / placeholder.
    # La generación IA real vive en EP008 (no se invoca aquí en v1.0; la
    # sección queda con summary vacío si no hay datos y la IA conversacional
    # de US-127 puede poblarlo).
    p = ctx.project
    return {
        "summary": (p.description if p and p.description else None),
    }


def _build_s06_progress(ctx, params, window):
    return {
        "percent": round(ctx.progress_percent, 1),
        "method": ctx.progress_method,
        "fallback": ctx.progress_fallback,
        # ENH-146 — gauge circular en vez de un número plano.
        "gauge_svg": gauge_svg(ctx.progress_percent),
    }


def _build_s08_progress_by_area(ctx, params, window):
    buckets: dict[str, dict[str, float]] = {}
    for t in ctx.tasks:
        label = _area_label(ctx, t.area_id)
        b = buckets.setdefault(label, {"total": 0, "done": 0, "progress_sum": 0.0})
        b["total"] += 1
        b["progress_sum"] += float(t.progress or 0)
        if t.status == "done":
            b["done"] += 1
    rows = []
    for label, b in sorted(buckets.items()):
        avg = round(b["progress_sum"] / b["total"], 1) if b["total"] else 0.0
        rows.append({
            "area_name": label,
            "total": int(b["total"]),
            "done": int(b["done"]),
            "avg_progress": avg,
        })
    return {"rows": rows}


def _build_s09_milestones_upcoming(ctx, params, window):
    today = window.cut_off_date
    horizon = today + timedelta(days=window.window_days)
    rows = []
    for t in ctx.tasks:
        if not t.is_milestone:
            continue
        if t.status == "done" or (t.progress or 0) >= 100:
            continue
        if not t.end_date:
            continue
        if today <= t.end_date <= horizon:
            rows.append(_task_to_row(ctx, t))
            ctx.excluded_task_ids.add(str(t.id))
    rows.sort(key=lambda r: (r["end_date"] or "", r["area_name"]))
    return {"rows": rows}


def _build_s16_critical(ctx, params, window):
    rows = []
    for t in ctx.tasks:
        if not getattr(t, "is_critical", False):
            continue
        if t.status == "done":
            continue
        rows.append(_task_to_row(ctx, t))
        ctx.excluded_task_ids.add(str(t.id))
    rows.sort(key=lambda r: (r["end_date"] or "9999-12-31", r["area_name"]))
    return {"rows": rows}


def _build_s17_delayed(ctx, params, window):
    today = window.cut_off_date
    rows = []
    for t in ctx.tasks:
        if str(t.id) in ctx.excluded_task_ids:
            continue  # Exclusión cruzada — ya salió en S-09 o S-16.
        if not _is_delayed(t, today):
            continue
        rows.append(_task_to_row(ctx, t))
    rows.sort(key=lambda r: (r["end_date"] or "", r["area_name"]))
    return {"rows": rows}


def _build_s18_upcoming(ctx, params, window):
    today = window.cut_off_date
    horizon = today + timedelta(days=window.window_days)
    rows = []
    for t in ctx.tasks:
        if str(t.id) in ctx.excluded_task_ids:
            continue  # Exclusión cruzada con S-09/S-16.
        if not t.end_date or t.status == "done":
            continue
        if today <= t.end_date <= horizon and not t.is_milestone:
            rows.append(_task_to_row(ctx, t))
    rows.sort(key=lambda r: (r["end_date"] or "", r["area_name"]))
    return {"rows": rows}


def _build_s11_risks(ctx, params, window):
    rows = []
    for r in ctx.risks:
        if r.status in ("closed", "materialized"):
            continue
        rows.append({
            "folio": r.folio,
            "title": r.title,
            "severity": r.severity,
            "status": r.status,
            "probability": r.probability,
            "impact": r.impact,
            "area_name": _area_label(ctx, r.area_id),
        })
    # severity puede ser entero (1-25 prob×impact) o string legacy.
    def _sev_key(sev):
        if sev is None:
            return 99
        if isinstance(sev, (int, float)):
            return -float(sev)  # mayor severity → primero
        sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sev_rank.get(str(sev).lower(), 9)

    rows.sort(key=lambda r: _sev_key(r["severity"]))
    return {"rows": rows}


def _build_s12_issues(ctx, params, window):
    rows = []
    for i in ctx.issues:
        if i.type != "issue":
            continue
        if i.status in ("resolved", "closed"):
            continue
        rows.append({
            "folio": i.folio,
            "title": i.title,
            "priority": i.priority,
            "status": i.status,
            "committed_date": (
                i.committed_date.isoformat() if i.committed_date else None
            ),
            "area_name": _area_label(ctx, i.area_id),
        })
    rows.sort(key=lambda r: (-(r["priority"] or 0), r["committed_date"] or ""))
    return {"rows": rows}


def _build_s14_actions(ctx, params, window):
    rows = []
    for i in ctx.issues:
        if i.type != "action":
            continue
        if i.status in ("resolved", "closed"):
            continue
        rows.append({
            "folio": i.folio,
            "title": i.title,
            "status": i.status,
            "committed_date": (
                i.committed_date.isoformat() if i.committed_date else None
            ),
            "area_name": _area_label(ctx, i.area_id),
        })
    rows.sort(key=lambda r: (r["committed_date"] or "", r["folio"] or ""))
    return {"rows": rows}


def _build_s13_decisions(ctx, params, window):
    rows = []
    for i in ctx.issues:
        if i.type != "decision":
            continue
        rows.append({
            "folio": i.folio,
            "title": i.title,
            "status": i.status,
            "committed_date": (
                i.committed_date.isoformat() if i.committed_date else None
            ),
            "area_name": _area_label(ctx, i.area_id),
        })
    rows.sort(key=lambda r: (r["committed_date"] or "", r["folio"] or ""))
    return {"rows": rows}


def _build_s19_gantt_snapshot(ctx, params, window):
    # ENH-146 — inlina el SVG del Gantt (US-132 render_gantt_svg) en vez de
    # un <img src> relativo que no resolvía bajo WeasyPrint. Si el render
    # falla, cae al endpoint snapshot para el preview HTTP.
    if not ctx.project:
        return {"empty": True}
    wbs_level = (params or {}).get("wbs_level", 1)
    try:
        svg = render_gantt_svg(ctx.project, ctx.tasks, wbs_level=wbs_level)
    except Exception:  # pragma: no cover - defensivo
        logger.exception("s19 gantt render failed for project %s", ctx.project.id)
        svg = ""
    return {
        "project_id": str(ctx.project.id),
        "wbs_level": wbs_level,
        "svg": svg,
        "snapshot_url": (
            f"/api/v1/projects/{ctx.project.id}/gantt/snapshot?wbs_level={wbs_level}"
        ),
    }


def _build_s20_team_composition(ctx, params, window):
    # Composición del equipo por área (modo B). Para v1.0 contamos owners
    # únicos por área para no depender del modelo Actor (que cambia en EP017).
    buckets: dict[str, set] = {}
    for t in ctx.tasks:
        label = _area_label(ctx, t.area_id)
        if t.owner_id:
            buckets.setdefault(label, set()).add(str(t.owner_id))
    return {
        "rows": [
            {"area_name": label, "count": len(owners)}
            for label, owners in sorted(buckets.items())
        ]
    }


def _build_s21_workload(ctx, params, window):
    # Carga por responsable: cuenta tareas activas por owner_id.
    buckets: dict[str, int] = {}
    for t in ctx.tasks:
        if t.status in ("done", "cancelled"):
            continue
        if not t.owner_id:
            continue
        buckets[str(t.owner_id)] = buckets.get(str(t.owner_id), 0) + 1
    rows = [
        {"owner_id": uid, "active_tasks": n}
        for uid, n in sorted(buckets.items(), key=lambda kv: -kv[1])
    ]
    return {"rows": rows}


def _build_s28_narrative(ctx, params, window):
    return {"text": (params or {}).get("text", "")}


_TREND_METRIC_LABELS = {
    "avg_progress": "Avance promedio (%)",
    "open_risks": "Riesgos abiertos",
    "severe_risks": "Riesgos severos",
    "open_issues": "Issues abiertos",
    "tasks_done": "Tareas completadas",
    "tasks_total": "Tareas totales",
    "budget_actual": "Presupuesto real",
    "projects_active": "Proyectos activos",
}


def _sparkline_svg(values: list[float], color: str = "#182e4e") -> str:
    from app.services.reports.svg import sparkline_svg

    return sparkline_svg(values, color)


def _build_s05_trends(ctx, params, window):
    """S-05 — Tendencia de una métrica desde metric_snapshots (US-158).

    Requiere que el job de snapshots (US-151) haya capturado historia del
    proyecto. Sin snapshots devuelve `empty=True` (la plantilla muestra un
    aviso, no rompe el render)."""
    metric = (params or {}).get("metric", "avg_progress")
    if metric not in METRIC_FIELDS:
        metric = "avg_progress"
    points = []
    for s in ctx.snapshots:
        raw = getattr(s, metric, 0)
        points.append({"date": s.snapshot_date.isoformat(), "value": float(raw or 0)})
    values = [p["value"] for p in points]
    first = values[0] if values else 0.0
    last = values[-1] if values else 0.0
    return {
        "metric": metric,
        "metric_label": _TREND_METRIC_LABELS.get(metric, metric),
        "points": points,
        "svg": _sparkline_svg(values) if values else "",
        "first": first,
        "last": last,
        "delta": last - first,
        "empty": len(values) == 0,
    }


def _build_s07_curve_s(ctx, params, window):
    """S-07 — Curva-S: avance planeado vs real acumulado desde metric_snapshots
    (US-161). El planeado se captura en `extras.avg_progress_plan` por snapshot."""
    from app.services.reports.svg import curve_svg

    points = []
    actual_vals: list[float] = []
    planned_vals: list[float] = []
    for s in ctx.snapshots:
        actual = float(getattr(s, "avg_progress", 0) or 0)
        planned = float((getattr(s, "extras", None) or {}).get("avg_progress_plan", 0) or 0)
        points.append({"date": s.snapshot_date.isoformat(), "actual": actual, "planned": planned})
        actual_vals.append(actual)
        planned_vals.append(planned)
    return {
        "points": points,
        "svg": curve_svg(actual_vals, planned_vals) if points else "",
        "last_actual": actual_vals[-1] if actual_vals else 0,
        "last_planned": planned_vals[-1] if planned_vals else 0,
        "empty": not points,
    }


def _build_s15_risk_matrix(ctx, params, window):
    """S-15 — Matriz 5×5 de riesgos abiertos (probabilidad × impacto)."""
    grid: dict[tuple[int, int], int] = {}
    total = 0
    for r in ctx.risks:
        if r.status in ("closed", "materialized"):
            continue
        if r.probability and r.impact:
            key = (int(r.probability), int(r.impact))
            grid[key] = grid.get(key, 0) + 1
            total += 1
    zone_bg = {"low": "#dcfce7", "mid": "#fef9c3", "high": "#fee2e2"}
    matrix = []
    for p in (5, 4, 3, 2, 1):
        cells = []
        for im in (1, 2, 3, 4, 5):
            sev = p * im
            zone = "low" if sev <= 6 else "mid" if sev <= 12 else "high"
            cells.append(
                {
                    "probability": p,
                    "impact": im,
                    "count": grid.get((p, im), 0),
                    "zone": zone,
                    "bg": zone_bg[zone],
                }
            )
        matrix.append({"probability": p, "cells": cells})
    return {"matrix": matrix, "total": total}


def _build_unimplemented(ctx, params, window):
    return {"status": "unimplemented"}


SECTION_BUILDERS: dict[str, Any] = {
    "S-05": _build_s05_trends,
    "S-07": _build_s07_curve_s,
    "S-15": _build_s15_risk_matrix,
    "S-01": _build_s01_header,
    "S-02": _build_s02_info,
    "S-03": _build_s03_rag,
    "S-04": _build_s04_summary,
    "S-06": _build_s06_progress,
    "S-08": _build_s08_progress_by_area,
    "S-09": _build_s09_milestones_upcoming,
    "S-11": _build_s11_risks,
    "S-12": _build_s12_issues,
    "S-13": _build_s13_decisions,
    "S-14": _build_s14_actions,
    "S-16": _build_s16_critical,
    "S-17": _build_s17_delayed,
    "S-18": _build_s18_upcoming,
    "S-19": _build_s19_gantt_snapshot,
    "S-20": _build_s20_team_composition,
    "S-21": _build_s21_workload,
    "S-28": _build_s28_narrative,
    # PRT (Nivel 1) — placeholders en v1.0; el módulo Nivel 1 (US-128)
    # podrá enriquecerlos con queries multi-proyecto.
    "S-33": _build_unimplemented,
    "S-34": _build_unimplemented,
    "S-35": _build_unimplemented,
    "S-36": _build_unimplemented,
}


def get_section_builder(code: str):
    """Public dispatch helper. Returns the placeholder if no builder."""
    return SECTION_BUILDERS.get(code, _build_unimplemented)


# ---------------------------------------------------------------------------
# Composition modes
# ---------------------------------------------------------------------------


def _apply_section_params(payload: dict[str, Any], params: dict) -> dict[str, Any]:
    """BUG-063: aplica los parámetros por sección (configurados inline en
    el canvas) al payload ya construido por el builder. Genérico para
    cualquier sección con `rows`:

    - ``order_by``: reordena rows (date_asc/date_desc/severity_desc/area).
    - ``top_n``: trunca a las primeras N rows.
    - ``excluded_fields``: quita esas keys de cada row (permite ocultar
      columnas sin quitar la sección).

    Secciones sin `rows` (header/summary/gauge) se devuelven intactas.
    """
    if not isinstance(payload, dict):
        return payload
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        return payload

    order_by = params.get("order_by")
    if order_by == "date_asc":
        rows = sorted(rows, key=lambda r: r.get("end_date") or r.get("date") or "9999")
    elif order_by == "date_desc":
        rows = sorted(rows, key=lambda r: r.get("end_date") or r.get("date") or "", reverse=True)
    elif order_by == "severity_desc":
        rows = sorted(rows, key=lambda r: r.get("severity") or 0, reverse=True)
    elif order_by == "area":
        rows = sorted(rows, key=lambda r: r.get("area_name") or "")

    top_n = params.get("top_n")
    if isinstance(top_n, int) and top_n > 0:
        rows = rows[:top_n]

    excluded = params.get("excluded_fields")
    if isinstance(excluded, list) and excluded:
        excluded_set = set(excluded)
        rows = [
            {k: v for k, v in r.items() if k not in excluded_set}
            if isinstance(r, dict) else r
            for r in rows
        ]

    out = dict(payload)
    out["rows"] = rows
    return out


def _section_by_section(
    section_codes: list[str],
    sections_map: dict[str, ReportSection],
    ctx: _RenderContext,
    params_by_code: dict[str, dict],
    window: ReportWindow,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Modo A — secuencial por sección. Cada sección renderiza una sola
    vez con sus items ordenados internamente por área→fecha.
    """
    meta: list[dict[str, Any]] = []
    data: dict[str, dict[str, Any]] = {}
    for code in section_codes:
        section = sections_map.get(code)
        builder = get_section_builder(code)
        params = params_by_code.get(code, {})
        try:
            payload = builder(ctx, params, window)
            payload = _apply_section_params(payload, params)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("engine: section %s builder failed: %s", code, exc)
            payload = {"status": "error", "error": str(exc)[:200]}
        meta.append({
            "code": code,
            "name": section.name if section else code,
            "category": section.category if section else None,
            "template": f"sections/{code.lower()}.html",
        })
        data[code] = payload
    return meta, data


def _apply_area_filter(
    data: dict[str, dict[str, Any]],
    ctx: _RenderContext,
    area_id: str,
) -> None:
    """BUG-063: filtra in-place las rows de cada sección dejando solo las
    del área seleccionada. Compara por `area_name` resuelto (las rows ya
    traen el nombre, no el id). Si el área no se puede resolver a un
    nombre, no filtra (defensivo). Re-deriva `__by_area__` si existe.
    """
    target_name = ctx.areas.get(str(area_id))
    if not target_name:
        return
    for code, payload in data.items():
        if code == "__by_area__":
            continue
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            continue
        payload["rows"] = [
            r for r in rows
            if isinstance(r, dict) and (r.get("area_name") or "Sin área asignada") == target_name
        ]
    # Si el modo B ya construyó __by_area__, recórtalo a la única área.
    if "__by_area__" in data and isinstance(data["__by_area__"], dict):
        data["__by_area__"] = {
            a: v for a, v in data["__by_area__"].items() if a == target_name
        }


def _section_by_area(
    section_codes: list[str],
    sections_map: dict[str, ReportSection],
    ctx: _RenderContext,
    params_by_code: dict[str, dict],
    window: ReportWindow,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Modo B — matriz invertida. Mismas secciones, pero el motor las
    agrupa por área. Las secciones header/EST/EQP/NAR/PRT van fuera del
    bucle de áreas (no tienen sentido por área); el resto se renderiza
    una vez por área filtrando ``area_name`` en sus rows.
    """
    meta, data = _section_by_section(
        section_codes, sections_map, ctx, params_by_code, window
    )

    # Partición de secciones: las que tienen rows con `area_name`
    # pueden re-particionarse por área. El resto queda como global.
    # BUG-063: usar .get() — no todas las rows traen `area_name`
    # (ej. tablas de hitos/issues sin área). Las que no, caen en
    # "Sin área asignada".
    area_names = sorted({
        row.get("area_name") or "Sin área asignada"
        for s in data.values()
        for row in s.get("rows", [])
    })
    by_area: dict[str, dict[str, list[dict[str, Any]]]] = {a: {} for a in area_names}
    for code, payload in data.items():
        rows = payload.get("rows")
        if not rows:
            continue
        for row in rows:
            area = row.get("area_name") or "Sin área asignada"
            by_area.setdefault(area, {}).setdefault(code, []).append(row)

    data["__by_area__"] = by_area
    return meta, data


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def render_template(
    db: AsyncSession,
    template_ref: ReportBuilderTemplate | UUID | str,
    scope: ReportScope,
    window: ReportWindow,
    *,
    params_overrides: dict[str, dict] | None = None,
) -> RenderResult:
    """Render a Report Builder template into HTML + JSON.

    Args:
        db: SQLAlchemy async session.
        template_ref: Template instance / id / seed code (`L3-AVANCE`...).
        scope: Tenant + project/org/program + level.
        window: `cut_off_date` + `window_days`.
        params_overrides: Per-section overrides (`{ "S-09": {...} }`).
            Falls back to `template.default_parameters` then `{}`.

    Returns:
        :class:`RenderResult` with `html`, `json`, `sections_meta`.

    Raises:
        AppError(404): template or project not found.
    """
    template = await _load_template(db, template_ref)
    mode = _normalize_mode(template.composition_mode)
    section_codes: list[str] = list(template.section_codes or [])
    sections_map = await _load_sections(db, section_codes)

    ctx = await _build_context(db, scope)

    # Params: defaults del template + overrides.
    default_params = template.default_parameters or {}
    overrides = params_overrides or {}
    params_by_code = {
        code: {**(default_params.get(code) or {}), **(overrides.get(code) or {})}
        for code in section_codes
    }

    if mode == "A":
        meta, data = _section_by_section(
            section_codes, sections_map, ctx, params_by_code, window
        )
    else:
        meta, data = _section_by_area(
            section_codes, sections_map, ctx, params_by_code, window
        )

    # BUG-063: filtro de área a nivel reporte. Post-filtra rows de cada
    # sección por el nombre del área seleccionada. Las secciones sin rows
    # (header/summary) no se tocan. Aplica antes de armar el HTML.
    if scope.area_id:
        _apply_area_filter(data, ctx, str(scope.area_id))

    # Render Jinja2 via shared pdf_renderer (US-037).
    title = (
        f"{template.name} — {ctx.project.folio}"
        if ctx.project
        else template.name
    )
    template_ctx = {
        "title": title,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "tenant_name": ctx.tenant_name or "",
        "tenant_logo_url": ctx.tenant_logo_url,
        "client_logo_url": ctx.client_logo_url,
        "cut_off_date": window.cut_off_date.isoformat(),
        "window_days": window.window_days,
        "template": {
            "id": str(template.id),
            "code": template.code,
            "name": template.name,
            "level": template.level,
            "composition_mode": mode,
        },
        "project": (
            {
                "id": str(ctx.project.id),
                "folio": ctx.project.folio,
                "name": ctx.project.name,
            }
            if ctx.project
            else None
        ),
        "pm_name": ctx.pm_name,
        "scope": {
            "tenant_id": str(scope.tenant_id),
            "project_id": str(scope.project_id) if scope.project_id else None,
            "organization_id": (
                str(scope.organization_id) if scope.organization_id else None
            ),
            "program_id": str(scope.program_id) if scope.program_id else None,
            "level": scope.level,
        },
        "sections_meta": meta,
        "sections_data": data,
        "mode": mode,
    }
    html = render_html("builder.html", template_ctx)

    return RenderResult(
        html=html,
        json={
            "template": template_ctx["template"],
            "scope": template_ctx["scope"],
            "window": {
                "cut_off_date": window.cut_off_date.isoformat(),
                "window_days": window.window_days,
            },
            "sections": data,
        },
        sections_meta=meta,
    )
