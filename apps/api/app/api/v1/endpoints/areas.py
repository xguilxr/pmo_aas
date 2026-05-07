"""Áreas → Equipos → Actores (catálogo tenant) CRUD — US-097.

Tres recursos paralelos bajo el mismo router para mantener la
jerarquía cohesiva. RLS enforced via `tenant_id == cu.user.tenant_id`
en cada query.
"""
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import not_found, validation_error
from app.db.session import get_db
from app.models.area import Actor, Area, Team
from app.schemas.area import (
    ActorCreate,
    ActorRead,
    ActorReassignBody,
    ActorReassignResponse,
    ActorUpdate,
    AreaCreate,
    AreaRead,
    AreaTreeResponse,
    AreaUpdate,
    TeamCreate,
    TeamRead,
    TeamUpdate,
    TreeActor,
    TreeArea,
    TreeTeam,
)


def _tenant(cu: CurrentUser) -> UUID:
    return cu.user.tenant_id


# =============================================================================
# /areas — top-level
# =============================================================================
areas_router = APIRouter(prefix="/areas", tags=["areas"])


@areas_router.get("", response_model=list[AreaRead])
async def list_areas(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Area).where(Area.tenant_id == str(tenant_id))
    if is_active is not None:
        stmt = stmt.where(Area.is_active == is_active)
    if q:
        stmt = stmt.where(func.lower(Area.name).like(f"%{q.lower()}%"))
    rows = (await db.execute(stmt.order_by(Area.name))).scalars().all()
    return [AreaRead.model_validate(r) for r in rows]


