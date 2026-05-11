"""US-118 — Fase 1: doble escritura project_members ↔ project_participations.

Durante la transición del modelo legacy `project_members` (user↔project,
role_in_project string) al nuevo `project_participations` (actor↔project,
project_role_id FK + dimensiones), las mutaciones en members deben
propagarse a participations para mantener una única fuente de verdad
hacia adelante (RBAC y filtros "mis proyectos" migran en Fase 2).

Uso (en endpoints que crean/borran ProjectMember):

    from app.services.project_membership_sync import sync_member_to_participation
    db.add(ProjectMember(project_id=p.id, user_id=u.id, role_in_project="pm"))
    await db.flush()
    await sync_member_to_participation(db, tenant_id, p.id, u.id, "pm")

Notas:
- Si no existe Actor para el user_id, se crea uno con `name=user.full_name`.
- Si no existe ProjectRole con el name correspondiente, se elige None
  (el endpoint puede haber poblado el catálogo seed via Alembic 0061).
- La función es idempotente: si ya hay participation activa para
  (project, actor) no duplica filas, solo actualiza el role.

NO toca lecturas — RBAC sigue leyendo project_members hasta Fase 2.
"""
from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Actor
from app.models.project_participation import ProjectParticipation
from app.models.project_role import ProjectRole
from app.models.user import User

_ROLE_LABEL_MAP = {
    "pm": "PM",
    "sponsor": "Sponsor",
    "sme": "SME",
    "key_user": "Key User",
    "tech_lead": "Tech Lead",
    "team": "Member",
}


async def _ensure_actor_for_user(
    db: AsyncSession, tenant_id: str, user_id: str
) -> Actor | None:
    actor = (
        await db.execute(
            select(Actor).where(
                and_(Actor.tenant_id == tenant_id, Actor.user_id == user_id)
            )
        )
    ).scalar_one_or_none()
    if actor:
        return actor
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        return None
    actor = Actor(
        tenant_id=tenant_id,
        user_id=user_id,
        name=getattr(user, "full_name", None) or getattr(user, "email", "Usuario"),
        email=getattr(user, "email", None),
        is_active=True,
    )
    db.add(actor)
    await db.flush()
    return actor


async def _resolve_role_id(
    db: AsyncSession, tenant_id: str, role_label: str | None
) -> str | None:
    target = _ROLE_LABEL_MAP.get((role_label or "team").lower(), "Member")
    role = (
        await db.execute(
            select(ProjectRole).where(
                and_(
                    ProjectRole.tenant_id == tenant_id,
                    ProjectRole.name == target,
                )
            )
        )
    ).scalar_one_or_none()
    return role.id if role else None


async def sync_member_to_participation(
    db: AsyncSession,
    tenant_id: str,
    project_id: str,
    user_id: str,
    role_label: str | None,
) -> ProjectParticipation | None:
    """Garantiza una participation activa para (project, user→actor) y
    actualiza su project_role_id según role_label."""
    actor = await _ensure_actor_for_user(db, tenant_id, user_id)
    if actor is None:
        return None
    role_id = await _resolve_role_id(db, tenant_id, role_label)

    existing = (
        await db.execute(
            select(ProjectParticipation).where(
                and_(
                    ProjectParticipation.project_id == project_id,
                    ProjectParticipation.actor_id == actor.id,
                )
            )
        )
    ).scalars().all()
    if existing:
        # Idempotente: actualizar la primera, no duplicar.
        target = next((p for p in existing if p.is_primary), existing[0])
        target.project_role_id = role_id
        target.is_active = True
        await db.flush()
        return target
    part = ProjectParticipation(
        tenant_id=tenant_id,
        project_id=project_id,
        actor_id=actor.id,
        project_role_id=role_id,
        functional_area_id=actor.area_id,
        is_primary=True,
        is_active=True,
    )
    db.add(part)
    await db.flush()
    return part


async def sync_member_removal(
    db: AsyncSession, project_id: str, user_id: str
) -> None:
    """Cuando un project_member se elimina, marcar la participation como
    inactiva (soft-delete coherente con DELETE de participation)."""
    actor = (
        await db.execute(
            select(Actor).where(Actor.user_id == user_id)
        )
    ).scalar_one_or_none()
    if not actor:
        return
    rows = (
        await db.execute(
            select(ProjectParticipation).where(
                and_(
                    ProjectParticipation.project_id == project_id,
                    ProjectParticipation.actor_id == actor.id,
                )
            )
        )
    ).scalars().all()
    for p in rows:
        p.is_active = False
        p.is_primary = False
    await db.flush()
