"""US-121 — Progress calculation service (EP020 Report Builder).

Computes a project's ``% avance`` according to the tenant-configured
method. Three modes are supported:

- ``by_task_count``: simple percent of tasks with ``status='completed'``.
- ``by_duration``: weighted by ``duration_days`` (falls back to
  ``end_date - start_date`` when ``duration_days`` is null).
- ``by_effort``: weighted by effort hours. The ``tasks.hours_estimated``
  column does not exist yet (deferred to US-087 fase 2), so this mode
  currently falls back to ``by_task_count`` and signals
  ``fallback="hours_unavailable"`` to the caller.

The default method is resolved from
``tenant.settings.report_builder.progress_calculation_method`` via
:func:`app.services.tenant_settings.get_progress_calculation_method`
(ENH-098). The Report Builder engine (US-123, Sprint 27) will be the
primary consumer; a thin ``GET /projects/{id}/progress`` endpoint is
exposed for smoke testing and for the project header.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unidades import razon_a_pct
from app.models.project import Project
from app.models.task import Task
from app.services.plan_metadata import compute_plan_rollup_progress

logger = logging.getLogger(__name__)

#: Methods accepted by :func:`compute_progress`. Mirrors
#: ``app.services.tenant_settings.PROGRESS_CALC_METHODS``.
SUPPORTED_METHODS: tuple[str, ...] = (
    "by_task_count",
    "by_duration",
    "by_effort",
)
DEFAULT_METHOD: str = "by_task_count"

#: Reason string returned when ``by_effort`` falls back to
#: ``by_task_count`` because the effort column is unavailable.
FALLBACK_HOURS_UNAVAILABLE = "hours_unavailable"


@dataclass(frozen=True)
class ProgressResult:
    """Outcome of :func:`compute_progress_detailed`."""

    value: float
    method: str
    fallback: str | None = None


def _task_duration(task: Task) -> float:
    """Return a positive duration weight for a task.

    Prefers ``duration_days``; otherwise derives from
    ``end_date - start_date``. Tasks without a usable duration get 0
    and contribute no weight. Single-day tasks count as 1.
    """
    if task.duration_days is not None and task.duration_days > 0:
        return float(task.duration_days)
    if task.start_date and task.end_date:
        delta = (task.end_date - task.start_date).days
        if delta >= 0:
            return float(delta + 1)  # inclusive
    return 0.0


def _percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    pct = razon_a_pct(numerator, denominator, decimales=6)
    if pct < 0.0:
        return 0.0
    if pct > 100.0:
        return 100.0
    return round(pct, 2)


async def _load_tenant_method(db: AsyncSession, project_id: UUID | str) -> str:
    """Resolve the tenant's configured progress method for a project."""
    pid = str(project_id)
    row = (
        await db.execute(select(Project.tenant_id).where(Project.id == pid))
    ).first()
    if row is None:
        return DEFAULT_METHOD
    tenant_id = row[0]
    try:
        from app.models.tenant import Tenant
        from app.services.tenant_settings import (
            get_progress_calculation_method,
        )

        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        ).scalar_one_or_none()
        if tenant is None:
            return DEFAULT_METHOD
        return get_progress_calculation_method(tenant)
    except Exception:  # pragma: no cover - defensive fallback
        logger.warning(
            "progress_calculator: tenant settings unavailable, "
            "defaulting to %s",
            DEFAULT_METHOD,
        )
        return DEFAULT_METHOD


async def compute_progress_detailed(
    db: AsyncSession,
    project_id: UUID | str,
    *,
    method: str | None = None,
) -> ProgressResult:
    """Compute progress and return method + optional fallback reason."""
    pid = str(project_id)
    resolved = method or await _load_tenant_method(db, pid)
    if resolved not in SUPPORTED_METHODS:
        logger.warning(
            "progress_calculator: unknown method %r, using %s",
            resolved,
            DEFAULT_METHOD,
        )
        resolved = DEFAULT_METHOD

    tasks = (
        await db.execute(select(Task).where(Task.project_id == pid))
    ).scalars().all()

    if not tasks:
        return ProgressResult(value=0.0, method=resolved, fallback=None)

    if resolved == "by_task_count":
        done = sum(1 for t in tasks if t.status == "completed")
        return ProgressResult(
            value=_percent(done, len(tasks)),
            method="by_task_count",
            fallback=None,
        )

    if resolved == "by_duration":
        total = sum(_task_duration(t) for t in tasks)
        done = sum(_task_duration(t) for t in tasks if t.status == "completed")
        if total <= 0:
            # No usable durations → fall back to task count to avoid 0.
            count_total = len(tasks)
            count_done = sum(1 for t in tasks if t.status == "completed")
            return ProgressResult(
                value=_percent(count_done, count_total),
                method="by_duration",
                fallback="duration_unavailable",
            )
        return ProgressResult(
            value=_percent(done, total),
            method="by_duration",
            fallback=None,
        )

    # by_effort — tasks.hours_estimated does not exist (US-087 fase 2).
    # Log once per call and fall back to by_task_count.
    logger.warning(
        "progress_calculator: by_effort requested but tasks.hours_estimated "
        "is unavailable; falling back to by_task_count"
    )
    done = sum(1 for t in tasks if t.status == "completed")
    return ProgressResult(
        value=_percent(done, len(tasks)),
        method="by_effort",
        fallback=FALLBACK_HOURS_UNAVAILABLE,
    )


async def compute_progress(
    db: AsyncSession,
    project_id: UUID | str,
    *,
    method: str | None = None,
) -> float:
    """Return the project's ``% avance`` (0..100) as a float.

    Thin wrapper over :func:`compute_progress_detailed` for callers that
    only need the numeric value.
    """
    result = await compute_progress_detailed(db, project_id, method=method)
    return result.value


async def plan_rollup_map(
    db: AsyncSession, project_ids: Iterable[UUID | str]
) -> dict[str, float]:
    """``{project_id: avance general derivado del plan (0..100)}`` para
    los proyectos que tienen tareas.

    Un solo ``SELECT ... WHERE project_id IN (...)`` (sin N+1). Los
    proyectos sin tareas quedan fuera del dict; el caller usa el avance
    manual (``Project.progress``) como fallback.
    """
    ids = [str(p) for p in project_ids]
    if not ids:
        return {}
    rows = (
        await db.execute(select(Task).where(Task.project_id.in_(ids)))
    ).scalars().all()
    by_project: dict[str, list[Task]] = {}
    for t in rows:
        by_project.setdefault(str(t.project_id), []).append(t)
    out: dict[str, float] = {}
    for pid, tasks in by_project.items():
        value = compute_plan_rollup_progress(tasks)
        if value is not None:
            out[pid] = value
    return out


async def effective_progress_map(
    db: AsyncSession, projects: list[Project]
) -> dict[str, float]:
    """``{project_id: avance efectivo}``: rollup del plan cuando el
    proyecto tiene tareas; si no, su ``Project.progress`` manual."""
    plan = await plan_rollup_map(db, [p.id for p in projects])
    return {
        str(p.id): plan.get(str(p.id), float(p.progress or 0))
        for p in projects
    }
