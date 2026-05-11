"""US-115 — helper para enriquecer responses con dimensiones derivadas.

Dado un actor + proyecto, resuelve la "primary participation" y devuelve
los IDs de área funcional / equipo operativo / rol proyecto y el flag
is_area_lead. Reutilizado por tasks, risks, issues responses.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Actor
from app.models.project_participation import ProjectParticipation


@dataclass
class DerivedAssignment:
    functional_area_id: str | None
    operational_team_id: str | None
    project_role_id: str | None
    is_area_lead: bool

    def to_dict(self) -> dict:
        return {
            "functional_area_id": self.functional_area_id,
            "operational_team_id": self.operational_team_id,
            "project_role_id": self.project_role_id,
            "is_area_lead": self.is_area_lead,
        }


EMPTY = DerivedAssignment(None, None, None, False)


async def derived_for_actor(
    db: AsyncSession,
    actor_id: str | UUID | None,
    project_id: str | UUID | None,
) -> DerivedAssignment:
    """Devuelve dimensiones para (actor, project). Sin participation o
    sin actor → todos None excepto que el actor tenga functional_area
    legacy (`actors.area_id`) — entonces se devuelve eso como fallback."""
    if not actor_id or not project_id:
        return EMPTY
    aid, pid = str(actor_id), str(project_id)
    # Primary primero; si no hay primary, la primera activa.
    rows = (
        await db.execute(
            select(ProjectParticipation)
            .where(
                and_(
                    ProjectParticipation.actor_id == aid,
                    ProjectParticipation.project_id == pid,
                )
            )
            .order_by(
                ProjectParticipation.is_primary.desc(),
                ProjectParticipation.is_active.desc(),
                ProjectParticipation.created_at.desc(),
            )
            .limit(1)
        )
    ).scalars().all()
    if rows:
        p = rows[0]
        return DerivedAssignment(
            functional_area_id=p.functional_area_id,
            operational_team_id=p.operational_team_id,
            project_role_id=p.project_role_id,
            is_area_lead=p.is_area_lead,
        )
    # Fallback: actor.area_id legacy.
    actor = (
        await db.execute(select(Actor).where(Actor.id == aid))
    ).scalar_one_or_none()
    if actor and actor.area_id:
        return DerivedAssignment(
            functional_area_id=actor.area_id,
            operational_team_id=actor.team_id,
            project_role_id=None,
            is_area_lead=actor.is_lead,
        )
    return EMPTY


async def derived_bulk(
    db: AsyncSession,
    pairs: list[tuple[str | None, str | None]],
) -> dict[tuple[str, str], DerivedAssignment]:
    """Versión bulk para listas de tareas: 1 query por proyecto."""
    if not pairs:
        return {}
    by_project: dict[str, set[str]] = {}
    for actor_id, project_id in pairs:
        if not actor_id or not project_id:
            continue
        by_project.setdefault(str(project_id), set()).add(str(actor_id))
    result: dict[tuple[str, str], DerivedAssignment] = {}
    for pid, actor_ids in by_project.items():
        rows = (
            await db.execute(
                select(ProjectParticipation)
                .where(
                    and_(
                        ProjectParticipation.project_id == pid,
                        ProjectParticipation.actor_id.in_(actor_ids),
                    )
                )
                .order_by(
                    ProjectParticipation.is_primary.desc(),
                    ProjectParticipation.is_active.desc(),
                    ProjectParticipation.created_at.desc(),
                )
            )
        ).scalars().all()
        seen: set[str] = set()
        for p in rows:
            if p.actor_id in seen:
                continue
            seen.add(p.actor_id)
            result[(p.actor_id, pid)] = DerivedAssignment(
                functional_area_id=p.functional_area_id,
                operational_team_id=p.operational_team_id,
                project_role_id=p.project_role_id,
                is_area_lead=p.is_area_lead,
            )
    return result
