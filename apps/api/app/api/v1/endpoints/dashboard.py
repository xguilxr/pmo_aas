import csv
import io
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import forbidden
from app.db.session import get_db
from app.models.project import Project
from app.models.project_request import ProjectRequest

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


async def _count(db: AsyncSession, stmt) -> int:
    return (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0


@router.get("/kpis")
async def kpis(
    cu: CurrentUser = Depends(require_permission("dashboard", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    active_phases = ["planning", "execution", "support"]

    active_projects = await _count(
        db,
        select(Project.id).where(
            Project.tenant_id == tenant_id,
            Project.phase.in_(active_phases),
            Project.deleted_at.is_(None),
        ),
    )
    requests_in_review = await _count(
        db,
        select(ProjectRequest.id).where(
            ProjectRequest.tenant_id == tenant_id, ProjectRequest.status == "in_review"
        ),
    )

    # Conteos de módulos — se calculan si existen las tablas (EP006). Defaults seguros.
    open_risks = 0
    severe_risks = 0
    change_requests_in_review = 0
    open_issues = 0
    try:
        from app.models.modules import ChangeRequest, Issue, Risk  # type: ignore

        open_risks = await _count(
            db,
            select(Risk.id).where(Risk.tenant_id == tenant_id, Risk.status != "closed"),
        )
        severe_risks = await _count(
            db,
            select(Risk.id).where(
                Risk.tenant_id == tenant_id, Risk.status != "closed", Risk.severity >= 13
            ),
        )
        change_requests_in_review = await _count(
            db,
            select(ChangeRequest.id).where(
                ChangeRequest.tenant_id == tenant_id, ChangeRequest.status == "in_review"
            ),
        )
        open_issues = await _count(
            db,
            select(Issue.id).where(
                Issue.tenant_id == tenant_id, Issue.status.in_(["open", "in_progress"])
            ),
        )
    except Exception:
        pass

    budget_total: Decimal | None = (
        await db.execute(
            select(func.coalesce(func.sum(Project.budget), 0)).where(
                Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
            )
        )
    ).scalar_one()
    progress_avg = (
        await db.execute(
            select(func.coalesce(func.avg(Project.progress), 0)).where(
                Project.tenant_id == tenant_id,
                Project.phase.in_(active_phases),
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    return {
        "active_projects": active_projects,
        "requests_in_review": requests_in_review,
        "open_risks": open_risks,
        "severe_risks": severe_risks,
        "change_requests_in_review": change_requests_in_review,
        "open_issues": open_issues,
        "budget_total": float(budget_total or 0),
        "progress_avg": float(progress_avg or 0),
    }


@router.get("/charts")
async def charts(
    cu: CurrentUser = Depends(require_permission("dashboard", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)

    rows = (
        await db.execute(
            select(Project.phase, func.count(Project.id))
            .where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
            .group_by(Project.phase)
        )
    ).all()
    projects_by_phase = {phase: cnt for phase, cnt in rows}

    rows = (
        await db.execute(
            select(Project.phase, func.coalesce(func.avg(Project.progress), 0))
            .where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
            .group_by(Project.phase)
        )
    ).all()
    progress_by_phase = {phase: float(avg) for phase, avg in rows}

    rows = (
        await db.execute(
            select(Project.type, func.coalesce(func.sum(Project.budget), 0))
            .where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
            .group_by(Project.type)
        )
    ).all()
    budget_by_type = {t or "unspecified": float(b) for t, b in rows}

    rows = (
        await db.execute(
            select(Project.health_status, func.count(Project.id))
            .where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
            .group_by(Project.health_status)
        )
    ).all()
    portfolio_health = {status: cnt for status, cnt in rows}

    return {
        "projects_by_phase": projects_by_phase,
        "progress_by_phase": progress_by_phase,
        "budget_by_type": budget_by_type,
        "portfolio_health": portfolio_health,
    }


@router.get("/plan-vs-actual")
async def plan_vs_actual(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    phase: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("dashboard", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    stmt = select(Project).where(Project.tenant_id == tenant_id, Project.deleted_at.is_(None))
    if organization_id:
        stmt = stmt.where(Project.organization_id == str(organization_id))
    if program_id:
        stmt = stmt.where(Project.program_id == str(program_id))
    if phase:
        stmt = stmt.where(Project.phase == phase)

    # Orden: rojo primero
    health_order = {"red": 0, "yellow": 1, "green": 2}
    projects = (await db.execute(stmt)).scalars().all()
    projects.sort(key=lambda p: health_order.get(p.health_status, 99))

    out = []
    for p in projects:
        out.append(
            {
                "project_id": str(p.id),
                "folio": p.folio,
                "name": p.name,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "budget_plan": float(p.budget or 0),
                "budget_actual": float(p.actual_budget or 0),
                "progress_plan": _plan_progress_for(p),
                "progress_actual": int(p.progress or 0),
                "health": p.health_status,
            }
        )
    return out


def _plan_progress_for(p: Project) -> int:
    if not p.start_date or not p.end_date:
        return 0
    from datetime import date

    today = date.today()
    if today <= p.start_date:
        return 0
    if today >= p.end_date:
        return 100
    total = (p.end_date - p.start_date).days or 1
    elapsed = (today - p.start_date).days
    return max(0, min(100, int(elapsed * 100 / total)))


@router.get("/plan-vs-actual/export.csv")
async def plan_vs_actual_csv(
    organization_id: UUID | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    phase: str | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("dashboard", "read")),
    db: AsyncSession = Depends(get_db),
):
    data = await plan_vs_actual(organization_id, program_id, phase, cu, db)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "folio", "name", "end_date", "budget_plan", "budget_actual",
            "progress_plan", "progress_actual", "health",
        ],
    )
    writer.writeheader()
    for row in data:
        writer.writerow({k: row[k] for k in writer.fieldnames})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plan_vs_actual.csv"},
    )