@areas_router.post("", response_model=AreaRead, status_code=201)
async def create_area(
    body: AreaCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    a = Area(
        tenant_id=str(tenant_id),
        name=body.name.strip(),
        description=body.description,
        lead_name=body.lead_name.strip() if body.lead_name else None,
        is_active=body.is_active,
        created_by=str(cu.id),
    )
    db.add(a)
    await db.commit()
    return AreaRead.model_validate(a)


@areas_router.get("/tree", response_model=AreaTreeResponse)
async def get_areas_tree(
    include_inactive: bool = Query(default=False),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Árbol completo del catálogo: Áreas → Equipos → Actores.

    Optimizado en 3 queries. `unassigned_actors` por área queda vacío
    (los actores se asocian sólo vía team). `orphan_actors` lista los
    actores sin team asignado (post bulk-move o recién creados).
    """
    tenant_id = _tenant(cu)

    areas_q = select(Area).where(Area.tenant_id == str(tenant_id))
    teams_q = select(Team).where(Team.tenant_id == str(tenant_id))
    actors_q = select(Actor).where(
        Actor.tenant_id == str(tenant_id), Actor.deleted_at.is_(None)
    )
    if not include_inactive:
        areas_q = areas_q.where(Area.is_active.is_(True))
        teams_q = teams_q.where(Team.is_active.is_(True))
        actors_q = actors_q.where(Actor.is_active.is_(True))

    areas = (await db.execute(areas_q.order_by(Area.name))).scalars().all()
    teams = (await db.execute(teams_q.order_by(Team.name))).scalars().all()
    actors = (await db.execute(actors_q.order_by(Actor.name))).scalars().all()

    teams_by_area: dict[str, list[Team]] = defaultdict(list)
    for t in teams:
        teams_by_area[str(t.area_id)].append(t)

    actors_by_team: dict[str, list[Actor]] = defaultdict(list)
    orphans: list[Actor] = []
    for a in actors:
        if a.team_id:
            actors_by_team[str(a.team_id)].append(a)
        else:
            orphans.append(a)

    return AreaTreeResponse(
        areas=[
            TreeArea(
                id=area.id,
                name=area.name,
                description=area.description,
                lead_name=area.lead_name,
                is_active=area.is_active,
                teams=[
                    TreeTeam(
                        id=t.id,
                        name=t.name,
                        description=t.description,
                        is_active=t.is_active,
                        actors=[TreeActor.model_validate(x) for x in actors_by_team.get(str(t.id), [])],
                    )
                    for t in teams_by_area.get(str(area.id), [])
                ],
                unassigned_actors=[],
            )
            for area in areas
        ],
        orphan_actors=[TreeActor.model_validate(o) for o in orphans],
    )


@areas_router.get("/{area_id}", response_model=AreaRead)
async def get_area(
    area_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    a = (
        await db.execute(
            select(Area).where(Area.id == str(area_id), Area.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Área")
    return AreaRead.model_validate(a)


@areas_router.patch("/{area_id}", response_model=AreaRead)
async def update_area(
    area_id: UUID,
    body: AreaUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    a = (
        await db.execute(
            select(Area).where(Area.id == str(area_id), Area.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Área")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(a, k, v)
    await db.commit()
    return AreaRead.model_validate(a)


@areas_router.delete("/{area_id}", status_code=204)
async def delete_area(
    area_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Borra Área en cascada (Teams se borran via FK CASCADE; Actores
    quedan sin team via FK SET NULL → aparecen en `orphan_actors`).
    """
    tenant_id = _tenant(cu)
    a = (
        await db.execute(
            select(Area).where(Area.id == str(area_id), Area.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Área")
    await db.delete(a)
    await db.commit()


# =============================================================================
# /teams
# =============================================================================
teams_router = APIRouter(prefix="/teams", tags=["teams"])


@teams_router.get("", response_model=list[TeamRead])
async def list_teams(
    area_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Team).where(Team.tenant_id == str(tenant_id))
    if area_id is not None:
        stmt = stmt.where(Team.area_id == str(area_id))
    if is_active is not None:
        stmt = stmt.where(Team.is_active == is_active)
    if q:
        stmt = stmt.where(func.lower(Team.name).like(f"%{q.lower()}%"))
    rows = (await db.execute(stmt.order_by(Team.name))).scalars().all()
    return [TeamRead.model_validate(r) for r in rows]


@teams_router.post("", response_model=TeamRead, status_code=201)
async def create_team(
    body: TeamCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    parent = (
        await db.execute(
            select(Area).where(
                Area.id == str(body.area_id), Area.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if parent is None:
        raise validation_error("area_id no existe en el tenant")
    t = Team(
        tenant_id=str(tenant_id),
        area_id=str(body.area_id),
        name=body.name.strip(),
        description=body.description,
        is_active=body.is_active,
        created_by=str(cu.id),
    )
    db.add(t)
    await db.commit()
    return TeamRead.model_validate(t)


@teams_router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(
            select(Team).where(Team.id == str(team_id), Team.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Equipo")
    return TeamRead.model_validate(t)


@teams_router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: UUID,
    body: TeamUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(
            select(Team).where(Team.id == str(team_id), Team.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Equipo")
    data = body.model_dump(exclude_none=True)
    if "area_id" in data:
        new_area = (
            await db.execute(
                select(Area).where(
                    Area.id == str(data["area_id"]), Area.tenant_id == str(tenant_id)
                )
            )
        ).scalar_one_or_none()
        if new_area is None:
            raise validation_error("area_id no existe en el tenant")
        data["area_id"] = str(data["area_id"])
    for k, v in data.items():
        setattr(t, k, v)
    await db.commit()
    return TeamRead.model_validate(t)


@teams_router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    t = (
        await db.execute(
            select(Team).where(Team.id == str(team_id), Team.tenant_id == str(tenant_id))
        )
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Equipo")
    await db.delete(t)
    await db.commit()


# =============================================================================
# /actors
# =============================================================================
actors_router = APIRouter(prefix="/actors", tags=["actors"])


@actors_router.get("", response_model=list[ActorRead])
async def list_actors(
    team_id: UUID | None = Query(default=None),
    area_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Actor).where(
        Actor.tenant_id == str(tenant_id), Actor.deleted_at.is_(None)
    )
    if team_id is not None:
        stmt = stmt.where(Actor.team_id == str(team_id))
    if area_id is not None:
        # actor.team.area_id; via subquery
        team_ids = (
            await db.execute(
                select(Team.id).where(
                    Team.area_id == str(area_id), Team.tenant_id == str(tenant_id)
                )
            )
        ).scalars().all()
        stmt = stmt.where(Actor.team_id.in_([str(x) for x in team_ids]))
    if is_active is not None:
        stmt = stmt.where(Actor.is_active == is_active)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Actor.name).like(like) | func.lower(Actor.email).like(like)
        )
    rows = (
        await db.execute(
            stmt.order_by(Actor.name).offset((page - 1) * limit).limit(limit)
        )
    ).scalars().all()
    return [ActorRead.model_validate(r) for r in rows]


@actors_router.post("", response_model=ActorRead, status_code=201)
async def create_actor(
    body: ActorCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    if body.team_id is not None:
        parent_team = (
            await db.execute(
                select(Team).where(
                    Team.id == str(body.team_id), Team.tenant_id == str(tenant_id)
                )
            )
        ).scalar_one_or_none()
        if parent_team is None:
            raise validation_error("team_id no existe en el tenant")
    a = Actor(
        tenant_id=str(tenant_id),
        team_id=str(body.team_id) if body.team_id else None,
        user_id=str(body.user_id) if body.user_id else None,
        name=body.name.strip(),
        email=str(body.email) if body.email else None,
        phone=body.phone,
        is_active=body.is_active,
        created_by=str(cu.id),
    )
    db.add(a)
    await db.commit()
    return ActorRead.model_validate(a)


@actors_router.get("/{actor_id}", response_model=ActorRead)
async def get_actor(
    actor_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    a = (
        await db.execute(
            select(Actor).where(
                Actor.id == str(actor_id),
                Actor.tenant_id == str(tenant_id),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Actor")
    return ActorRead.model_validate(a)


@actors_router.patch("/{actor_id}", response_model=ActorRead)
async def update_actor(
    actor_id: UUID,
    body: ActorUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    a = (
        await db.execute(
            select(Actor).where(
                Actor.id == str(actor_id),
                Actor.tenant_id == str(tenant_id),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Actor")
    data_full = body.model_dump(exclude_unset=True)
    if "team_id" in data_full:
        new_team_id = data_full["team_id"]
        if new_team_id is not None:
            parent_team = (
                await db.execute(
                    select(Team).where(
                        Team.id == str(new_team_id), Team.tenant_id == str(tenant_id)
                    )
                )
            ).scalar_one_or_none()
            if parent_team is None:
                raise validation_error("team_id no existe en el tenant")
            a.team_id = str(new_team_id)
        else:
            a.team_id = None
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        if k == "team_id":
            continue
        if k in ("user_id", "email") and v is not None:
            v = str(v)
        setattr(a, k, v)
    await db.commit()
    return ActorRead.model_validate(a)


@actors_router.post(
    "/{actor_id}/reassign", response_model=ActorReassignResponse
)
async def reassign_actor(
    actor_id: UUID,
    body: ActorReassignBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-099 — bulk-move tareas (y opcionalmente RAID / minutas) de un
    actor a otro. Operación atómica: si algo falla se hace rollback.

    El vínculo actor→tareas es vía `actor.user_id` (las tareas
    referencian `users.id` en `tasks.owner_id`). Si el actor origen
    no tiene `user_id`, no hay nada que mover (devuelve 0 / 0 / 0).

    MVP: scope='tasks' única; RAID y minutas quedan diferidos hasta
    que el owner valide el modelo final de actores en esos módulos.
    """
    from sqlalchemy import update as sa_update

    from app.models.task import Task as TaskModel
    from app.services.audit import write_audit

    tenant_id = _tenant(cu)
    src = (
        await db.execute(
            select(Actor).where(
                Actor.id == str(actor_id),
                Actor.tenant_id == str(tenant_id),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if src is None:
        raise not_found("Actor")
    tgt = (
        await db.execute(
            select(Actor).where(
                Actor.id == str(body.target_actor_id),
                Actor.tenant_id == str(tenant_id),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if tgt is None:
        raise validation_error("target_actor_id no existe en el tenant")
    if str(tgt.id) == str(src.id):
        raise validation_error("target_actor_id debe ser distinto del actor origen")

    tasks_moved = 0
    if "tasks" in body.scopes:
        if src.user_id is not None and tgt.user_id is not None:
            res = await db.execute(
                sa_update(TaskModel)
                .where(
                    TaskModel.tenant_id == str(tenant_id),
                    TaskModel.owner_id == str(src.user_id),
                )
                .values(owner_id=str(tgt.user_id))
            )
            tasks_moved = res.rowcount or 0

    if body.deactivate_source:
        from datetime import UTC
        from datetime import datetime as _dt
        src.is_active = False
        src.deleted_at = _dt.now(UTC)

    await write_audit(
        db,
        action="actor.reassign",
        module="actors",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="actor",
        entity_id=str(src.id),
        details={
            "target_actor_id": str(tgt.id),
            "tasks_moved": tasks_moved,
            "deactivated": body.deactivate_source,
        },
    )
    await db.commit()
    return ActorReassignResponse(
        tasks_moved=tasks_moved,
        raid_moved=0,
        minutes_moved=0,
        source_deactivated=body.deactivate_source,
    )


@actors_router.delete("/{actor_id}", status_code=204)
async def delete_actor(
    actor_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete del actor (marca `deleted_at` + `is_active=False`)."""
    from datetime import UTC, datetime

    tenant_id = _tenant(cu)
    a = (
        await db.execute(
            select(Actor).where(
                Actor.id == str(actor_id),
                Actor.tenant_id == str(tenant_id),
                Actor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise not_found("Actor")
    a.deleted_at = datetime.now(UTC)
    a.is_active = False
    await db.commit()
