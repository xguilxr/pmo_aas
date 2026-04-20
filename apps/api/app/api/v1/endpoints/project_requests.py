from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, conflict, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.organization import BusinessUnit, Department, Organization
from app.models.project_request import ProjectRequest
from app.schemas.project_request import (
    CreateProjectFromRequest,
    ProjectRequestCreate,
    ProjectRequestRead,
    ProjectRequestUpdate,
    ReviewRequest,
)
from app.services.audit import write_audit
from app.services.folio import next_folio

router = APIRouter(prefix="/project-requests", tags=["project_requests"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


@router.post("", response_model=ProjectRequestRead, status_code=201)
async def create_request(
    body: ProjectRequestCreate,
    cu: CurrentUser = Depends(require_permission("admin.requests", "create")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(body.organization_id),
                Organization.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise business_rule("La organización no existe en tu tenant")

    # Validar FKs BU/Depto si vienen (US-NEW-011).
    if body.business_unit_id is not None:
        bu = (
            await db.execute(
                select(BusinessUnit).where(
                    BusinessUnit.id == str(body.business_unit_id),
                    BusinessUnit.tenant_id == tenant_id,
                    BusinessUnit.organization_id == str(body.organization_id),
                    BusinessUnit.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if bu is None:
            raise business_rule(
                "La unidad de negocio no pertenece a la organización indicada"
            )
    if body.department_id is not None:
        dept = (
            await db.execute(
                select(Department).where(
                    Department.id == str(body.department_id),
                    Department.tenant_id == tenant_id,
                    Department.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if dept is None:
            raise business_rule("El departamento no existe o no pertenece al tenant")
        if (
            body.business_unit_id is not None
            and str(dept.business_unit_id) != str(body.business_unit_id)
        ):
            raise business_rule(
                "El departamento no pertenece a la unidad de negocio indicada"
            )

    folio = await next_folio(db, tenant_id=tenant_id, prefix="SOL")
    pr = ProjectRequest(
        tenant_id=tenant_id,
        folio=folio,
        title=body.title,
        description=body.description,
        objective=body.objective,
        organization_id=str(body.organization_id),
        business_unit=body.business_unit,
        department=body.department,
        business_unit_id=(
            str(body.business_unit_id) if body.business_unit_id else None
        ),
        department_id=str(body.department_id) if body.department_id else None,
        sponsor=body.sponsor,
        sponsor_email=str(body.sponsor_email),
        benefits=body.benefits,
        budget=body.budget,
        scope=body.scope,
        entregables=body.entregables,
        key_people=body.key_people,
        if_not_done=body.if_not_done,
        observations=body.observations,
        requester_name=body.requester_name or cu.user.full_name,
        requester_email=(
            str(body.requester_email) if body.requester_email else cu.user.email
        ),
        requested_by=cu.id,
        requested_at=datetime.now(UTC),
        status="in_review",
        attachments=[a.model_dump() for a in body.attachments],
    )
    db.add(pr)
    await db.flush()
    await write_audit(
        db, action="project_request.create", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request",
        entity_id=str(pr.id), details={"folio": folio},
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr)


@router.get("", response_model=list[ProjectRequestRead])
async def list_requests(
    status: str | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    cu: CurrentUser = Depends(require_permission("admin.requests", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(ProjectRequest).where(ProjectRequest.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(ProjectRequest.status == status)
    if organization_id:
        stmt = stmt.where(ProjectRequest.organization_id == str(organization_id))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(ProjectRequest.title).like(like))
    rows = (
        await db.execute(stmt.order_by(ProjectRequest.requested_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()
    return [ProjectRequestRead.model_validate(r) for r in rows]


@router.get("/{request_id}", response_model=ProjectRequestRead)
async def get_request(
    request_id: UUID,
    cu: CurrentUser = Depends(require_permission("admin.requests", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    return ProjectRequestRead.model_validate(pr)


@router.patch("/{request_id}", response_model=ProjectRequestRead)
async def update_request(
    request_id: UUID,
    body: ProjectRequestUpdate,
    cu: CurrentUser = Depends(require_permission("admin.requests", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status not in {"in_review", "needs_info"}:
        raise conflict("No editable en este estado", code="STATE_TRANSITION")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(pr, f, v)
    await write_audit(
        db, action="project_request.update", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request", entity_id=str(pr.id),
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr)


@router.post("/{request_id}/review", response_model=ProjectRequestRead)
async def review_request(
    request_id: UUID,
    body: ReviewRequest,
    cu: CurrentUser = Depends(require_permission("admin.requests", "approve")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status not in {"in_review", "needs_info"}:
        raise conflict("Transición de estado inválida", code="STATE_TRANSITION")
    if body.decision in {"reject", "needs_info"} and not (body.comment and body.comment.strip()):
        raise validation_error("comment obligatorio para reject/needs_info")

    status_map = {"approve": "approved", "reject": "rejected", "needs_info": "needs_info"}
    pr.status = status_map[body.decision]
    pr.reviewed_by = cu.id
    pr.reviewed_at = datetime.now(UTC)
    pr.review_comment = body.comment
    await write_audit(
        db, action=f"project_request.{body.decision}", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request", entity_id=str(pr.id),
        details={"comment": body.comment},
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr)


@router.post("/{request_id}/resubmit", response_model=ProjectRequestRead)
async def resubmit_request(
    request_id: UUID,
    cu: CurrentUser = Depends(require_permission("admin.requests", "update")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status != "needs_info":
        raise conflict("Solo se puede re-someter si status=needs_info", code="STATE_TRANSITION")
    pr.status = "in_review"
    await write_audit(
        db, action="project_request.resubmit", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request", entity_id=str(pr.id),
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr)


@router.post("/{request_id}/create-project")
async def create_project_from_request(
    request_id: UUID,
    body: CreateProjectFromRequest,
    cu: CurrentUser = Depends(require_permission("admin.projects", "create")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.project import Project  # import diferido
    from app.models.project_charter import ProjectCharter

    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status != "approved":
        raise business_rule("Solo se puede crear proyecto desde una solicitud 'approved'")

    # Idempotencia
    if pr.project_id:
        return {"project_id": str(pr.project_id), "idempotent": True}

    folio = await next_folio(db, tenant_id=tenant_id, prefix="PRJ")
    project = Project(
        tenant_id=tenant_id,
        organization_id=pr.organization_id,
        business_unit_id=pr.business_unit_id,
        department_id=pr.department_id,
        folio=folio,
        name=pr.title,
        description=pr.description,
        sponsor=pr.sponsor,
        budget=pr.budget,
        phase="planning",
        pm_id=str(body.pm_id),
        request_id=pr.id,
    )
    db.add(project)
    await db.flush()
    pr.project_id = project.id

    # Auto-crear Charter pre-llenado desde solicitud (US-NEW-012).
    # Líder de negocio y líder técnico quedan en blanco para completar.
    charter = ProjectCharter(
        tenant_id=tenant_id,
        project_id=project.id,
        request_id=pr.id,
        project_name=project.name,
        description=pr.description,
        organization_id=pr.organization_id,
        business_unit_id=pr.business_unit_id,
        department_id=pr.department_id,
        sponsor=pr.sponsor,
        sponsor_email=pr.sponsor_email,
        pm_id=str(body.pm_id),
        project_type=None,
        priority=None,
        objective=pr.objective,
        scope=pr.scope,
        key_people=pr.key_people,
        benefits=pr.benefits,
        restrictions=None,
        risks_summary=None,
        created_by=cu.id,
    )
    db.add(charter)
    await db.flush()

    await write_audit(
        db, action="project.created_from_request", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(project.id),
        details={
            "request_id": str(pr.id),
            "folio": folio,
            "charter_id": str(charter.id),
        },
    )
    await db.commit()
    return {
        "project_id": str(project.id),
        "folio": folio,
        "charter_id": str(charter.id),
        "idempotent": False,
    }
