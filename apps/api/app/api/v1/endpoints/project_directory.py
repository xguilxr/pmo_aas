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
from app.core.errors import conflict, mensaje, not_found, validation_error
from app.db.session import get_db
from app.dominio.raci import UNICO as PAPEL_UNICO
from app.models.area import Actor
from app.models.project import Project
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
from app.services.costo_asignacion import congelar as congelar_tarifa
from app.services.costo_asignacion import costo as costo_de_participacion
from app.services.costo_asignacion import resumen_de_proyecto


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
        raise conflict(mensaje(
            que="Project role with this name already exists",
            porque="Dos roles con el mismo nombre serían indistinguibles al asignar.",
            accion="Elige otro nombre, o edita el existente.",
        ))
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
        raise not_found("Rol en el proyecto")
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
        raise not_found("Rol en el proyecto")
    # Restrict si está en uso.
    in_use = (
        await db.execute(
            select(ProjectParticipation.id).where(
                ProjectParticipation.project_role_id == str(role_id)
            ).limit(1)
        )
    ).first()
    if in_use:
        raise conflict(mensaje(
            que="Project role in use, cannot delete",
            porque="Hay personas asignadas con ese rol y quedarían sin él.",
            accion="Reasigna a esas personas y vuelve a intentarlo.",
        ))
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
    # US-215 — el costo se **deriva** al leer, no se guarda. Un costo almacenado
    # se queda viejo el día que alguien mueve las fechas o el % de dedicación por
    # un camino que se olvidó de recalcularlo; es la misma razón por la que la
    # completitud de US-210 se deriva. Lo que sí está guardado es la tarifa.
    total = costo_de_participacion(part)
    data.cost_total = float(total) if total is not None else None
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


async def _exigir_una_sola_a(
    db: AsyncSession, tenant_id: str, project_id: str, *, esta: str, papel: str | None
) -> None:
    """US-217 — rechaza una segunda `A` en el mismo proyecto.

    La `A` es el único papel que no se puede repartir: si dos personas responden
    por el resultado, ninguna lo hace. Los otros tres se pueden dar a quien haga
    falta.

    El error nombra **a quién** la tiene ya: «Ana Ruiz ya es la A» es accionable
    y «ya hay una A» obliga a ir a buscarla, que es exactamente el paso que hace
    que alguien deje el RACI a medias.

    No hay restricción de base de datos que lo cubra a propósito: un índice único
    parcial funcionaría en Postgres y no en SQLite, y una regla que solo se
    cumple en producción es peor que una que se cumple en la frontera.
    """
    if papel != PAPEL_UNICO:
        return
    filas = (
        await db.execute(
            select(ProjectParticipation.id, ProjectParticipation.actor_id)
            .where(
                ProjectParticipation.tenant_id == tenant_id,
                ProjectParticipation.project_id == project_id,
                ProjectParticipation.raci == PAPEL_UNICO,
                ProjectParticipation.id != esta,
            )
            .limit(1)
        )
    ).all()
    if not filas:
        return
    _, actor_id = filas[0]
    nombre = (
        await db.execute(select(Actor.name).where(Actor.id == str(actor_id)))
    ).scalar_one_or_none()
    raise validation_error(
        mensaje(
            que=f"{nombre or 'otra persona'} ya es el responsable último (A) "
            "de este proyecto",
            porque="La «A» del RACI responde por el resultado y no se puede "
            "repartir: si dos personas responden, ninguna lo hace.",
            accion=f"Quítale la A a {nombre or 'quien la tiene'} antes de "
            "asignarla, o usa «R» si esta persona ejecuta el trabajo.",
        ),
        {"raci": "duplicada"},
    )


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
        raise not_found("Actor en la organización")

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
        # US-183: FTE% + ciclo de vida de capacidad.
        allocation_pct=body.allocation_pct,
        assignment_type=body.assignment_type,
        status=body.status,
        is_critical=body.is_critical,
        phase=body.phase,
        # US-217 — RACI y stakeholder clave.
        raci=body.raci,
        is_key_stakeholder=body.is_key_stakeholder,
        created_by=str(cu.user.id),
    )
    db.add(part)
    await db.flush()
    # US-215 — la tarifa se congela aquí, del catálogo. Que el actor no tenga
    # tarifa capturada es lo normal y **no** impide asignarlo: `congelar`
    # devuelve `False` y la participación queda sin costo calculable, que es la
    # verdad. Se puede congelar después con el endpoint explícito.
    await congelar_tarifa(db, tenant_id=_tenant(cu), participacion=part)
    await _exigir_una_sola_a(
        db, str(_tenant(cu)), str(project_id), esta=str(part.id), papel=body.raci
    )
    if body.is_primary:
        await _ensure_unique_primary(
            db, str(project_id), str(body.actor_id), keep_id=part.id
        )
    # US-184: fast-path — si con esta asignación el actor quedó
    # sobreasignado, alerta a los PMs afectados. Nunca bloquea el write.
    if body.allocation_pct is not None:
        try:
            from app.models.tenant import Tenant
            from app.services.capacity_alerts import alert_actor_if_overloaded

            tenant = (
                await db.execute(
                    select(Tenant).where(Tenant.id == str(_tenant(cu)))
                )
            ).scalar_one_or_none()
            await alert_actor_if_overloaded(db, tenant, str(body.actor_id))
        except Exception:  # pragma: no cover
            pass
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
        raise not_found("Participación")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in {"operational_team_id", "project_role_id", "functional_area_id"}:
            setattr(part, k, str(v) if v else None)
        elif k == "raci":
            # US-217 — la cadena vacía quita el papel. Un `None` no serviría:
            # `exclude_unset` ya distingue «no lo mandes», así que `None`
            # tendría dos lecturas y una de las dos se acabaría equivocando.
            setattr(part, k, v or None)
        else:
            setattr(part, k, v)
    await db.flush()
    if "raci" in data:
        await _exigir_una_sola_a(
            db,
            str(_tenant(cu)),
            str(project_id),
            esta=str(part.id),
            papel=part.raci,
        )
    if data.get("is_primary") is True:
        await _ensure_unique_primary(
            db, str(project_id), part.actor_id, keep_id=part.id
        )
    # US-184: fast-path de alerta si cambió FTE/estado de la asignación.
    if "allocation_pct" in data or "status" in data:
        try:
            from app.models.tenant import Tenant
            from app.services.capacity_alerts import alert_actor_if_overloaded

            tenant = (
                await db.execute(
                    select(Tenant).where(Tenant.id == str(_tenant(cu)))
                )
            ).scalar_one_or_none()
            await alert_actor_if_overloaded(db, tenant, str(part.actor_id))
        except Exception:  # pragma: no cover
            pass
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
        raise not_found("Participación")
    part.is_active = False
    part.is_primary = False
    await db.commit()


