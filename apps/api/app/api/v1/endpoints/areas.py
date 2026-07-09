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
from app.core.errors import conflict, not_found, validation_error
from app.db.session import get_db
from app.models.area import Actor, Area, AreaAssignment, Team
from app.schemas.area import (
    ActorCreate,
    ActorRead,
    ActorReassignBody,
    ActorReassignResponse,
    ActorUpdate,
    AreaAssignmentRead,
    AreaAssignmentSetBody,
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
    return cu.effective_tenant_id


async def _ensure_area_assignment_for_scope(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    area_id: str,
    scope: tuple[str, str] | None,
    created_by: str | None,
) -> None:
    """BUG-085: garantiza que el área tenga un AreaAssignment para el scope
    desde el que se creó (proyecto / programa / organización). Idempotente:
    no duplica si ya existe una asignación equivalente. La cascada de lectura
    (`list_areas_by_project`) se encarga de propagar hacia los hijos.
    """
    if scope is None:
        return
    kind, target = scope
    col = {
        "project": AreaAssignment.project_id,
        "program": AreaAssignment.program_id,
        "organization": AreaAssignment.organization_id,
    }[kind]
    existing = (
        await db.execute(
            select(AreaAssignment.id).where(
                AreaAssignment.tenant_id == str(tenant_id),
                AreaAssignment.area_id == area_id,
                col == target,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(
        AreaAssignment(
            tenant_id=str(tenant_id),
            area_id=area_id,
            organization_id=target if kind == "organization" else None,
            program_id=target if kind == "program" else None,
            project_id=target if kind == "project" else None,
            is_global=False,
            created_by=created_by,
        )
    )


# =============================================================================
# /areas — top-level
# =============================================================================
areas_router = APIRouter(prefix="/areas", tags=["areas"])


@areas_router.get("", response_model=list[AreaRead])
async def list_areas(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    include_global: bool = Query(default=True),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """BUG-061: cuando `organization_id` se pasa, devuelve áreas de esa
    organización + (si `include_global=true`) las tenant-globales. Sin
    `organization_id` se devuelven todas las del tenant."""
    tenant_id = _tenant(cu)
    stmt = select(Area).where(Area.tenant_id == str(tenant_id))
    if is_active is not None:
        stmt = stmt.where(Area.is_active == is_active)
    if q:
        stmt = stmt.where(func.lower(Area.name).like(f"%{q.lower()}%"))
    if organization_id is not None:
        if include_global:
            stmt = stmt.where(
                (Area.organization_id == str(organization_id))
                | (Area.organization_id.is_(None))
            )
        else:
            stmt = stmt.where(Area.organization_id == str(organization_id))
    rows = (await db.execute(stmt.order_by(Area.name))).scalars().all()
    return [AreaRead.model_validate(r) for r in rows]


@areas_router.post("", response_model=AreaRead, status_code=201)
async def create_area(
    body: AreaCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-078: si `body.lead` viene, crea/reusa el Actor líder primero
    y enlaza vía `lead_actor_id`. Decisión owner: el líder se persiste
    como Actor con `is_lead=true` antes de crear el área.
    """
    tenant_id = _tenant(cu)
    name = body.name.strip()
    org_id = str(body.organization_id) if body.organization_id else None

    # BUG-085: scope de creación. Si el área se crea desde un proyecto o
    # programa, derivamos la organización del padre y recordamos el scope
    # para crear el AreaAssignment correcto al final (propagación):
    #   - project_id → assignment al proyecto (queda en ese proyecto).
    #   - program_id → assignment al programa (se propaga a sus proyectos).
    #   - organization_id → assignment a la org (se propaga a programas/proyectos).
    # Esto resuelve "no hay organization_id" al crear área dentro de un
    # proyecto: dentro de un proyecto el org_id es el del proyecto.
    from app.models.organization import Organization, Program
    from app.models.project import Project

    scope: tuple[str, str] | None = None  # (kind, id) → org/program/project
    if body.project_id is not None:
        project = (
            await db.execute(
                select(Project).where(
                    Project.id == str(body.project_id),
                    Project.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if project is None:
            raise validation_error("project_id no existe en el tenant")
        org_id = str(project.organization_id)
        scope = ("project", str(body.project_id))
    elif body.program_id is not None:
        program = (
            await db.execute(
                select(Program).where(
                    Program.id == str(body.program_id),
                    Program.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if program is None:
            raise validation_error("program_id no existe en el tenant")
        org_id = str(program.organization_id)
        scope = ("program", str(body.program_id))
    elif org_id is not None:
        scope = ("organization", org_id)

    # US-170: nuevas áreas deben pertenecer a una organización (no globales).
    if org_id is None:
        raise validation_error(
            "Se requiere un alcance para crear un área "
            "(project_id, program_id u organization_id)"
        )

    # BUG-061: validar que la org pertenece al tenant.
    org_ok = (
        await db.execute(
            select(Organization.id).where(
                Organization.id == org_id,
                Organization.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if org_ok is None:
        raise validation_error("organization_id no existe en el tenant")

    # BUG-060/061: pre-check del unique scoped al mismo organization_id
    # (NULL == NULL para esta lógica). Si existe inactivo → reactivar;
    # si existe activo → 409 limpio.
    name_clash = func.lower(Area.name) == name.lower()
    if org_id is None:
        scope_clause = Area.organization_id.is_(None)
    else:
        scope_clause = Area.organization_id == org_id
    existing_area = (
        await db.execute(
            select(Area).where(
                Area.tenant_id == str(tenant_id),
                scope_clause,
                name_clash,
            )
        )
    ).scalar_one_or_none()
    if existing_area is not None:
        if not existing_area.is_active:
            existing_area.is_active = True
            existing_area.description = body.description or existing_area.description
            # BUG-085: al reactivar, garantiza la asignación al scope actual.
            await _ensure_area_assignment_for_scope(
                db, tenant_id=tenant_id, area_id=str(existing_area.id),
                scope=scope, created_by=str(cu.id),
            )
            await db.commit()
            await db.refresh(existing_area)
            return AreaRead.model_validate(existing_area)
        raise conflict(
            "Ya existe un área con ese nombre en este alcance "
            "(misma organización o entre globales)",
            code="AREA_NAME_DUPLICATE",
            fields={"existing_area_id": str(existing_area.id)},
        )

    a = Area(
        tenant_id=str(tenant_id),
        organization_id=org_id,
        name=name,
        description=body.description,
        is_active=body.is_active,
        created_by=str(cu.id),
    )
    db.add(a)
    await db.flush()  # obtain a.id

    # BUG-085: crea el AreaAssignment del scope de creación (proyecto /
    # programa / organización) para que el área quede visible y propague.
    await _ensure_area_assignment_for_scope(
        db, tenant_id=tenant_id, area_id=str(a.id),
        scope=scope, created_by=str(cu.id),
    )

    if body.lead is not None:
        lead_actor: Actor | None = None
        if body.lead.actor_id is not None:
            lead_actor = (
                await db.execute(
                    select(Actor).where(
                        Actor.id == str(body.lead.actor_id),
                        Actor.tenant_id == str(tenant_id),
                    )
                )
            ).scalar_one_or_none()
            if lead_actor is None:
                raise not_found("Lead actor")
            lead_actor.is_lead = True
        elif body.lead.name:
            lead_actor = Actor(
                tenant_id=str(tenant_id),
                team_id=None,
                user_id=None,
                name=body.lead.name.strip(),
                email=body.lead.email,
                phone=body.lead.phone,
                is_active=True,
                is_lead=True,
                created_by=str(cu.id),
            )
            db.add(lead_actor)
            await db.flush()
        if lead_actor is not None:
            a.lead_actor_id = lead_actor.id
    await db.commit()
    await db.refresh(a)
    return AreaRead.model_validate(a)


@areas_router.get("/tree", response_model=AreaTreeResponse)
async def get_areas_tree(
    include_inactive: bool = Query(default=False),
    organization_id: UUID | None = Query(default=None),
    include_global: bool = Query(default=True),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Árbol completo del catálogo: Áreas → Equipos → Actores.

    Optimizado en 3 queries. `unassigned_actors` por área queda vacío
    (los actores se asocian sólo vía team). `orphan_actors` lista los
    actores sin team asignado (post bulk-move o recién creados).

    BUG-061: si `organization_id` se pasa, filtra a las áreas de esa
    org (más las globales si `include_global=true`).
    """
    tenant_id = _tenant(cu)

    areas_q = select(Area).where(Area.tenant_id == str(tenant_id))
    if organization_id is not None:
        if include_global:
            areas_q = areas_q.where(
                (Area.organization_id == str(organization_id))
                | (Area.organization_id.is_(None))
            )
        else:
            areas_q = areas_q.where(Area.organization_id == str(organization_id))
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
    actors_by_area_no_team: dict[str, list[Actor]] = defaultdict(list)
    orphans: list[Actor] = []
    pmo_area = next((a for a in areas if a.name == "PMO"), None)
    for a in actors:
        if a.team_id:
            actors_by_team[str(a.team_id)].append(a)
            continue
        # ENH-084 rework: actor sin team con `area_id` directo va a
        # `unassigned_actors` de esa área.
        if a.area_id:
            actors_by_area_no_team[str(a.area_id)].append(a)
            continue
        # ENH-082: actor sincronizado desde user (PMO seed) sin team
        # ni area_id explícito → cae en PMO si existe.
        if pmo_area is not None and a.user_id is not None:
            actors_by_area_no_team[str(pmo_area.id)].append(a)
            continue
        orphans.append(a)
    other_orphans = orphans

    return AreaTreeResponse(
        areas=[
            TreeArea(
                id=area.id,
                organization_id=area.organization_id,
                name=area.name,
                description=area.description,
                lead_actor_id=area.lead_actor_id,
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
                unassigned_actors=[
                    TreeActor.model_validate(x)
                    for x in actors_by_area_no_team.get(str(area.id), [])
                ],
            )
            for area in areas
        ],
        orphan_actors=[TreeActor.model_validate(o) for o in other_orphans],
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
    # BUG-061: organization_id puede venir explícitamente null (mover a
    # global) — usar exclude_unset para distinguir "no enviar" de
    # "enviar null". El resto de campos sigue con exclude_none.
    payload = body.model_dump(exclude_unset=True)
    data = {k: v for k, v in payload.items() if v is not None or k == "organization_id"}

    # BUG-061: validar nueva org si vino set (no None).
    if data.get("organization_id") is not None:
        from app.models.organization import Organization

        org_ok = (
            await db.execute(
                select(Organization.id).where(
                    Organization.id == str(data["organization_id"]),
                    Organization.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if org_ok is None:
            raise validation_error("organization_id no existe en el tenant")
        data["organization_id"] = str(data["organization_id"])

    # BUG-060/061: rename / move-org con colisión devuelve 409 estructurado.
    name_changing = "name" in data
    org_changing = "organization_id" in data
    if name_changing or org_changing:
        new_name = data["name"].strip() if name_changing else a.name
        new_org = data["organization_id"] if org_changing else a.organization_id
        scope_clause = (
            Area.organization_id.is_(None)
            if new_org is None
            else Area.organization_id == new_org
        )
        clash = (
            await db.execute(
                select(Area).where(
                    Area.tenant_id == str(tenant_id),
                    Area.id != str(area_id),
                    scope_clause,
                    func.lower(Area.name) == new_name.lower(),
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise conflict(
                "Ya existe un área con ese nombre en este alcance",
                code="AREA_NAME_DUPLICATE",
                fields={"existing_area_id": str(clash.id)},
            )
        if name_changing:
            data["name"] = new_name
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
    name = body.name.strip()
    # BUG-060: pre-check del unique (tenant_id, area_id, name).
    existing_team = (
        await db.execute(
            select(Team).where(
                Team.tenant_id == str(tenant_id),
                Team.area_id == str(body.area_id),
                func.lower(Team.name) == name.lower(),
            )
        )
    ).scalar_one_or_none()
    if existing_team is not None:
        if not existing_team.is_active:
            existing_team.is_active = True
            existing_team.description = body.description or existing_team.description
            await db.commit()
            await db.refresh(existing_team)
            return TeamRead.model_validate(existing_team)
        raise conflict(
            "Ya existe un equipo con ese nombre en esta área",
            code="TEAM_NAME_DUPLICATE",
            fields={"existing_team_id": str(existing_team.id)},
        )
    t = Team(
        tenant_id=str(tenant_id),
        area_id=str(body.area_id),
        name=name,
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
    # BUG-060: rename / re-assign con colisión devuelve 409 en vez de 500.
    target_area_id = data.get("area_id", t.area_id)
    target_name = data["name"].strip() if "name" in data else t.name
    if "name" in data or "area_id" in data:
        clash = (
            await db.execute(
                select(Team).where(
                    Team.tenant_id == str(tenant_id),
                    Team.area_id == str(target_area_id),
                    Team.id != str(team_id),
                    func.lower(Team.name) == target_name.lower(),
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise conflict(
                "Ya existe un equipo con ese nombre en esta área",
                code="TEAM_NAME_DUPLICATE",
                fields={"existing_team_id": str(clash.id)},
            )
    if "name" in data:
        data["name"] = target_name
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
    # US-182: filtros del pool de recursos.
    resource_type: str | None = Query(default=None),
    portfolio_function: str | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Actor).where(
        Actor.tenant_id == str(tenant_id), Actor.deleted_at.is_(None)
    )
    if resource_type is not None:
        stmt = stmt.where(Actor.resource_type == resource_type)
    if portfolio_function is not None:
        stmt = stmt.where(Actor.portfolio_function == portfolio_function)
    if organization_id is not None:
        stmt = stmt.where(Actor.organization_id == str(organization_id))
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

    # BUG-059: el unique (tenant_id, email) hacía que un POST con un
    # email ya registrado tirara 500. Para flujos de "carga de recursos
    # a áreas" reusamos el actor existente: si está soft-deleted lo
    # revivimos con los nuevos datos; si está activo devolvemos 409 con
    # `existing_actor_id` para que el frontend ofrezca asignar al
    # existente en vez de duplicar.
    if body.email:
        normalized_email = str(body.email).strip().lower()
        existing = (
            await db.execute(
                select(Actor).where(
                    Actor.tenant_id == str(tenant_id),
                    func.lower(Actor.email) == normalized_email,
                )
            )
        ).scalars().first()
        if existing is not None:
            if existing.deleted_at is not None:
                existing.deleted_at = None
                existing.team_id = (
                    str(body.team_id) if body.team_id else existing.team_id
                )
                existing.area_id = (
                    str(body.area_id) if body.area_id else existing.area_id
                )
                existing.user_id = (
                    str(body.user_id) if body.user_id else existing.user_id
                )
                existing.name = body.name.strip()
                existing.phone = body.phone
                existing.is_active = body.is_active
                existing.is_lead = body.is_lead
                # BUG-072: el revive también debe actualizar los campos
                # de enriquecimiento US-114 si vienen en el body, igual
                # que la creación. Antes se quedaban con el valor viejo
                # (o null) de la entidad soft-deleted.
                if body.company is not None:
                    existing.company = body.company
                if body.job_title is not None:
                    existing.job_title = body.job_title
                if body.manager_actor_id is not None:
                    existing.manager_actor_id = str(body.manager_actor_id)
                await db.commit()
                return ActorRead.model_validate(existing)
            raise conflict(
                "Ya existe un actor con ese email en el tenant",
                code="ACTOR_EMAIL_DUPLICATE",
                fields={"existing_actor_id": str(existing.id)},
            )

    a = Actor(
        tenant_id=str(tenant_id),
        team_id=str(body.team_id) if body.team_id else None,
        area_id=str(body.area_id) if body.area_id else None,
        user_id=str(body.user_id) if body.user_id else None,
        name=body.name.strip(),
        email=str(body.email).strip().lower() if body.email else None,
        phone=body.phone,
        is_active=body.is_active,
        is_lead=body.is_lead,
        # BUG-072: campos de enriquecimiento US-114. El schema los aceptaba
        # pero el constructor los ignoraba — el frontend pedía Empresa /
        # Cargo y al guardar la persona el valor se perdía.
        company=body.company,
        job_title=body.job_title,
        manager_actor_id=(
            str(body.manager_actor_id) if body.manager_actor_id else None
        ),
        created_by=str(cu.id),
        # US-182: pool de recursos con capacidad. Los None caen a los
        # defaults del modelo (100/100, no-clave, compartido).
        organization_id=(
            str(body.organization_id) if body.organization_id else None
        ),
        resource_type=body.resource_type,
        portfolio_function=body.portfolio_function,
        seniority=body.seniority,
        scarcity_level=body.scarcity_level,
        location=body.location,
        skills_tags=body.skills_tags if body.skills_tags is not None else [],
        **(
            {"nominal_capacity_pct": body.nominal_capacity_pct}
            if body.nominal_capacity_pct is not None
            else {}
        ),
        **(
            {"project_capacity_pct": body.project_capacity_pct}
            if body.project_capacity_pct is not None
            else {}
        ),
        **(
            {"is_key_resource": body.is_key_resource}
            if body.is_key_resource is not None
            else {}
        ),
        **(
            {"is_shared_resource": body.is_shared_resource}
            if body.is_shared_resource is not None
            else {}
        ),
        fte_cost_rate=body.fte_cost_rate,
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
            # ENH-084 rework: si el team se setea, area_id queda en
            # sync con team.area_id automáticamente para mantener
            # consistencia, salvo que el caller pase area_id explícito.
            if "area_id" not in data_full:
                a.area_id = str(parent_team.area_id)
        else:
            a.team_id = None
    if "area_id" in data_full:
        new_area_id = data_full["area_id"]
        if new_area_id is not None:
            parent_area = (
                await db.execute(
                    select(Area).where(
                        Area.id == str(new_area_id),
                        Area.tenant_id == str(tenant_id),
                    )
                )
            ).scalar_one_or_none()
            if parent_area is None:
                raise validation_error("area_id no existe en el tenant")
            a.area_id = str(new_area_id)
        else:
            a.area_id = None
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        if k in ("team_id", "area_id"):
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


# =============================================================================
# /admin/areas/{area_id}/assignments — US-103 catálogo compartido
# =============================================================================
assignments_router = APIRouter(prefix="/admin/areas", tags=["areas"])


@assignments_router.get(
    "/{area_id}/assignments",
    response_model=list[AreaAssignmentRead],
)
async def list_area_assignments(
    area_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    # Validar que el área pertenece al tenant
    area = (
        await db.execute(
            select(Area).where(
                Area.id == str(area_id),
                Area.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if area is None:
        raise not_found("Area")
    # ENH-080: enriquece cada assignment con nombre legible del scope
    # destino (org/program/project) para que el dropdown del catálogo
    # admin pueda mostrar a qué Org/Programa/Proyectos está habilitada.
    from app.models.organization import Organization, Program
    from app.models.project import Project

    rows = (
        await db.execute(
            select(AreaAssignment).where(
                AreaAssignment.tenant_id == str(tenant_id),
                AreaAssignment.area_id == str(area_id),
            )
        )
    ).scalars().all()

    org_ids = {r.organization_id for r in rows if r.organization_id}
    prog_ids = {r.program_id for r in rows if r.program_id}
    proj_ids = {r.project_id for r in rows if r.project_id}

    org_names: dict[str, str] = {}
    if org_ids:
        for oid, oname in (
            await db.execute(
                select(Organization.id, Organization.name).where(
                    Organization.id.in_(org_ids)
                )
            )
        ).all():
            org_names[str(oid)] = oname
    prog_names: dict[str, str] = {}
    if prog_ids:
        for pid, pname in (
            await db.execute(
                select(Program.id, Program.name).where(Program.id.in_(prog_ids))
            )
        ).all():
            prog_names[str(pid)] = pname
    proj_names: dict[str, str] = {}
    if proj_ids:
        for pid, pname in (
            await db.execute(
                select(Project.id, Project.name).where(Project.id.in_(proj_ids))
            )
        ).all():
            proj_names[str(pid)] = pname

    out: list[AreaAssignmentRead] = []
    for r in rows:
        item = AreaAssignmentRead.model_validate(r)
        if r.organization_id:
            item.organization_name = org_names.get(str(r.organization_id))
        if r.program_id:
            item.program_name = prog_names.get(str(r.program_id))
        if r.project_id:
            item.project_name = proj_names.get(str(r.project_id))
        out.append(item)
    return out


@assignments_router.put(
    "/{area_id}/assignments",
    response_model=list[AreaAssignmentRead],
)
async def set_area_assignments(
    area_id: UUID,
    body: AreaAssignmentSetBody,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Reemplaza el set completo de asignaciones del área.

    Cada `scope` aporta exactamente un destino: organization_id /
    program_id / project_id / is_global. El backend valida exclusividad.
    """
    from sqlalchemy import delete as sa_delete

    tenant_id = _tenant(cu)
    area = (
        await db.execute(
            select(Area).where(
                Area.id == str(area_id),
                Area.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if area is None:
        raise not_found("Area")

    # Validar cada scope
    for s in body.scopes:
        targets = sum(
            [
                bool(s.organization_id),
                bool(s.program_id),
                bool(s.project_id),
                bool(s.is_global),
            ]
        )
        if targets != 1:
            raise validation_error(
                "Cada scope debe especificar exactamente un destino "
                "(organization_id, program_id, project_id o is_global)."
            )

    # Replace strategy: borra todo y reinserta. Simple para v1.
    await db.execute(
        sa_delete(AreaAssignment).where(
            AreaAssignment.tenant_id == str(tenant_id),
            AreaAssignment.area_id == str(area_id),
        )
    )
    new_rows: list[AreaAssignment] = []
    for s in body.scopes:
        row = AreaAssignment(
            tenant_id=str(tenant_id),
            area_id=str(area_id),
            organization_id=str(s.organization_id) if s.organization_id else None,
            program_id=str(s.program_id) if s.program_id else None,
            project_id=str(s.project_id) if s.project_id else None,
            is_global=bool(s.is_global),
            created_by=str(cu.id),
        )
        db.add(row)
        new_rows.append(row)
    await db.commit()
    for r in new_rows:
        await db.refresh(r)
    return [AreaAssignmentRead.model_validate(r) for r in new_rows]


@assignments_router.get(
    "/by-project/{project_id}/actors",
    response_model=list[ActorRead],
)
async def list_actors_by_project(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-079 + BUG-086: lista los Actores del catálogo asignables como
    responsables/owners en un proyecto. Usa la cascada centralizada
    (`area_visibility.actors_visible_to_project`): actores de equipos cuya
    área es visible, actores con ``area_id`` directo a un área visible, y
    actores con participación activa. Antes, una heurística excluía a los
    recursos cargados directo en un área (sin team, sin user, sin is_lead),
    por lo que no aparecían como asignables en RAID/Plan."""
    from app.models.project import Project
    from app.services.area_visibility import actors_visible_to_project

    tenant_id = _tenant(cu)
    project = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise not_found("Project")

    actors = await actors_visible_to_project(db, tenant_id, project)
    return [ActorRead.model_validate(a) for a in actors]


@assignments_router.post("/pmo/sync-users")
async def sync_pmo_users(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-082 — Re-sincroniza users activos del tenant como Actores en
    área PMO (idempotente). Mismo match que migración 0050:
    `actor.user_id == user.id` o `actor.email == user.email`.

    Crea Actores con `team_id=NULL` (sin equipo) bajo el tenant. La
    asociación con el área PMO se hace en el tree endpoint via heurística
    `user_id IS NOT NULL` para evitar agregar `area_id` directo a Actor.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.models.user import User

    tenant_id = _tenant(cu)

    # Asegura que el área PMO exista (puede no haber sido sembrada si
    # el tenant es post-migración 0048).
    pmo = (
        await db.execute(
            select(Area).where(
                Area.tenant_id == str(tenant_id),
                Area.name == "PMO",
            )
        )
    ).scalar_one_or_none()
    if pmo is None:
        pmo = Area(
            tenant_id=str(tenant_id),
            name="PMO",
            description="Área PMO (default, aplica a todos los proyectos)",
            is_active=True,
            created_by=str(cu.id),
        )
        db.add(pmo)
        await db.flush()
        # Garantiza assignment global para que el área aplique a todos
        # los proyectos del tenant.
        db.add(
            AreaAssignment(
                tenant_id=str(tenant_id),
                area_id=str(pmo.id),
                is_global=True,
                created_by=str(cu.id),
            )
        )
        await db.flush()

    users = (
        await db.execute(
            select(User).where(
                User.tenant_id == str(tenant_id),
                User.is_active.is_(True),
            )
        )
    ).scalars().all()

    created = 0
    linked = 0
    skipped = 0
    for u in users:
        # ¿Ya existe Actor por user_id o email?
        existing: Actor | None = None
        if u.email:
            existing = (
                await db.execute(
                    select(Actor).where(
                        Actor.tenant_id == str(tenant_id),
                        Actor.deleted_at.is_(None),
                        (Actor.user_id == str(u.id))
                        | (Actor.email == u.email),
                    )
                )
            ).scalars().first()
        else:
            existing = (
                await db.execute(
                    select(Actor).where(
                        Actor.tenant_id == str(tenant_id),
                        Actor.deleted_at.is_(None),
                        Actor.user_id == str(u.id),
                    )
                )
            ).scalars().first()
        if existing is not None:
            if existing.user_id is None:
                existing.user_id = str(u.id)
                linked += 1
            else:
                skipped += 1
            continue
        actor = Actor(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            team_id=None,
            user_id=str(u.id),
            name=u.full_name or (u.email or "(sin nombre)"),
            email=u.email,
            phone=None,
            is_active=True,
            is_lead=False,
        )
        db.add(actor)
        created += 1

    await db.commit()
    return {
        "created": created,
        "linked": linked,
        "skipped": skipped,
        "total_users": len(users),
        "synced_at": datetime.now(UTC).isoformat(),
    }


@assignments_router.get(
    "/by-project/{project_id}",
    response_model=list[AreaRead],
)
async def list_areas_by_project(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Lista las áreas visibles para un proyecto considerando cascada.

    Un área es visible si:
    - Tiene assignment con `is_global=true`, o
    - Tiene assignment al `project_id` directo, o
    - Tiene assignment al `program_id` del proyecto, o
    - Tiene assignment a la `organization_id` del proyecto.
    """
    from sqlalchemy import or_

    from app.models.project import Project

    tenant_id = _tenant(cu)
    project = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise not_found("Project")

    cond = or_(
        AreaAssignment.is_global == True,  # noqa: E712
        AreaAssignment.project_id == str(project_id),
    )
    if project.program_id:
        cond = or_(cond, AreaAssignment.program_id == str(project.program_id))
    cond = or_(cond, AreaAssignment.organization_id == str(project.organization_id))

    stmt = (
        select(Area)
        .join(AreaAssignment, AreaAssignment.area_id == Area.id)
        .where(
            Area.tenant_id == str(tenant_id),
            Area.is_active == True,  # noqa: E712
            cond,
        )
        .distinct()
        .order_by(Area.name)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [AreaRead.model_validate(r) for r in rows]
