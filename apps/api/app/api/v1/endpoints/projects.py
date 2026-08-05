from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, conflict, forbidden, not_found, validation_error
from app.core.visibility import get_user_visibility
from app.db.session import get_db
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.models.project_member import ProjectMember
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.project import (
    ActivityItem,
    HealthDeclare,
    HealthEvaluationCreate,
    HealthEvaluationRead,
    MemberCreate,
    PhaseChange,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectUpdate,
)
from app.services.audit import write_audit
from app.services.charter_generator import generate_charter_docx
from app.services.folio import next_folio
from app.services.plan_metadata import round_half_up
from app.services.progress_calculator import plan_rollup_map
from app.services.project_health import (
    apply_auto_health,
    compute_project_health_detail,
)
from app.services.project_membership_sync import sync_member_to_participation

router = APIRouter(prefix="/projects", tags=["projects"])

# ADR-022: `cancelled` se alcanza desde cualquier fase viva. Cancelar no es un
# paso más del ciclo —es interrumpirlo—, así que no depende de dónde estaba el
# proyecto: se puede cortar un proyecto en planificación, en ejecución o en
# hypercare, y en los tres casos el final es el mismo.
#
# `closed` NO lleva a `cancelled`: un proyecto que llegó al final ya tuvo su
# final. Los dos son terminales, por la misma razón que `closed` lo era.
VALID_TRANSITIONS = {
    "planning": {"execution", "closed", "cancelled"},
    "execution": {"hypercare", "closed", "cancelled"},
    "hypercare": {"closed", "cancelled"},
    "closed": set(),
    "cancelled": set(),
}


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    phase: list[str] | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    no_program: bool = Query(default=False),
    type: list[str] | None = Query(default=None),
    health: list[str] | None = Query(default=None),
    priority_min: int | None = Query(default=None, ge=1, le=5),
    priority_max: int | None = Query(default=None, ge=1, le=5),
    q: str | None = Query(default=None),
    only_mine: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=15, ge=1, le=100),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Project).where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
    if phase:
        stmt = stmt.where(Project.phase.in_(phase))
    if organization_id:
        stmt = stmt.where(Project.organization_id == str(organization_id))
    if program_id:
        stmt = stmt.where(Project.program_id == str(program_id))
    if no_program:
        stmt = stmt.where(Project.program_id.is_(None))
    if type:
        stmt = stmt.where(Project.type.in_(type))
    if health:
        stmt = stmt.where(Project.health_status.in_(health))
    if priority_min is not None:
        stmt = stmt.where(Project.priority >= priority_min)
    if priority_max is not None:
        stmt = stmt.where(Project.priority <= priority_max)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Project.name).like(like),
                func.lower(Project.folio).like(like),
                func.lower(Project.sponsor).like(like),
            )
        )
    if only_mine:
        stmt = stmt.join(ProjectMember, ProjectMember.project_id == Project.id).where(
            ProjectMember.user_id == cu.id
        )

    # US-168: PM users see only projects from their scope assignments
    if not cu.is_admin_equivalent:
        visibility = await get_user_visibility(cu.user, db)
        if not visibility.unrestricted:
            if not visibility.project_ids:
                return []
            stmt = stmt.where(Project.id.in_(visibility.project_ids))

    rows = (
        await db.execute(stmt.order_by(Project.created_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()
    # ENH-109 — el avance del resumen se deriva del plan (promedio de los
    # WBS de nivel más alto). El campo manual `Project.progress` queda como
    # fallback para proyectos sin plan. Un solo SELECT de tasks por la página.
    plan_map = await plan_rollup_map(db, [p.id for p in rows])
    out: list[ProjectRead] = []
    for p in rows:
        r = ProjectRead.model_validate(p)
        derived = plan_map.get(str(p.id))
        if derived is not None:
            r.progress = round_half_up(derived)
        out.append(r)
    return out


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    body: ProjectCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(body.organization_id), Organization.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise business_rule("organization_id inválido")

    pm = (
        await db.execute(
            select(User).where(User.id == str(body.pm_id), User.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if pm is None:
        raise validation_error("pm_id inválido")

    folio = await next_folio(db, tenant_id=tenant_id, prefix="PRJ")
    data = body.model_dump()
    for k in ("organization_id", "program_id", "pm_id"):
        if data.get(k) is not None:
            data[k] = str(data[k])
    project = Project(tenant_id=tenant_id, folio=folio, **data)
    db.add(project)
    await db.flush()

    db.add(ProjectMember(project_id=project.id, user_id=str(body.pm_id), role_in_project="pm"))
    # US-118 Fase 1: doble escritura → project_participations.
    await sync_member_to_participation(
        db, tenant_id, project.id, str(body.pm_id), "pm"
    )

    # BUG-018: autocrear charter + documento con la info que llega del form.
    # Los campos no capturados (stakeholders extra, prioridad, alcance,
    # beneficios, restricciones, riesgos) se complementan en la UI del
    # charter (secciones 1-3). Mismo patrón que create_project_from_request.
    charter = ProjectCharter(
        tenant_id=tenant_id,
        project_id=project.id,
        request_id=None,
        project_name=project.name,
        description=project.description,
        organization_id=project.organization_id,
        sponsor=project.sponsor,
        pm_id=str(body.pm_id),
        project_type=project.type,
        priority=project.priority,
        created_by=cu.id,
    )
    db.add(charter)
    await db.flush()

    # BUG-028: genera el .docx real del charter y lo sube al storage (R2
    # en prod, local en dev). El Document se crea dentro del generator.
    charter_doc = await generate_charter_docx(
        db,
        tenant_id=tenant_id,
        project=project,
        charter=charter,
        created_by=cu.id,
    )

    await write_audit(
        db, action="project.create", module="projects", user_id=cu.id, tenant_id=tenant_id,
        entity_type="project", entity_id=str(project.id),
        details={
            "folio": folio,
            "charter_id": str(charter.id),
            "charter_doc_id": str(charter_doc.id),
        },
    )

    # US-027/028: notificar PM asignado al crear el proyecto. No si el PM
    # es quien lo creó (sería self-notification ruidosa).
    if str(body.pm_id) != cu.id:
        from app.services.notifications import PM_ASSIGNED, enqueue_notification

        await enqueue_notification(
            db,
            tenant_id=tenant_id,
            user_id=str(body.pm_id),
            type=PM_ASSIGNED,
            title=f"Te asignaron como PM de {project.name}",
            body=f"Folio {folio}. Complementa el Project Charter antes de arrancar.",
            entity_type="project",
            entity_id=str(project.id),
            link=f"/admin/projects/{project.id}/charter",
        )

    await db.commit()
    return ProjectRead.model_validate(project)


async def _get_project(db: AsyncSession, project_id: UUID, tenant_id: UUID) -> Project:
    p = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id), Project.tenant_id == tenant_id,
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if p is None:
        raise not_found("Proyecto")
    return p


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)

    members_rows = (
        await db.execute(
            select(ProjectMember.user_id, ProjectMember.role_in_project, User.username, User.full_name)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == p.id)
        )
    ).all()
    members = [
        {"user_id": str(r.user_id), "role_in_project": r.role_in_project,
         "username": r.username, "full_name": r.full_name}
        for r in members_rows
    ]

    counts: dict[str, int] = {}
    try:
        from app.models.modules import (  # type: ignore
            ChangeRequest,
            Document,
            Issue,
            Lesson,
            MeetingMinute,
            Risk,
        )

        for label, model in [
            ("risks", Risk), ("issues", Issue), ("change_requests", ChangeRequest),
            ("documents", Document), ("lessons", Lesson), ("minutes", MeetingMinute),
        ]:
            counts[label] = (
                await db.execute(select(func.count(model.id)).where(model.project_id == p.id))
            ).scalar_one()
        # ENH-130: RAID desglosado por tipo de Issue (action/issue/decision)
        # para las tarjetas Acciones / Incidentes / Decisiones del Resumen.
        for label, issue_type in [
            ("actions", "action"), ("incidents", "issue"), ("decisions", "decision"),
        ]:
            counts[label] = (
                await db.execute(
                    select(func.count(Issue.id)).where(
                        Issue.project_id == p.id, Issue.type == issue_type
                    )
                )
            ).scalar_one()
    except Exception:
        pass

    # ENH-129: KPIs de tareas para el gauge de Avance (hitos, críticos,
    # atrasados). Atrasado = fin < hoy y no completada.
    task_kpis: dict[str, int] = {}
    try:
        from app.models.task import Task  # type: ignore

        today = date.today()
        task_kpis["milestones_total"] = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == p.id, Task.is_milestone.is_(True)
                )
            )
        ).scalar_one()
        task_kpis["milestones_done"] = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == p.id,
                    Task.is_milestone.is_(True),
                    Task.status == "completed",
                )
            )
        ).scalar_one()
        task_kpis["critical_total"] = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == p.id, Task.is_critical.is_(True)
                )
            )
        ).scalar_one()
        task_kpis["critical_done"] = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == p.id,
                    Task.is_critical.is_(True),
                    Task.status == "completed",
                )
            )
        ).scalar_one()
        task_kpis["overdue"] = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == p.id,
                    Task.end_date.is_not(None),
                    Task.end_date < today,
                    Task.status != "completed",
                )
            )
        ).scalar_one()
    except Exception:
        pass

    out = ProjectRead.model_validate(p).model_dump()
    # ENH-109 — avance derivado del plan también en el detalle.
    plan_map = await plan_rollup_map(db, [p.id])
    derived = plan_map.get(str(p.id))
    if derived is not None:
        out["progress"] = round_half_up(derived)
    out["members"] = members
    out["module_counts"] = counts
    out["task_kpis"] = task_kpis
    return out


