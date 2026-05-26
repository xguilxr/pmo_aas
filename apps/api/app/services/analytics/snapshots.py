"""Cómputo y persistencia de MetricSnapshot (US-151).

Calcula las métricas de *stock* de un scope (tenant/organización/programa/
proyecto) y las persiste de forma idempotente en `metric_snapshots`. El
worker corre esto semanalmente; también se usa para el backfill on-demand.

La lógica de agregación es intencionalmente similar a la de
`api/v1/endpoints/dashboard.py` para que el dashboard interactivo y la
serie histórica midan lo mismo.
"""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric_snapshot import MetricSnapshot
from app.models.modules import ChangeRequest, Issue, Risk
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.project_request import ProjectRequest
from app.models.task import Task

ACTIVE_PHASES = ["planning", "execution", "support"]
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
    values["avg_progress"] = (
        round(sum(int(r.progress or 0) for r in active) / len(active), 2)
        if active
        else 0
    )
    values["budget_plan"] = float(sum(float(r.budget or 0) for r in proj_rows))
    values["budget_actual"] = float(sum(float(r.actual_budget or 0) for r in proj_rows))

    if project_ids:
        values["open_risks"] = await _count(
            db,
            select(func.count(Risk.id)).where(
                Risk.project_id.in_(project_ids), Risk.status != "closed"
            ),
        )
        values["severe_risks"] = await _count(
            db,
            select(func.count(Risk.id)).where(
                Risk.project_id.in_(project_ids),
                Risk.status != "closed",
                Risk.severity >= SEVERE_THRESHOLD,
            ),
        )
        values["open_issues"] = await _count(
            db,
            select(func.count(Issue.id)).where(
                Issue.project_id.in_(project_ids),
                Issue.status.in_(["open", "in_progress"]),
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
                Task.project_id.in_(project_ids), Task.status == "done"
            ),
        )
        for days, key in ((7, "milestones_due_7"), (14, "milestones_due_14"), (30, "milestones_due_30")):
            values[key] = await _count(
                db,
                select(func.count(Task.id)).where(
                    Task.project_id.in_(project_ids),
                    Task.is_milestone.is_(True),
                    Task.status != "done",
                    Task.end_date.is_not(None),
                    Task.end_date >= ref_date,
                    Task.end_date <= ref_date + timedelta(days=days),
                ),
            )

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
            **{k: values[k] for k in METRIC_FIELDS if k in values},
        )
        db.add(snap)
        return snap

    for k in METRIC_FIELDS:
        if k in values:
            setattr(existing, k, values[k])
    return existing


async def snapshot_tenant(
    db: AsyncSession, tenant_id: str | UUID, snapshot_date: date | None = None
) -> int:
    """Persiste snapshots de un tenant a los 4 niveles. Devuelve filas escritas."""
    tenant_id = str(tenant_id)
    snapshot_date = snapshot_date or date.today()
    written = 0

    async def _do(scope_type: str, scope_id: str) -> None:
        nonlocal written
        values = await compute_snapshot_values(
            db, tenant_id, scope_type, scope_id, ref_date=snapshot_date
        )
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
