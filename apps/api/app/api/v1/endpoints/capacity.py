"""US-183 — Endpoints de capacidad/saturación de recursos (Revamp 1.0).

- GET /capacity/summary   — saturación individual + por rol/área/equipo.
- GET /capacity/conflicts — recursos sobreasignados con proyectos en choque
  y recomendación (gobernanza de capacidad).
- GET /capacity/weekly-load — US-208: carga por persona y semana (% FTE) más
  capacidad vs demanda, críticos compartidos y sugerencias.
- GET /projects/{id}/resource-load — carga de los recursos de UN proyecto
  (demanda total de cada recurso en todos sus proyectos).
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.capacity import (
    WINDOWS,
    resource_capacity_summary,
    resource_conflicts,
    weekly_load,
)

router = APIRouter(prefix="/capacity", tags=["capacity"])
project_load_router = APIRouter(
    prefix="/projects/{project_id}/resource-load", tags=["capacity"]
)


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _get_tenant(db: AsyncSession, tenant_id: UUID) -> Tenant | None:
    return (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()


async def _get_tenant_obligatorio(db: AsyncSession, tenant_id: UUID) -> Tenant:
    """El inquilino de la sesión, o 403.

    Existe porque `_get_tenant` devuelve `Tenant | None` y los servicios que
    leen `tenant.settings` necesitan uno de verdad. Que no esté significa que la
    sesión apunta a un inquilino borrado: no es un caso a tratar con un default,
    es una sesión que ya no vale.
    """
    tenant = await _get_tenant(db, tenant_id)
    if tenant is None:
        raise forbidden()
    return tenant


def _window(window: str) -> str:
    return window if window in WINDOWS else "week"


@router.get("/summary")
async def capacity_summary(
    window: str = Query(default="week"),
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(db, _tenant(cu))
    return await resource_capacity_summary(
        db,
        tenant,
        window=_window(window),
        organization_id=str(organization_id) if organization_id else None,
    )


@router.get("/weekly-load")
async def capacity_weekly_load(
    weeks: int = Query(default=12, ge=1, le=52),
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """US-208 — carga por persona y por semana, en % de FTE.

    El heatmap del artboard «Recursos › Capacidad», más los otros tres paneles
    de la pestaña en la misma respuesta: capacidad vs demanda, recursos críticos
    compartidos y la lectura de los dos. El porqué de que vayan juntos está en
    `weekly_load`.

    El techo de 52 semanas es para que nadie pida un heatmap de cinco años: la
    respuesta lleva una serie por recurso, y el ancho de la serie multiplica.
    """
    tenant = await _get_tenant_obligatorio(db, _tenant(cu))
    return await weekly_load(
        db,
        tenant,
        weeks=weeks,
        organization_id=str(organization_id) if organization_id else None,
    )


@router.get("/conflicts")
async def capacity_conflicts(
    window: str = Query(default="3weeks"),
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(db, _tenant(cu))
    return await resource_conflicts(
        db,
        tenant,
        window=_window(window),
        organization_id=str(organization_id) if organization_id else None,
    )


@project_load_router.get("")
async def project_resource_load(
    project_id: UUID,
    window: str = Query(default="3weeks"),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Carga de los recursos asignados a este proyecto. La demanda de cada
    recurso considera TODOS sus proyectos (así se ve el conflicto)."""
    from app.services.capacity import _load_assignments, window_range

    tenant = await _get_tenant(db, _tenant(cu))
    summary = await resource_capacity_summary(db, tenant, window=_window(window))
    start, end = window_range(_window(window))
    rows = await _load_assignments(
        db, str(_tenant(cu)), start, end, project_id=str(project_id)
    )
    project_actor_ids = {str(r.actor_id) for r in rows}
    alloc_here = {}
    for r in rows:
        if r.status == "activa" and r.allocation_pct is not None:
            aid = str(r.actor_id)
            alloc_here[aid] = alloc_here.get(aid, 0.0) + float(r.allocation_pct)
    resources = [
        {**res, "allocation_in_project_pct": round(alloc_here.get(res["actor_id"], 0.0), 2)}
        for res in summary["resources"]
        if res["actor_id"] in project_actor_ids
    ]
    return {
        "window": summary["window"],
        "start": summary["start"],
        "end": summary["end"],
        "resources": resources,
    }