# ---------------------------------------------------------------------------
# US-215 — costo de recursos: congelar la tarifa y leer el total
# ---------------------------------------------------------------------------


@participations_router.post(
    "/{participation_id}/freeze-cost-rate", response_model=ParticipationRead
)
async def freeze_cost_rate(
    project_id: UUID,
    participation_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> ParticipationRead:
    """US-215 — vuelve a copiar la tarifa del catálogo a esta asignación.

    Existe porque congelar al asignar no alcanza en los dos casos reales:
    la persona se asignó antes de que alguien capturara su tarifa, y la tarifa
    de verdad cambió para este proyecto.

    **Recongelar revalúa la asignación entera** al nuevo importe, incluido el
    trabajo ya hecho. Es una limitación conocida de tener un solo snapshot por
    participación, y la salida correcta cuando la tarifa cambia a mitad de camino
    ya existe en el modelo: cerrar la participación en la fecha del cambio y
    abrir otra con el periodo nuevo. Las participaciones ya llevan
    `start_date`/`end_date` y ciclo de vida (US-183) justamente para eso; una
    tabla de historial de tarifas resolvería lo mismo duplicando el mecanismo.

    Falla con 422 —y no en silencio— si el actor no tiene tarifa **y** periodo en
    el catálogo. Aquí sí es un error: alguien pidió explícitamente congelar, y
    devolver un 200 sin haber congelado nada dejaría al usuario creyendo que ya
    está.
    """
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
        raise not_found("Participación")
    if not await congelar_tarifa(db, tenant_id=_tenant(cu), participacion=part):
        raise validation_error(
            mensaje(
                que="Esta persona no tiene tarifa y unidad de tiempo en el catálogo",
                porque="Sin la tarifa no hay importe, y sin la unidad —por hora, "
                "por día o por mes— el importe no significa nada: multiplicarlo "
                "suponiendo una daría un costo creíble y falso.",
                accion="Captura la tarifa y su unidad en el catálogo de recursos "
                "y vuelve a congelar.",
            ),
            {"cost_rate_snapshot": "sin tarifa en el catálogo"},
        )
    await db.commit()
    await db.refresh(part)
    actor = (
        await db.execute(select(Actor).where(Actor.id == str(part.actor_id)))
    ).scalar_one_or_none()
    return _hydrate(part, actor)


@participations_router.get("/cost-summary")
async def project_cost_summary(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """US-215 — el costo de recursos del proyecto, **por moneda**.

    Nunca un total único: dos personas facturadas en monedas distintas no tienen
    un costo total, y sumarlas inventaría un número que no existe en ninguna
    parte. Convertir exigiría un tipo de cambio con fecha, que es una estimación
    y no un dato (misma regla que `dominio/moneda.py`).

    Viene con `without_rate` **en la misma respuesta**. Un total sin ese número
    miente por omisión: «$400.000 en recursos» con doce asignaciones sin tarifa
    es un presupuesto a medias presentado como completo. En llamadas separadas se
    puede mostrar uno sin el otro, y eso es lo que hay que impedir.

    Solo cuentan las asignaciones con estado `activa` — una tentativa no es un
    compromiso de gasto y una cancelada no lo fue nunca—, el mismo criterio que
    el motor de saturación de US-183.
    """
    rows = (
        (
            await db.execute(
                select(ProjectParticipation).where(
                    and_(
                        ProjectParticipation.tenant_id == str(_tenant(cu)),
                        ProjectParticipation.project_id == str(project_id),
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    return resumen_de_proyecto(list(rows))

