"""BUG-086 — fuente única de la cascada de visibilidad de Áreas y
Recursos (Actores) por proyecto.

Regla de propagación (catálogo tenant, US-103 + BUG-085):
- Un área es visible para un proyecto si tiene un ``AreaAssignment`` con
  ``is_global``, o al ``project_id``, al ``program_id`` del proyecto, o a
  la ``organization_id`` del proyecto.
- Un actor (recurso) es asignable en un proyecto si pertenece a un equipo
  cuya área es visible, o tiene ``area_id`` directo a un área visible, o
  tiene una participación activa en el proyecto.

Centralizar esto evita el drift entre los pickers de Plan / RAID /
Cambios / Lecciones / Minutas (antes cada endpoint reimplementaba la
cascada con heurísticas distintas, dejando recursos sin aparecer).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Actor, Area, AreaAssignment, Team
from app.models.project import Project


def _project_cascade_condition(project: Project):
    cond = or_(
        AreaAssignment.is_global.is_(True),
        AreaAssignment.project_id == str(project.id),
        AreaAssignment.organization_id == str(project.organization_id),
    )
    if project.program_id:
        cond = or_(cond, AreaAssignment.program_id == str(project.program_id))
    return cond


async def visible_area_ids(
    db: AsyncSession, tenant_id: UUID | str, project: Project
) -> list[str]:
    """IDs de áreas activas visibles para el proyecto (cascada)."""
    rows = (
        await db.execute(
            select(Area.id)
            .join(AreaAssignment, AreaAssignment.area_id == Area.id)
            .where(
                Area.tenant_id == str(tenant_id),
                Area.is_active.is_(True),
                _project_cascade_condition(project),
            )
            .distinct()
        )
    ).scalars().all()
    return [str(x) for x in rows]


async def actors_visible_to_project(
    db: AsyncSession, tenant_id: UUID | str, project: Project
) -> list[Actor]:
    """Actores asignables como responsables en el proyecto.

    Une (a) actores de equipos cuya área es visible, (b) actores con
    ``area_id`` directo a un área visible y (c) actores con participación
    activa en el proyecto. Excluye soft-deleted / inactivos.
    """
    from app.models.project_participation import ProjectParticipation

    area_ids = await visible_area_ids(db, tenant_id, project)

    team_ids: list[str] = []
    if area_ids:
        team_ids = [
            str(x)
            for x in (
                await db.execute(
                    select(Team.id).where(
                        Team.tenant_id == str(tenant_id),
                        Team.area_id.in_(area_ids),
                        Team.is_active.is_(True),
                    )
                )
            ).scalars().all()
        ]

    participating_actor_ids = [
        str(x)
        for x in (
            await db.execute(
                select(ProjectParticipation.actor_id).where(
                    ProjectParticipation.tenant_id == str(tenant_id),
                    ProjectParticipation.project_id == str(project.id),
                    ProjectParticipation.is_active.is_(True),
                )
            )
        ).scalars().all()
    ]

    conds = []
    if team_ids:
        conds.append(Actor.team_id.in_(team_ids))
    if area_ids:
        conds.append(Actor.area_id.in_(area_ids))
    if participating_actor_ids:
        conds.append(Actor.id.in_(participating_actor_ids))
    if not conds:
        return []

    rows = (
        await db.execute(
            select(Actor)
            .where(
                Actor.tenant_id == str(tenant_id),
                Actor.is_active.is_(True),
                Actor.deleted_at.is_(None),
                or_(*conds),
            )
            .order_by(Actor.name)
        )
    ).scalars().all()
    return list(rows)
