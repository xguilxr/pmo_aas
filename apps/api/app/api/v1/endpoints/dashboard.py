import csv
import io
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_request import ProjectRequest
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


async def _count(db: AsyncSession, stmt) -> int:
    return (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0


async def scoped_project_ids(
    cu: CurrentUser,
    db: AsyncSession,
    tenant_id: UUID,
    organization_id: UUID | None = None,
) -> list[str] | None:
    """Devuelve IDs de proyectos visibles al usuario según jerarquía de roles
    (US-015). `None` significa "sin restricción" (admin-equivalente: ve
    todo el tenant filtrable por org).

    Reglas:
      - Admin-equivalente (is_admin_equivalent = True, incluye Administrador y
        Senior PMO via DEC-005): ve todo el tenant. Aplica filtro por `org`
        si se pasa.
      - Project Manager / resto de roles: sólo proyectos donde es `pm_id`
        o está en `project_members`.
    """
    if cu.is_admin_equivalent:
        return None  # sin restricción adicional

    user_id = str(cu.id)
    # Proyectos donde es PM asignado
    pm_stmt = select(Project.id).where(
        Project.tenant_id == tenant_id,
        Project.deleted_at.is_(None),
        Project.pm_id == user_id,
    )
    if organization_id:
        pm_stmt = pm_stmt.where(Project.organization_id == str(organization_id))
    pm_ids = (await db.execute(pm_stmt)).scalars().all()

    # Proyectos donde es miembro (cualquier rol)
    mem_stmt = (
        select(Project.id)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            Project.tenant_id == tenant_id,
            Project.deleted_at.is_(None),
            ProjectMember.user_id == user_id,
        )
    )
    if organization_id:
        mem_stmt = mem_stmt.where(Project.organization_id == str(organization_id))
    member_ids = (await db.execute(mem_stmt)).scalars().all()

    combined = {str(i) for i in pm_ids} | {str(i) for i in member_ids}
    # Devolver lista; vacía = ningún proyecto visible
    return list(combined)


