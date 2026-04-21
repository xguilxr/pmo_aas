"""US-052 — vistas cross-tenant de RAID/Cambios/Minutas/Reportes.

Los endpoints existentes en `modules.py` y `reports.py` son project-scoped
(`/projects/{id}/<recurso>`). Estas rutas agregan listado a nivel tenant
con filtros por organization_id, program_id y project_id, para las
páginas `/admin/raid`, `/admin/changes`, `/admin/minutes` y
`/admin/reports`.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.api.v1.endpoints.reports import ReportRead
from app.core.errors import forbidden
from app.db.session import get_db
from app.models.ai import Report
from app.models.modules import (
    ChangeRequest,
    Issue,
    MeetingMinute,
    Risk,
)
from app.models.project import Project
from app.schemas.modules import (
    ChangeRequestRead,
    IssueRead,
    MeetingMinuteRead,
    RiskRead,
)

router = APIRouter(prefix="/tenant", tags=["tenant_cross"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


def _project_scope(
    stmt,
    project_model_rel,
    tenant_id: UUID,
    organization_id: UUID | None,
    program_id: UUID | None,
    project_id: UUID | None,
):
    """Aplica filtros cruzados (tenant, org, programa, proyecto) usando el
    join implícito con `Project`."""
    stmt = stmt.join(Project, Project.id == project_model_rel).where(
        Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
    )
    if organization_id is not None:
        stmt = stmt.where(Project.organization_id == str(organization_id))
    if program_id is not None:
        stmt = stmt.where(Project.program_id == str(program_id))
    if project_id is not None:
        stmt = stmt.where(Project.id == str(project_id))
    return stmt


@router.get("/risks", response_model=list[RiskRead])
async def list_tenant_risks(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("risks", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Risk).where(Risk.deleted_at.is_(None))
    stmt = _project_scope(
        stmt, Risk.project_id, tenant_id, organization_id, program_id, project_id
    )
    rows = (
        await db.execute(stmt.order_by(Risk.severity.desc().nullslast()))
    ).scalars().all()
    return [RiskRead.model_validate(r) for r in rows]


@router.get("/issues", response_model=list[IssueRead])
async def list_tenant_issues(
    type: str | None = Query(default=None, description="action|issue|decision"),
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("issues", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Issue).where(Issue.deleted_at.is_(None))
    stmt = _project_scope(
        stmt, Issue.project_id, tenant_id, organization_id, program_id, project_id
    )
    if type:
        stmt = stmt.where(Issue.type == type)
    rows = (
        await db.execute(stmt.order_by(Issue.created_at.desc()))
    ).scalars().all()
    return [IssueRead.model_validate(r) for r in rows]


@router.get("/change-requests", response_model=list[ChangeRequestRead])
async def list_tenant_changes(
    status: str | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("change_requests", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(ChangeRequest).where(ChangeRequest.deleted_at.is_(None))
    stmt = _project_scope(
        stmt,
        ChangeRequest.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
    )
    if status:
        stmt = stmt.where(ChangeRequest.status == status)
    rows = (
        await db.execute(stmt.order_by(ChangeRequest.created_at.desc()))
    ).scalars().all()
    return [ChangeRequestRead.model_validate(r) for r in rows]


@router.get("/meeting-minutes", response_model=list[MeetingMinuteRead])
async def list_tenant_minutes(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("minutes", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(MeetingMinute)
    stmt = _project_scope(
        stmt,
        MeetingMinute.project_id,
        tenant_id,
        organization_id,
        program_id,
        project_id,
    )
    rows = (
        await db.execute(stmt.order_by(MeetingMinute.meeting_date.desc()))
    ).scalars().all()
    return [MeetingMinuteRead.model_validate(r) for r in rows]


@router.get("/reports", response_model=list[ReportRead])
async def list_tenant_reports(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("reports", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Report)
    stmt = _project_scope(
        stmt, Report.project_id, tenant_id, organization_id, program_id, project_id
    )
    rows = (
        await db.execute(stmt.order_by(Report.created_at.desc()))
    ).scalars().all()
    return [ReportRead.model_validate(r) for r in rows]
