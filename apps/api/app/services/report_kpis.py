"""KPIs estructurados para reportes — US-087.

Calcula los indicadores numéricos del período del reporte (avance,
costos, horas) desde datos derivados de Tasks + Project. Los campos
sin datos quedan en `None` para que la plantilla los oculte y NO los
muestre como "0" o "—" (decisión owner: ceros engañan).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unidades import razon_a_pct
from app.models.project import Project
from app.models.task import Task
from app.services.plan_metadata import compute_plan_rollup_progress


async def compute_kpis(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """Devuelve dict con KPIs del período. Las llaves cuyo cálculo
    no aplica al proyecto quedan en `None` (la plantilla las oculta).

    Estructura:
      - period_start, period_end (siempre presentes, ISO).
      - progress_pct_real: float | None (avg de Task.progress).
      - progress_pct_planned: float | None (% tareas que deberían
        estar a 100% por su end_date <= period_end).
      - cost_planned, cost_real: float | None (Project.budget /
        actual_budget si > 0).
      - hours_planned, hours_real: None (no existe la fuente todavía).
    """
    project = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()

    tasks = (
        await db.execute(
            select(Task).where(Task.project_id == str(project_id))
        )
    ).scalars().all()

    progress_pct_real: float | None = None
    progress_pct_planned: float | None = None
    if tasks:
        # ENH-109 — avance real = rollup jerárquico por WBS (promedio de los
        # items de nivel más alto), no el promedio plano de todas las tareas
        # (que mezclaba padres y hojas y subcontaba).
        rollup = compute_plan_rollup_progress(tasks)
        progress_pct_real = round(rollup, 1) if rollup is not None else None
        # planned: % de tareas cuyo end_date <= period_end y deberían
        # estar al 100%. Si ninguna tarea tiene end_date, no se puede.
        scoped = [t for t in tasks if t.end_date is not None]
        if scoped:
            should_be_done = sum(1 for t in scoped if t.end_date <= period_end)
            progress_pct_planned = razon_a_pct(should_be_done, len(scoped))

    cost_planned = (
        float(project.budget) if project and project.budget and project.budget > 0 else None
    )
    cost_real = (
        float(project.actual_budget)
        if project and project.actual_budget and project.actual_budget > 0
        else None
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "progress_pct_real": progress_pct_real,
        "progress_pct_planned": progress_pct_planned,
        "cost_planned": cost_planned,
        "cost_real": cost_real,
        "hours_planned": None,
        "hours_real": None,
    }


def kpis_have_any_value(kpis: dict[str, Any]) -> bool:
    """True si al menos un KPI numérico tiene valor (no None).
    Las fechas siempre están presentes, no cuentan como "valor"
    para la decisión de mostrar el bloque entero.
    """
    keys = (
        "progress_pct_real",
        "progress_pct_planned",
        "cost_planned",
        "cost_real",
        "hours_planned",
        "hours_real",
    )
    return any(kpis.get(k) is not None for k in keys)


def default_period_start(cut_off: date, days: int = 14) -> date:
    """Helper: el período por default es 14 días hacia atrás del corte."""
    return cut_off - timedelta(days=days)
