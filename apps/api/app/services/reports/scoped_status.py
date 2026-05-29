"""Contexto de los reportes de status Nivel 1 (Portafolio/PMO) y Nivel 2
(Organización / Programa) — US-160.

Estos reportes viven **fuera** del Report Builder (que es project-only):
se derivan de los dashboards N1/N2 y se descargan desde sus páginas. Reusan
`compute_snapshot_values` (KPIs actuales), `metric_snapshots` (tendencias) y
los riesgos en vivo (matriz P×I).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.user import User
from app.services.analytics.snapshots import (
    aggregate_project_trends,
    compute_snapshot_values,
)
from app.services.reports.branding import load_report_branding
from app.services.reports.svg import donut_svg, gauge_svg, sparkline_svg, treemap_svg

_HEALTH_DONUT_COLOR = {"green": "#1F8A5B", "yellow": "#B26B12", "red": "#C0392B"}

_ZONE_BG = {"low": "#dcfce7", "mid": "#fef9c3", "high": "#fee2e2"}
_HEALTH_HEX = {"green": "#16a34a", "yellow": "#eab308", "red": "#dc2626"}


def _worst_health_color(row: dict) -> str:
    if row.get("red"):
        return _HEALTH_HEX["red"]
    if row.get("yellow"):
        return _HEALTH_HEX["yellow"]
    return _HEALTH_HEX["green"]
_TREND_COLOR = {"avg_progress": "#16a34a", "open_risks": "#d97706"}
_TREND_LABEL = {"avg_progress": "Avance promedio (%)", "open_risks": "Riesgos abiertos"}


def _risk_matrix(pairs: list[tuple[int, int]]) -> dict:
    grid: dict[tuple[int, int], int] = {}
    total = 0
    for p, i in pairs:
        grid[(p, i)] = grid.get((p, i), 0) + 1
        total += 1
    matrix = []
    for p in (5, 4, 3, 2, 1):
        cells = []
        for im in (1, 2, 3, 4, 5):
            sev = p * im
            zone = "low" if sev <= 6 else "mid" if sev <= 12 else "high"
            cells.append(
                {"probability": p, "impact": im, "count": grid.get((p, im), 0),
                 "zone": zone, "bg": _ZONE_BG[zone]}
            )
        matrix.append({"probability": p, "cells": cells})
    return {"matrix": matrix, "total": total}


async def _project_ids(db: AsyncSession, conds: list) -> list[str]:
    rows = (await db.execute(select(Project.id).where(*conds))).scalars().all()
    return [str(i) for i in rows]


def _project_conditions(tenant_id: str, scope_type: str, scope_id: str) -> list:
    conds = [Project.tenant_id == tenant_id, Project.deleted_at.is_(None)]
    if scope_type == "organization":
        conds.append(Project.organization_id == scope_id)
    elif scope_type == "program":
        conds.append(Project.program_id == scope_id)
    return conds


def _shape_trends(snaps) -> list[dict]:
    out = []
    for metric in ("avg_progress", "open_risks"):
        values = [float(getattr(s, metric) or 0) for s in snaps]
        out.append({
            "metric": metric,
            "label": _TREND_LABEL[metric],
            "svg": sparkline_svg(values, _TREND_COLOR[metric]) if values else "",
            "last": values[-1] if values else 0,
            "delta": (values[-1] - values[0]) if values else 0,
            "empty": not values,
        })
    return out


async def _scope_snapshots(db: AsyncSession, tenant_id: str, scope_type: str, scope_id: str, weeks: int):
    since = date.today() - timedelta(weeks=weeks)
    return (
        await db.execute(
            select(MetricSnapshot)
            .where(
                MetricSnapshot.tenant_id == tenant_id,
                MetricSnapshot.scope_type == scope_type,
                MetricSnapshot.scope_id == scope_id,
                MetricSnapshot.snapshot_date >= since,
            )
            .order_by(MetricSnapshot.snapshot_date)
        )
    ).scalars().all()


async def _risk_pairs(db: AsyncSession, project_ids: list[str]) -> list[tuple[int, int]]:
    if not project_ids:
        return []
    rows = (
        await db.execute(
            select(Risk.probability, Risk.impact).where(
                Risk.project_id.in_(project_ids),
                Risk.status != "closed",
                Risk.probability.is_not(None),
                Risk.impact.is_not(None),
            )
        )
    ).all()
    return [(int(p), int(i)) for p, i in rows]


def _money(n: float) -> str:
    return f"${n:,.0f}"


async def _health_rows_by(
    db: AsyncSession, tenant_id: str, group_col, name_map: dict[str, str], extra_conds: list
) -> list[dict]:
    """Agrupa proyectos por `group_col` (org_id o program_id) → conteos de salud
    + presupuesto. `name_map` resuelve id→nombre."""
    rows = (
        await db.execute(
            select(
                group_col,
                Project.health_status,
                func.count(Project.id),
                func.coalesce(func.sum(Project.budget), 0),
                func.coalesce(func.sum(Project.actual_budget), 0),
            )
            .where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None), *extra_conds)
            .group_by(group_col, Project.health_status)
        )
    ).all()
    agg: dict[str, dict] = {}
    for gid, health, cnt, bplan, bactual in rows:
        key = str(gid) if gid else "none"
        e = agg.setdefault(key, {
            "id": key, "name": name_map.get(key, "Sin asignar"),
            "green": 0, "yellow": 0, "red": 0, "total": 0,
            "budget_plan": 0.0, "budget_actual": 0.0,
        })
        if health in ("green", "yellow", "red"):
            e[health] += int(cnt)
        e["total"] += int(cnt)
        e["budget_plan"] += float(bplan or 0)
        e["budget_actual"] += float(bactual or 0)
    for e in agg.values():
        e["budget_plan_fmt"] = _money(e["budget_plan"])
        e["budget_actual_fmt"] = _money(e["budget_actual"])
    return sorted(agg.values(), key=lambda r: (-r["red"], -r["total"]))


async def build_scope_status_context(
    db: AsyncSession,
    tenant_id: UUID | str,
    scope_type: str,
    scope_id: UUID | str | None,
    weeks: int = 12,
    restrict_project_ids: list[str] | None = None,
) -> dict:
    """Contexto del reporte de status para tenant/organization/program.

    `restrict_project_ids` (no-admin): limita KPIs, riesgos, tablas y
    tendencias a los proyectos visibles del usuario; `None` = sin restricción."""
    tenant_id = str(tenant_id)
    if scope_type == "tenant":
        scope_id = tenant_id
        scope_label = "Portafolio (toda la PMO)"
        title = "Reporte de Status — Portafolio PMO"
    elif scope_type == "organization":
        if not scope_id:
            raise not_found("Organización")
        scope_id = str(scope_id)
        org = (
            await db.execute(
                select(Organization).where(
                    Organization.id == scope_id, Organization.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if org is None:
            raise not_found("Organización")
        scope_label = org.name
        title = f"Reporte de Status — {org.name}"
    elif scope_type == "program":
        if not scope_id:
            raise not_found("Programa")
        scope_id = str(scope_id)
        prog = (
            await db.execute(
                select(Program).where(
                    Program.id == scope_id, Program.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if prog is None:
            raise not_found("Programa")
        scope_label = prog.name
        title = f"Reporte de Status — {prog.name}"
    else:
        raise not_found("Scope")

    kpis = await compute_snapshot_values(
        db, tenant_id, scope_type, scope_id, restrict_project_ids=restrict_project_ids
    )
    conds = _project_conditions(tenant_id, scope_type, scope_id)
    if restrict_project_ids is not None:
        conds.append(Project.id.in_(restrict_project_ids or ["__none__"]))
    pids = await _project_ids(db, conds)
    if restrict_project_ids is None:
        snaps = await _scope_snapshots(db, tenant_id, scope_type, scope_id, weeks)
    else:
        snaps = await aggregate_project_trends(
            db, tenant_id, pids, date.today() - timedelta(weeks=weeks)
        )
    trends = _shape_trends(snaps)
    risk_matrix = _risk_matrix(await _risk_pairs(db, pids))
    # Filtro de proyectos visibles para las tablas comparativas (no-admin).
    restrict_conds = (
        [Project.id.in_(restrict_project_ids or ["__none__"])]
        if restrict_project_ids is not None
        else []
    )

    # Tabla comparativa según nivel.
    rows: list[dict] = []
    rows_kind = ""
    if scope_type == "tenant":
        org_names = {
            str(i): n for i, n in (
                await db.execute(
                    select(Organization.id, Organization.name).where(
                        Organization.tenant_id == tenant_id
                    )
                )
            ).all()
        }
        rows = await _health_rows_by(
            db, tenant_id, Project.organization_id, org_names, restrict_conds
        )
        rows_kind = "organizations"
    elif scope_type == "organization":
        prog_names = {
            str(i): n for i, n in (
                await db.execute(
                    select(Program.id, Program.name).where(
                        Program.organization_id == scope_id
                    )
                )
            ).all()
        }
        rows = await _health_rows_by(
            db, tenant_id, Project.program_id, prog_names,
            [Project.organization_id == scope_id, *restrict_conds],
        )
        rows_kind = "programs"
    else:  # program → lista de proyectos
        prj = (
            await db.execute(
                select(Project).where(*conds).order_by(Project.folio)
            )
        ).scalars().all()
        pm_ids = sorted({p.pm_id for p in prj if p.pm_id})
        pm_names = {}
        if pm_ids:
            pm_names = {
                str(i): n for i, n in (
                    await db.execute(
                        select(User.id, User.full_name).where(User.id.in_(pm_ids))
                    )
                ).all()
            }
        rows = [
            {
                "folio": p.folio, "name": p.name, "phase": p.phase,
                "health": p.health_status, "progress": int(p.progress or 0),
                "pm_name": pm_names.get(str(p.pm_id)) if p.pm_id else None,
                "budget_plan": float(p.budget or 0),
                "budget_plan_fmt": _money(float(p.budget or 0)),
                "budget_actual_fmt": _money(float(p.actual_budget or 0)),
            }
            for p in prj
        ]
        rows_kind = "projects"

    # ENH-146 — branding (nombre PMO + logos). El logo de cliente aplica a
    # nivel organización; portafolio/programa muestran solo la marca PMO.
    brand_org_id = scope_id if scope_type == "organization" else None
    branding = await load_report_branding(db, tenant_id, brand_org_id)
    tenant_name = branding["tenant_name"]

    # Heatmap (Org/Programa × Salud) — solo cuando las filas traen breakdown.
    heatmap_rows = rows if rows_kind in ("organizations", "programs") else []
    # Treemap (presupuesto × salud).
    if rows_kind == "projects":
        treemap_items = [
            {"label": r["name"], "value": r.get("budget_plan", 0),
             "color": _HEALTH_HEX.get(r.get("health"), "#9ca3af")}
            for r in rows
        ]
    else:
        treemap_items = [
            {"label": r["name"], "value": r.get("budget_plan", 0),
             "color": _worst_health_color(r)}
            for r in rows
        ]

    return {
        "title": title,
        "scope_label": scope_label,
        "scope_type": scope_type,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
        "tenant_name": tenant_name,
        "tenant_logo_url": branding["tenant_logo_url"],
        "client_logo_url": branding["client_logo_url"],
        "kpis": kpis,
        "health": {
            "green": kpis["health_green"],
            "yellow": kpis["health_yellow"],
            "red": kpis["health_red"],
        },
        # ENH-146 — donut de salud + gauge de avance (charts reales en PDF).
        "health_donut_svg": donut_svg(
            [
                {"label": "Verde", "value": kpis["health_green"], "color": _HEALTH_DONUT_COLOR["green"]},
                {"label": "Amarillo", "value": kpis["health_yellow"], "color": _HEALTH_DONUT_COLOR["yellow"]},
                {"label": "Rojo", "value": kpis["health_red"], "color": _HEALTH_DONUT_COLOR["red"]},
            ],
            center_label=str(
                kpis["health_green"] + kpis["health_yellow"] + kpis["health_red"]
            ),
            center_sub="proyectos",
            size=132,
        ),
        "progress_gauge_svg": gauge_svg(kpis.get("avg_progress") or 0),
        "budget_plan_fmt": _money(kpis["budget_plan"]),
        "budget_actual_fmt": _money(kpis["budget_actual"]),
        "trends": trends,
        "risk_matrix": risk_matrix,
        "rows": rows,
        "rows_kind": rows_kind,
        "heatmap_rows": heatmap_rows,
        "treemap_svg": treemap_svg(treemap_items),
    }