@router.get("/kpis")
async def kpis(
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    active_phases = ["planning", "execution", "support"]

    # Scoping por jerarquía (US-015): None = sin restricción (admin),
    # lista = sólo esos project_ids. Lista vacía = ningún proyecto visible.
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)
    role_restricted = role_ids is not None

    def scoped_projects():
        stmt = select(Project.id).where(
            Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
        )
        if organization_id:
            stmt = stmt.where(Project.organization_id == str(organization_id))
        if role_restricted:
            stmt = stmt.where(Project.id.in_(role_ids or ["__none__"]))
        return stmt

    # IDs de proyectos del scope actual para filtrar módulos
    scoped_ids_rows = (await db.execute(scoped_projects())).scalars().all()
    scoped_ids = [str(i) for i in scoped_ids_rows]

    active_projects = await _count(
        db,
        scoped_projects().where(Project.phase.in_(active_phases)),
    )
    req_stmt = select(ProjectRequest.id).where(
        ProjectRequest.tenant_id == tenant_id, ProjectRequest.status == "in_review"
    )
    if organization_id:
        req_stmt = req_stmt.where(
            ProjectRequest.organization_id == str(organization_id)
        )
    # Solicitudes: a los no-admins se les muestran solo las que ellos crearon
    if role_restricted:
        req_stmt = req_stmt.where(ProjectRequest.requested_by == str(cu.id))
    requests_in_review = await _count(db, req_stmt)

    # Conteos de módulos — se calculan si existen las tablas (EP006). Defaults seguros.
    open_risks = 0
    severe_risks = 0
    change_requests_in_review = 0
    open_issues = 0
    try:
        from app.models.modules import ChangeRequest, Issue, Risk  # type: ignore

        def scope_risks(stmt):
            if organization_id and scoped_ids:
                return stmt.where(Risk.project_id.in_(scoped_ids))
            if organization_id and not scoped_ids:
                return stmt.where(Risk.project_id.in_(["__none__"]))  # vacío
            return stmt

        open_risks = await _count(
            db,
            scope_risks(
                select(Risk.id).where(Risk.tenant_id == tenant_id, Risk.status != "closed")
            ),
        )
        severe_risks = await _count(
            db,
            scope_risks(
                select(Risk.id).where(
                    Risk.tenant_id == tenant_id,
                    Risk.status != "closed",
                    Risk.severity >= 13,
                )
            ),
        )

        cr_stmt = select(ChangeRequest.id).where(
            ChangeRequest.tenant_id == tenant_id,
            ChangeRequest.status == "in_review",
        )
        if organization_id:
            cr_stmt = cr_stmt.where(
                ChangeRequest.project_id.in_(scoped_ids or ["__none__"])
            )
        change_requests_in_review = await _count(db, cr_stmt)

        iss_stmt = select(Issue.id).where(
            Issue.tenant_id == tenant_id,
            Issue.status.in_(["open", "in_progress"]),
        )
        if organization_id:
            iss_stmt = iss_stmt.where(Issue.project_id.in_(scoped_ids or ["__none__"]))
        open_issues = await _count(db, iss_stmt)
    except Exception:
        pass

    budget_stmt = select(func.coalesce(func.sum(Project.budget), 0)).where(
        Project.tenant_id == tenant_id, Project.deleted_at.is_(None)
    )
    if organization_id:
        budget_stmt = budget_stmt.where(
            Project.organization_id == str(organization_id)
        )
    if role_restricted:
        budget_stmt = budget_stmt.where(Project.id.in_(role_ids or ["__none__"]))
    budget_total: Decimal | None = (await db.execute(budget_stmt)).scalar_one()

    progress_stmt = select(func.coalesce(func.avg(Project.progress), 0)).where(
        Project.tenant_id == tenant_id,
        Project.phase.in_(active_phases),
        Project.deleted_at.is_(None),
    )
    if organization_id:
        progress_stmt = progress_stmt.where(
            Project.organization_id == str(organization_id)
        )
    if role_restricted:
        progress_stmt = progress_stmt.where(Project.id.in_(role_ids or ["__none__"]))
    progress_avg = (await db.execute(progress_stmt)).scalar_one()

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
    organization_id: UUID | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)

    def scoped_where():
        base = [Project.tenant_id == tenant_id, Project.deleted_at.is_(None)]
        if organization_id:
            base.append(Project.organization_id == str(organization_id))
        if role_ids is not None:
            base.append(Project.id.in_(role_ids or ["__none__"]))
        return base

    rows = (
        await db.execute(
            select(Project.phase, func.count(Project.id))
            .where(*scoped_where())
            .group_by(Project.phase)
        )
    ).all()
    projects_by_phase = dict(rows)

    rows = (
        await db.execute(
            select(Project.phase, func.coalesce(func.avg(Project.progress), 0))
            .where(*scoped_where())
            .group_by(Project.phase)
        )
    ).all()
    progress_by_phase = {phase: float(avg) for phase, avg in rows}

    rows = (
        await db.execute(
            select(Project.type, func.coalesce(func.sum(Project.budget), 0))
            .where(*scoped_where())
            .group_by(Project.type)
        )
    ).all()
    budget_by_type = {t or "unspecified": float(b) for t, b in rows}

    rows = (
        await db.execute(
            select(Project.health_status, func.count(Project.id))
            .where(*scoped_where())
            .group_by(Project.health_status)
        )
    ).all()
    portfolio_health = dict(rows)

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
    cu: CurrentUser = Depends(require_authenticated()),
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

    # Scoping por jerarquía (US-015): Project Managers ven sólo lo suyo.
    role_ids = await scoped_project_ids(cu, db, tenant_id, organization_id)
    if role_ids is not None:
        stmt = stmt.where(Project.id.in_(role_ids or ["__none__"]))

    # Orden: rojo primero
    health_order = {"red": 0, "yellow": 1, "green": 2}
    projects = (await db.execute(stmt)).scalars().all()
    projects.sort(key=lambda p: health_order.get(p.health_status, 99))

    # Pre-cargar nombres de PM (BUG-003: columna PM Asignado).
    pm_ids = sorted({p.pm_id for p in projects if p.pm_id})
    pm_names: dict[str, str] = {}
    if pm_ids:
        rows = (
            await db.execute(
                select(User.id, User.full_name).where(User.id.in_(pm_ids))
            )
        ).all()
        pm_names = {str(i): n for i, n in rows}

    out = []
    for p in projects:
        pm_id = str(p.pm_id) if p.pm_id else None
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
                "pm_id": pm_id,
                "pm_name": pm_names.get(pm_id) if pm_id else None,
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
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    data = await plan_vs_actual(organization_id, program_id, phase, cu, db)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "folio", "name", "pm_name", "end_date", "budget_plan",
            "budget_actual", "progress_plan", "progress_actual", "health",
        ],
    )
    writer.writeheader()
    for row in data:
        writer.writerow({k: row.get(k, "") or "" for k in writer.fieldnames})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plan_vs_actual.csv"},
    )
