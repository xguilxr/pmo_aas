"""Cómputo y persistencia de MetricSnapshot (US-151).

Calcula las métricas de *stock* de un scope (tenant/organización/programa/
proyecto) y las persiste de forma idempotente en `metric_snapshots`. El
worker corre esto semanalmente; también se usa para el backfill on-demand.

La lógica de agregación es intencionalmente similar a la de
`api/v1/endpoints/dashboard.py` para que el dashboard interactivo y la
serie histórica midan lo mismo.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import get_args
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unidades import razon_a_pct
from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import ChangeRequest, Issue, Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.project_request import ProjectRequest
from app.models.task import Task
from app.schemas.project import FASES_TERMINALES, ProjectPhase
from app.services.indicadores import avance_de_cartera
from app.services.progress_calculator import plan_rollup_map

# ADR-022: se deriva del vocabulario en vez de repetirlo. Cuando D-2 renombró
# `support` → `hypercare`, esta lista era el sitio que se quedaba con el nombre
# viejo **sin fallar** —los proyectos en hypercare habrían desaparecido de los
# snapshots en silencio—, y por eso llevó prueba propia. Derivarla cierra la
# clase entera: añadir una fase terminal la excluye de aquí sin tocar nada.
ACTIVE_PHASES = [f for f in get_args(ProjectPhase) if f not in FASES_TERMINALES]
SEVERE_THRESHOLD = 13

# Métricas numéricas que componen el snapshot (todas las columnas escalares).
METRIC_FIELDS = (
    "projects_total",
    "projects_active",
    "health_green",
    "health_yellow",
    "health_red",
    "avg_progress",
    "budget_plan",
    "budget_actual",
    "open_risks",
    "severe_risks",
    "open_issues",
    "changes_in_review",
    "requests_in_review",
    "tasks_total",
    "tasks_done",
    "milestones_due_7",
    "milestones_due_14",
    "milestones_due_30",
)


def _planned_progress(start: date | None, end: date | None, ref_date: date) -> float:
    """% planeado por tiempo transcurrido (lineal start→end). Mismo criterio
    que dashboard `_plan_progress_for`, evaluado a `ref_date`."""
    if not start or not end:
        return 0.0
    if ref_date <= start:
        return 0.0
    if ref_date >= end:
        return 100.0
    total = (end - start).days or 1
    elapsed = (ref_date - start).days
    return max(0.0, min(100.0, razon_a_pct(elapsed, total, decimales=2)))


def _project_conditions(tenant_id: str, scope_type: str, scope_id: str) -> list:
    conds = [Project.tenant_id == str(tenant_id), Project.deleted_at.is_(None)]
    if scope_type == "organization":
        conds.append(Project.organization_id == str(scope_id))
    elif scope_type == "program":
        conds.append(Project.program_id == str(scope_id))
    elif scope_type == "project":
        conds.append(Project.id == str(scope_id))
    return conds


async def compute_snapshot_values(
    db: AsyncSession,
    tenant_id: str | UUID,
    scope_type: str,
    scope_id: str | UUID,
    ref_date: date | None = None,
    restrict_project_ids: list[str] | None = None,
) -> dict:
    """Devuelve el dict de métricas para un scope a la fecha de referencia.

    `restrict_project_ids` (no-admin): limita el cómputo a esos proyectos
    visibles para el usuario; `None` = sin restricción (admin/job)."""
    tenant_id = str(tenant_id)
    scope_id = str(scope_id)
    ref_date = ref_date or date.today()

    conds = _project_conditions(tenant_id, scope_type, scope_id)
    if restrict_project_ids is not None:
        conds.append(Project.id.in_(restrict_project_ids or ["__none__"]))
    proj_rows = (
        await db.execute(
            select(
                Project.id,
                Project.phase,
                Project.health_status,
                Project.progress,
                Project.budget,
                Project.actual_budget,
                Project.start_date,
                Project.end_date,
            ).where(*conds)
        )
    ).all()

    project_ids = [str(r.id) for r in proj_rows]
    active = [r for r in proj_rows if r.phase in ACTIVE_PHASES]

    values: dict = {f: 0 for f in METRIC_FIELDS}
    values["projects_total"] = len(proj_rows)
    values["projects_active"] = len(active)
    values["health_green"] = sum(1 for r in proj_rows if r.health_status == "green")
    values["health_yellow"] = sum(1 for r in proj_rows if r.health_status == "yellow")
    values["health_red"] = sum(1 for r in proj_rows if r.health_status == "red")
    # BUG-082: el avance de la serie histórica debe ser el avance *efectivo*
    # (rollup WBS del plan, ENH-155) — el mismo que muestra el dashboard en
    # vivo. Antes se leía la columna `Project.progress` (manual), que queda en
    # 0 para proyectos cuyo avance se deriva del plan, así que la "evolución de
    # avance" salía en 0 aunque el proyecto tuviera progreso real. El rollup
    # cubre proyectos con tareas; el resto cae al `progress` manual.
    # DAT-09: el promedio lo define `indicadores.avance_de_cartera`, no este
    # archivo. Antes tenía su propia división y su propio `else 0`, y así es
    # como la corrección de la ficha llegó al tablero y no aquí.
    rollup = await plan_rollup_map(db, [str(r.id) for r in active]) if active else {}
    values["avg_progress"] = avance_de_cartera(
        [rollup.get(str(r.id), float(r.progress or 0)) for r in active]
    )
    values["budget_plan"] = float(sum(float(r.budget or 0) for r in proj_rows))
    values["budget_actual"] = float(sum(float(r.actual_budget or 0) for r in proj_rows))

    if project_ids:
        values["open_risks"] = await _count(
            db,
            select(func.count(Risk.id)).where(
                Risk.project_id.in_(project_ids), Risk.status != "resolved"  # US-179
            ),
        )
        values["severe_risks"] = await _count(
            db,
            select(func.count(Risk.id)).where(
                Risk.project_id.in_(project_ids),
                Risk.status != "resolved",  # US-179
                Risk.severity >= SEVERE_THRESHOLD,
            ),
        )
        values["open_issues"] = await _count(
            db,
            select(func.count(Issue.id)).where(
                Issue.project_id.in_(project_ids),
                Issue.status.in_(["open", "in_progress", "on_hold"]),  # US-179
            ),
        )
        values["changes_in_review"] = await _count(
            db,
            select(func.count(ChangeRequest.id)).where(
                ChangeRequest.project_id.in_(project_ids),
                ChangeRequest.status == "in_review",
            ),
        )
        values["tasks_total"] = await _count(
            db, select(func.count(Task.id)).where(Task.project_id.in_(project_ids))
        )
        values["tasks_done"] = await _count(
            db,
            select(func.count(Task.id)).where(
                Task.project_id.in_(project_ids), Task.status == "completed"
            ),
        )
        for days, key in ((7, "milestones_due_7"), (14, "milestones_due_14"), (30, "milestones_due_30")):
            values[key] = await _count(
                db,
                select(func.count(Task.id)).where(
                    Task.project_id.in_(project_ids),
                    Task.is_milestone.is_(True),
                    Task.status != "completed",
                    Task.end_date.is_not(None),
                    Task.end_date >= ref_date,
                    Task.end_date <= ref_date + timedelta(days=days),
                ),
            )

    # US-161: avance PLANEADO (curva-S, S-07) — promedio del % planeado por
    # tiempo transcurrido (start_date→end_date) sobre los proyectos activos.
    # Se guarda en `extras` para no migrar una columna por métrica derivada.
    planned = [_planned_progress(r.start_date, r.end_date, ref_date) for r in active]
    values["extras"] = {
        "avg_progress_plan": round(sum(planned) / len(planned), 2) if planned else 0
    }

    # Solicitudes en revisión: viven a nivel tenant/organización (no tienen
    # project_id). A nivel programa/proyecto no aplica → 0.
    if scope_type in ("tenant", "organization"):
        req_stmt = select(func.count(ProjectRequest.id)).where(
            ProjectRequest.tenant_id == tenant_id,
            ProjectRequest.status == "in_review",
        )
        if scope_type == "organization":
            req_stmt = req_stmt.where(ProjectRequest.organization_id == scope_id)
        values["requests_in_review"] = await _count(db, req_stmt)

    return values


async def _count(db: AsyncSession, stmt) -> int:
    return (await db.execute(stmt)).scalar_one() or 0


async def aggregate_project_trends(
    db: AsyncSession,
    tenant_id: str | UUID,
    project_ids: list[str],
    since: date,
):
    """Serie de tendencia agregada desde snapshots de un conjunto de proyectos
    (para usuarios no-admin que ven solo sus proyectos). Suma los contadores y
    promedia `avg_progress` por fecha. Devuelve objetos con los mismos atributos
    que MetricSnapshot (acceso por getattr) para reusar el shape del endpoint."""
    from types import SimpleNamespace

    if not project_ids:
        return []
    snaps = (
        await db.execute(
            select(MetricSnapshot)
            .where(
                MetricSnapshot.tenant_id == str(tenant_id),
                MetricSnapshot.scope_type == "project",
                MetricSnapshot.scope_id.in_(project_ids),
                MetricSnapshot.snapshot_date >= since,
            )
            .order_by(MetricSnapshot.snapshot_date)
        )
    ).scalars().all()

    buckets: dict[date, dict] = {}
    progress: dict[date, list[float]] = {}
    for s in snaps:
        d = s.snapshot_date
        b = buckets.setdefault(d, {f: 0.0 for f in METRIC_FIELDS})
        for f in METRIC_FIELDS:
            if f == "avg_progress":
                continue
            b[f] += float(getattr(s, f) or 0)
        progress.setdefault(d, []).append(float(s.avg_progress or 0))

    out = []
    for d in sorted(buckets):
        b = buckets[d]
        pr = progress.get(d) or [0.0]
        b["avg_progress"] = round(sum(pr) / len(pr), 2)
        out.append(SimpleNamespace(snapshot_date=d, **b))
    return out


async def upsert_snapshot(
    db: AsyncSession,
    tenant_id: str | UUID,
    scope_type: str,
    scope_id: str | UUID,
    snapshot_date: date,
    values: dict,
) -> MetricSnapshot:
    """Inserta o actualiza la fila del scope/fecha (idempotente)."""
    tenant_id = str(tenant_id)
    scope_id = str(scope_id)
    existing = (
        await db.execute(
            select(MetricSnapshot).where(
                MetricSnapshot.tenant_id == tenant_id,
                MetricSnapshot.scope_type == scope_type,
                MetricSnapshot.scope_id == scope_id,
                MetricSnapshot.snapshot_date == snapshot_date,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        snap = MetricSnapshot(
            tenant_id=tenant_id,
            scope_type=scope_type,
            scope_id=scope_id,
            snapshot_date=snapshot_date,
            extras=values.get("extras", {}),
            **{k: values[k] for k in METRIC_FIELDS if k in values},
        )
        db.add(snap)
        return snap

    for k in METRIC_FIELDS:
        if k in values:
            setattr(existing, k, values[k])
    if "extras" in values:
        existing.extras = values["extras"]
    return existing


async def snapshot_tenant(
    db: AsyncSession, tenant_id: str | UUID, snapshot_date: date | None = None
) -> int:
    """Persiste snapshots de un tenant a los 4 niveles. Devuelve filas escritas."""
    tenant_id = str(tenant_id)
    snapshot_date = snapshot_date or date.today()
    written = 0

    # US-180: refrescar la salud auto de todos los proyectos del tenant
    # antes de contar, y llevar el desglose por dimensiones al snapshot
    # de scope proyecto (extras.health_dimensions) para tendencias.
    from app.models.tenant import Tenant
    from app.services.project_health import refresh_health_bulk

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    tenant_projects = (
        await db.execute(
            select(Project).where(
                Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    health_map = await refresh_health_bulk(
        db, tenant, list(tenant_projects), today=snapshot_date
    )

    # US-184: sweep semanal de alertas de capacidad (dedupe 7 días). Nunca
    # debe tumbar el snapshot.
    if tenant is not None:
        try:
            from app.services.capacity_alerts import sweep_capacity_alerts

            await sweep_capacity_alerts(db, tenant, today=snapshot_date)
        except Exception:  # pragma: no cover
            logging.getLogger("pmoaas.analytics").exception(
                "capacity alerts sweep failed tenant=%s", tenant_id
            )

    async def _do(scope_type: str, scope_id: str) -> None:
        nonlocal written
        values = await compute_snapshot_values(
            db, tenant_id, scope_type, scope_id, ref_date=snapshot_date
        )
        if scope_type == "project" and scope_id in health_map:
            values.setdefault("extras", {})["health_dimensions"] = health_map[scope_id]["dims"]
        await upsert_snapshot(db, tenant_id, scope_type, scope_id, snapshot_date, values)
        written += 1

    await _do("tenant", tenant_id)

    org_ids = (
        await db.execute(
            select(Organization.id).where(Organization.tenant_id == tenant_id)
        )
    ).scalars().all()
    for oid in org_ids:
        await _do("organization", str(oid))

    prog_ids = (
        await db.execute(select(Program.id).where(Program.tenant_id == tenant_id))
    ).scalars().all()
    for pid in prog_ids:
        await _do("program", str(pid))

    proj_ids = (
        await db.execute(
            select(Project.id).where(
                Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    for pid in proj_ids:
        await _do("project", str(pid))

    await db.commit()
    return written


async def snapshot_all_tenants(
    db: AsyncSession, snapshot_date: date | None = None
) -> int:
    """Persiste snapshots de todos los tenants activos."""
    from app.models.tenant import Tenant

    snapshot_date = snapshot_date or date.today()
    tenant_ids = (
        await db.execute(select(Tenant.id).where(Tenant.is_active.is_(True)))
    ).scalars().all()
    total = 0
    for tid in tenant_ids:
        total += await snapshot_tenant(db, str(tid), snapshot_date)
    return total
