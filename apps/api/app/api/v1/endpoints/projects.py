from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, conflict, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import (
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

router = APIRouter(prefix="/projects", tags=["projects"])

VALID_TRANSITIONS = {
    "planning": {"execution", "closed"},
    "execution": {"support", "closed"},
    "support": {"closed"},
    "closed": set(),
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

    rows = (
        await db.execute(stmt.order_by(Project.created_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()
    return [ProjectRead.model_validate(p) for p in rows]


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
    except Exception:
        pass

    out = ProjectRead.model_validate(p).model_dump()
    out["members"] = members
    out["module_counts"] = counts
    return out


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
    await db.commit()
    return ProjectRead.model_validate(p)


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
