"""US-115 — endpoints del directorio de proyecto.

- /projects/{project_id}/participations — CRUD de la participación de
  Actores en un proyecto. `is_primary=true` único por (project, actor).
- /project-roles — CRUD del catálogo tenant editable.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import conflict, not_found
from app.db.session import get_db
from app.models.area import Actor
from app.models.project_participation import ProjectParticipation
from app.models.project_role import ProjectRole
from app.schemas.project_directory import (
    ActorMini,
    ParticipationCreate,
    ParticipationRead,
    ParticipationUpdate,
    ProjectRoleCreate,
    ProjectRoleRead,
    ProjectRoleUpdate,
)


def _tenant(cu: CurrentUser) -> UUID:
    return cu.effective_tenant_id


# =============================================================================
# /project-roles — catálogo tenant editable
# =============================================================================
roles_router = APIRouter(prefix="/project-roles", tags=["project-roles"])


@roles_router.get("", response_model=list[ProjectRoleRead])
async def list_project_roles(
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProjectRole).where(ProjectRole.tenant_id == str(_tenant(cu)))
    if is_active is not None:
        stmt = stmt.where(ProjectRole.is_active == is_active)
    rows = (await db.execute(stmt.order_by(ProjectRole.name))).scalars().all()
    return rows


@roles_router.post("", response_model=ProjectRoleRead, status_code=201)
async def create_project_role(
    body: ProjectRoleCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(
            select(ProjectRole).where(
                and_(
                    ProjectRole.tenant_id == str(_tenant(cu)),
                    ProjectRole.name == body.name,
                )
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise conflict("Project role with this name already exists")
    role = ProjectRole(
        tenant_id=str(_tenant(cu)),
        name=body.name,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@roles_router.patch("/{role_id}", response_model=ProjectRoleRead)
async def update_project_role(
    role_id: UUID,
    body: ProjectRoleUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    role = (
        await db.execute(
            select(ProjectRole).where(
                and_(
                    ProjectRole.tenant_id == str(_tenant(cu)),
                    ProjectRole.id == str(role_id),
                )
            )
        )
    ).scalar_one_or_none()
    if not role:
        raise not_found("Project role not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(role, k, v)
    await db.commit()
    await db.refresh(role)
    return role


@roles_router.delete("/{role_id}", status_code=204)
async def delete_project_role(
    role_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    role = (
        await db.execute(
            select(ProjectRole).where(
                and_(
                    ProjectRole.tenant_id == str(_tenant(cu)),
                    ProjectRole.id == str(role_id),
                )
            )
        )
    ).scalar_one_or_none()
    if not role:
        raise not_found("Project role not found")
    # Restrict si está en uso.
    in_use = (
        await db.execute(
            select(ProjectParticipation.id).where(
                ProjectParticipation.project_role_id == str(role_id)
            ).limit(1)
        )
    ).first()
    if in_use:
        raise conflict("Project role in use, cannot delete")
    await db.delete(role)
    await db.commit()


# =============================================================================
# /projects/{project_id}/participations
# =============================================================================
participations_router = APIRouter(
    prefix="/projects/{project_id}/participations", tags=["participations"]
)


def _hydrate(part: ProjectParticipation, actor: Actor | None) -> ParticipationRead:
    data = ParticipationRead.model_validate(part, from_attributes=True)
    if actor is not None:
        data.actor = ActorMini(
            id=actor.id,
            name=actor.name,
            email=actor.email,
            company=actor.company,
            job_title=actor.job_title,
        )
    return data


async def _ensure_unique_primary(
    db: AsyncSession,
    project_id: str,
    actor_id: str,
    keep_id: str | None = None,
) -> None:
    """Cuando is_primary=true se setea, desmarcar las demás del mismo (project, actor)."""
    stmt = update(ProjectParticipation).where(
        and_(
            ProjectParticipation.project_id == project_id,
            ProjectParticipation.actor_id == actor_id,
            ProjectParticipation.is_primary.is_(True),
        )
    )
    if keep_id is not None:
        stmt = stmt.where(ProjectParticipation.id != keep_id)
    stmt = stmt.values(is_primary=False)
    await db.execute(stmt)


@participations_router.get("", response_model=list[ParticipationRead])
async def list_participations(
    project_id: UUID,
    is_active: bool | None = Query(default=None),
    is_primary: bool | None = Query(default=None),
    include: str = Query(default="", description='"actor" para hidratar persona'),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProjectParticipation).where(
        and_(
            ProjectParticipation.tenant_id == str(_tenant(cu)),
            ProjectParticipation.project_id == str(project_id),
        )
    )
    if is_active is not None:
        stmt = stmt.where(ProjectParticipation.is_active == is_active)
    if is_primary is not None:
        stmt = stmt.where(ProjectParticipation.is_primary == is_primary)
    rows = (await db.execute(stmt)).scalars().all()
    if "actor" not in include:
        return [_hydrate(r, None) for r in rows]
    actor_ids = list({r.actor_id for r in rows})
    actors_by_id: dict[str, Actor] = {}
    if actor_ids:
        actors = (
            (await db.execute(select(Actor).where(Actor.id.in_(actor_ids))))
            .scalars()
            .all()
        )
        actors_by_id = {a.id: a for a in actors}
    return [_hydrate(r, actors_by_id.get(r.actor_id)) for r in rows]


@participations_router.post("", response_model=ParticipationRead, status_code=201)
async def create_participation(
    project_id: UUID,
    body: ParticipationCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # Validar actor pertenece al tenant.
    actor = (
        await db.execute(
            select(Actor).where(
                and_(
                    Actor.tenant_id == str(_tenant(cu)),
                    Actor.id == str(body.actor_id),
                )
            )
        )
    ).scalar_one_or_none()
    if not actor:
        raise not_found("Actor not found in tenant")

    part = ProjectParticipation(
        tenant_id=str(_tenant(cu)),
        project_id=str(project_id),
        actor_id=str(body.actor_id),
        operational_team_id=str(body.operational_team_id) if body.operational_team_id else None,
        project_role_id=str(body.project_role_id) if body.project_role_id else None,
        functional_area_id=(
            str(body.functional_area_id) if body.functional_area_id else actor.area_id
        ),
        is_area_lead=body.is_area_lead,
        is_primary=body.is_primary,
        start_date=body.start_date,
        end_date=body.end_date,
        is_active=body.is_active,
        created_by=str(cu.user.id),
    )
    db.add(part)
    await db.flush()
    if body.is_primary:
        await _ensure_unique_primary(
            db, str(project_id), str(body.actor_id), keep_id=part.id
        )
    await db.commit()
    await db.refresh(part)
    return _hydrate(part, actor)


@participations_router.patch("/{participation_id}", response_model=ParticipationRead)
async def update_participation(
    project_id: UUID,
    participation_id: UUID,
    body: ParticipationUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    part = (
        await db.execute(
            select(ProjectParticipation).where(
                and_(
                    ProjectParticipation.tenant_id == str(_tenant(cu)),
                    ProjectParticipation.project_id == str(project_id),
                    ProjectParticipation.id == str(participation_id),
                )
            )
        )
    ).scalar_one_or_none()
    if not part:
        raise not_found("Participation not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in {"operational_team_id", "project_role_id", "functional_area_id"}:
            setattr(part, k, str(v) if v else None)
        else:
            setattr(part, k, v)
    await db.flush()
    if data.get("is_primary") is True:
        await _ensure_unique_primary(
            db, str(project_id), part.actor_id, keep_id=part.id
        )
    await db.commit()
    await db.refresh(part)
    return _hydrate(part, None)


# =============================================================================
# /projects/{project_id}/eligible-actors — para dropdowns filtrados (US-117)
# =============================================================================
eligible_router = APIRouter(
    prefix="/projects/{project_id}/eligible-actors", tags=["participations"]
)


@eligible_router.get("", response_model=list[ActorMini])
async def list_eligible_actors(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Actores asignables como responsables/owners en el proyecto.

    BUG-086: une dos fuentes para que ningún recurso "asignado al proyecto"
    quede fuera de los dropdowns (plan, RAID, cambios, lecciones, minutas):
    1. Actores con participación activa (respeta la ventana temporal
       `start_date <= today <= end_date` cuando está definida).
    2. Actores visibles por la cascada de áreas del proyecto (catálogo):
       de equipos de áreas visibles o con `area_id` directo a un área
       visible. Antes, un recurso cargado a un área del proyecto sin
       participación no aparecía como asignable.
    """
    from datetime import date

    from app.models.project import Project
    from app.services.area_visibility import actors_visible_to_project

    tenant_id = _tenant(cu)
    today = date.today()
    seen: set[str] = set()
    out: list[ActorMini] = []

    def _push(actor: Actor) -> None:
        if actor.id in seen:
            return
        seen.add(actor.id)
        out.append(
            ActorMini(
                id=actor.id,
                name=actor.name,
                email=actor.email,
                company=actor.company,
                job_title=actor.job_title,
            )
        )

    # (1) participaciones activas con ventana temporal respetada.
    rows = (
        await db.execute(
            select(ProjectParticipation, Actor)
            .join(Actor, Actor.id == ProjectParticipation.actor_id)
            .where(
                and_(
                    ProjectParticipation.tenant_id == str(tenant_id),
                    ProjectParticipation.project_id == str(project_id),
                    ProjectParticipation.is_active.is_(True),
                    Actor.is_active.is_(True),
                )
            )
        )
    ).all()
    for part, actor in rows:
        if part.start_date and part.start_date > today:
            continue
        if part.end_date and part.end_date < today:
            continue
        _push(actor)

    # (2) actores visibles por la cascada de áreas del proyecto.
    project = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if project is not None:
        for actor in await actors_visible_to_project(db, tenant_id, project):
            _push(actor)

    out.sort(key=lambda a: (a.name or "").lower())
    return out


@participations_router.delete("/{participation_id}", status_code=204)
async def delete_participation(
    project_id: UUID,
    participation_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: marca is_active=False (mantiene historia para reportes)."""
    part = (
        await db.execute(
            select(ProjectParticipation).where(
                and_(
                    ProjectParticipation.tenant_id == str(_tenant(cu)),
                    ProjectParticipation.project_id == str(project_id),
                    ProjectParticipation.id == str(participation_id),
                )
            )
        )
    ).scalar_one_or_none()
    if not part:
        raise not_found("Participation not found")
    part.is_active = False
    part.is_primary = False
    await db.commit()