@router.get("/{project_id}/activity", response_model=list[ActivityItem])
async def get_project_activity(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-149: feed de actividad del proyecto leído del audit log.

    Eventos a nivel proyecto (cambios de fase, salud, asignaciones,
    actualizaciones) en orden cronológico inverso.
    """
    from app.models.audit import AuditLog

    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)  # valida acceso

    rows = (
        await db.execute(
            select(AuditLog, User.full_name)
            .outerjoin(User, User.id == AuditLog.user_id)
            .where(
                AuditLog.entity_type == "project",
                AuditLog.entity_id == str(p.id),
            )
            .order_by(AuditLog.occurred_at.desc())
            .limit(limit)
        )
    ).all()

    return [
        ActivityItem(
            id=row.AuditLog.id,
            action=row.AuditLog.action,
            module=row.AuditLog.module,
            occurred_at=row.AuditLog.occurred_at,
            user_id=row.AuditLog.user_id,
            user_name=row.full_name,
            details=row.AuditLog.details or {},
        )
        for row in rows
    ]


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no editable")
    data = body.model_dump(exclude_none=True)
    before = {k: getattr(p, k) for k in data}
    health_changed = (
        "health_status" in data and before.get("health_status") != data["health_status"]
    )
    for k, v in data.items():
        if k in ("program_id", "pm_id") and v is not None:
            v = str(v)
        setattr(p, k, v)
    # US-084: campos agregados editados a mano. Marcamos en
    # manually_edited_fields para que importadores los respeten y la
    # UI muestre badge de "editado manualmente".
    plan_aggregate_fields = {"start_date", "end_date", "budget", "progress"}
    touched = plan_aggregate_fields.intersection(data.keys())
    if touched:
        edited = dict(p.manually_edited_fields or {})
        now_iso = datetime.now(UTC).isoformat()
        for k in touched:
            edited[k] = {"edited_at": now_iso, "edited_by": str(cu.id)}
        p.manually_edited_fields = edited
    await write_audit(
        db, action="project.update", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(p.id),
        details={"before": {k: str(v) for k, v in before.items()}, "after": {k: str(v) for k, v in data.items()}},
    )
    # US-180: tocar health_status por el PATCH genérico cuenta como
    # declaración manual (sin razón). El flujo con razón vive en
    # PATCH /projects/{id}/health.
    if health_changed:
        p.health_source = "manual"
        await write_audit(
            db, action="project.health.declared", module="projects",
            user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(p.id),
            details={
                "before": str(before.get("health_status")),
                "after": data["health_status"],
                "source": "manual",
                "reason": None,
            },
        )
    await db.commit()
    return ProjectRead.model_validate(p)


@router.get("/{project_id}/health-detail")
async def get_health_detail(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-180 — desglose de salud por dimensiones + causas + foco PM.

    Si la fuente es 'auto', refresca el semáforo persistido con el color
    calculado (mantiene honestos los agregados SQL de dashboards).
    """
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    detail = await compute_project_health_detail(db, tenant, p)
    if apply_auto_health(p, detail["computed"]):
        await db.commit()
    return {
        "health_status": p.health_status,
        "health_source": p.health_source,
        "health_reason": p.health_reason,
        "computed": detail["computed"],
        "dimensions": detail["dimensions"],
        "focus": detail["focus"],
    }


@router.patch("/{project_id}/health", response_model=ProjectRead)
async def declare_health(
    project_id: UUID,
    body: HealthDeclare,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-180 — declarar el semáforo (con razón) o volver a 'auto'."""
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no editable")

    before = {"status": p.health_status, "source": p.health_source}
    if body.status is None:
        # Volver a fuente automática: recalcular de inmediato.
        p.health_source = "auto"
        p.health_reason = None
        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
        ).scalar_one_or_none()
        detail = await compute_project_health_detail(db, tenant, p)
        p.health_status = detail["computed"]
    else:
        reason = (body.reason or "").strip()
        if body.status in ("yellow", "red") and len(reason) < 5:
            raise validation_error(
                "Declarar salud amarilla o roja requiere una razón (mínimo 5 caracteres)"
            )
        p.health_status = body.status
        p.health_source = "manual"
        p.health_reason = reason or None

    await write_audit(
        db, action="project.health.declared", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(p.id),
        details={
            "before": f"{before['status']} ({before['source']})",
            "after": f"{p.health_status} ({p.health_source})",
            "reason": p.health_reason,
        },
    )
    await db.commit()
    return ProjectRead.model_validate(p)


@router.post(
    "/{project_id}/health-evaluations",
    response_model=HealthEvaluationRead,
    status_code=201,
)
async def create_health_evaluation(
    project_id: UUID,
    body: HealthEvaluationCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-191 — evaluación de salud del período: 5 dimensiones + overall
    (la "sexta") con fecha. Cada guardado es un registro histórico; el
    overall se aplica al semáforo del proyecto como declaración manual
    (nota obligatoria en amarillo/rojo, regla US-180)."""
    from datetime import date as _date

    from app.models.project import ProjectHealthEvaluation

    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no editable")

    note = (body.note or "").strip()
    if body.overall in ("yellow", "red") and len(note) < 5:
        raise validation_error(
            "Evaluar la salud global en amarillo o rojo requiere una nota "
            "(mínimo 5 caracteres)"
        )

    ev = ProjectHealthEvaluation(
        tenant_id=str(tenant_id),
        project_id=str(project_id),
        evaluated_at=body.evaluated_at or _date.today(),
        schedule=body.schedule,
        budget=body.budget,
        risks=body.risks,
        decisions=body.decisions,
        resources=body.resources,
        overall=body.overall,
        note=note or None,
        created_by=str(cu.id),
    )
    db.add(ev)

    # La sexta evaluación ES el semáforo del proyecto (cuadro grande).
    p.health_status = body.overall
    p.health_source = "manual"
    p.health_reason = note or f"Evaluación PM {ev.evaluated_at.isoformat()}"

    await write_audit(
        db, action="project.health.evaluated", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project",
        entity_id=str(p.id),
        details={
            "evaluated_at": ev.evaluated_at.isoformat(),
            "overall": body.overall,
            "dimensions": {
                k: getattr(body, k)
                for k in ("schedule", "budget", "risks", "decisions", "resources")
                if getattr(body, k)
            },
        },
    )
    await db.commit()
    await db.refresh(ev)
    return HealthEvaluationRead.model_validate(ev)


@router.get(
    "/{project_id}/health-evaluations",
    response_model=list[HealthEvaluationRead],
)
async def list_health_evaluations(
    project_id: UUID,
    limit: int = Query(default=12, ge=1, le=100),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-191 — historial de evaluaciones (más reciente primero)."""
    from app.models.project import ProjectHealthEvaluation

    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    rows = (
        await db.execute(
            select(ProjectHealthEvaluation)
            .where(ProjectHealthEvaluation.project_id == str(project_id))
            .order_by(
                ProjectHealthEvaluation.evaluated_at.desc(),
                ProjectHealthEvaluation.created_at.desc(),
            )
            .limit(limit)
        )
    ).scalars().all()
    return [HealthEvaluationRead.model_validate(r) for r in rows]


@router.post("/{project_id}/plan-aggregates/reset", response_model=ProjectRead)
async def reset_plan_aggregate(
    project_id: UUID,
    body: dict,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-084: quita el flag de 'editado manualmente' de un campo del
    plan. Body: `{"field": "start_date"}`. El valor actual del campo
    se preserva pero queda elegible para sobrescritura por importadores.
    """
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    if p.phase == "closed":
        raise business_rule("Proyecto cerrado, no editable")
    field = body.get("field")
    if field not in {"start_date", "end_date", "budget", "progress"}:
        raise validation_error("field inválido")
    edited = dict(p.manually_edited_fields or {})
    edited.pop(field, None)
    p.manually_edited_fields = edited
    await db.commit()
    return ProjectRead.model_validate(p)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):

    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    p.deleted_at = datetime.now(UTC)
    await write_audit(
        db, action="project.delete", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(p.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.post("/{project_id}/phase/change", response_model=ProjectRead)
async def change_phase(
    project_id: UUID,
    body: PhaseChange,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    if body.new_phase not in VALID_TRANSITIONS.get(p.phase, set()):
        raise conflict(
            f"Transición inválida: {p.phase} → {body.new_phase}", code="STATE_TRANSITION"
        )
    if body.new_phase == "execution" and p.start_date is None:
        raise business_rule("start_date es obligatoria al pasar a execution")
    old = p.phase
    p.phase = body.new_phase
    await write_audit(
        db, action="project.phase_change", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(p.id),
        details={"from": old, "to": body.new_phase, "comment": body.comment},
    )
    await db.commit()
    return ProjectRead.model_validate(p)


@router.get("/{project_id}/members")
async def list_members(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    rows = (
        await db.execute(
            select(ProjectMember.user_id, ProjectMember.role_in_project, User.username, User.full_name)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == str(project_id))
        )
    ).all()
    return [
        {"user_id": str(r.user_id), "role_in_project": r.role_in_project,
         "username": r.username, "full_name": r.full_name}
        for r in rows
    ]


@router.post("/{project_id}/members", status_code=201)
async def add_member(
    project_id: UUID,
    body: MemberCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    await _get_project(db, project_id, tenant_id)
    exists = (
        await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == str(project_id),
                ProjectMember.user_id == str(body.user_id),
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        raise conflict("Miembro ya existe en el proyecto")
    db.add(
        ProjectMember(
            project_id=str(project_id), user_id=str(body.user_id),
            role_in_project=body.role_in_project,
        )
    )
    await write_audit(
        db, action="project.member.add", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(project_id),
        details={"member": str(body.user_id), "role_in_project": body.role_in_project},
    )
    await db.commit()
    return {"ok": True}


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    if str(user_id) == (str(p.pm_id) if p.pm_id else ""):
        raise business_rule("No puedes remover al PM vigente; cambia pm_id primero")
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == str(project_id),
            ProjectMember.user_id == str(user_id),
        )
    )
    await write_audit(
        db, action="project.member.remove", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(project_id),
        details={"member": str(user_id)},
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get("/{project_id}/export")
async def export_project(
    project_id: UUID,
    format: str = Query(default="json", pattern="^(json|pdf)$"),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    payload = ProjectRead.model_validate(p).model_dump(mode="json")
    if format == "json":
        return payload
    # PDF MVP: texto plano devuelto como application/pdf minimal-ish.
    # Producción: integrar WeasyPrint en worker.
    from fastapi.responses import Response

    body = (
        f"Proyecto {p.folio}\n{p.name}\nFase: {p.phase}\n"
        f"Avance: {p.progress}%\nPresupuesto: {p.budget}\n"
    ).encode()
    return Response(content=body, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={p.folio}.pdf"})


@router.get("/{project_id}/progress")
async def get_project_progress(
    project_id: UUID,
    method: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-121 — Return ``% avance`` resolved by the configured method.

    Optional ``?method=`` query param overrides the tenant default.
    Response shape: ``{"value": float, "method": str, "fallback": str|None}``.
    """
    from app.services.progress_calculator import compute_progress_detailed

    tenant_id = _tenant(cu)
    p = await _get_project(db, project_id, tenant_id)
    result = await compute_progress_detailed(db, p.id, method=method)
    payload: dict[str, object] = {
        "value": result.value,
        "method": result.method,
    }
    if result.fallback is not None:
        payload["fallback"] = result.fallback
    return payload
