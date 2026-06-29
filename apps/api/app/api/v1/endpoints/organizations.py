from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_authenticated, require_capability
from app.api.v1.endpoints.dashboard import scoped_project_ids
from app.core.errors import business_rule, conflict, forbidden, not_found
from app.core.hard_delete import confirm_slug, ensure_confirm, ensure_inactive
from app.core.visibility import get_user_visibility
from app.db.session import get_db
from app.models.modules import Risk
from app.models.organization import BusinessUnit, Department, Organization, Program
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.models.project_member import ProjectMember
from app.models.project_request import ProjectRequest
from app.models.user import User
from app.schemas.hard_delete import HardDeletePreview
from app.schemas.organization import (
    BusinessUnitCreate,
    BusinessUnitRead,
    BusinessUnitUpdate,
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    OrganizationCreate,
    OrganizationPanel,
    OrganizationPanelDetail,
    OrganizationPanelHealth,
    OrganizationRead,
    OrganizationUpdate,
    OrgPanelBusinessUnit,
    OrgPanelDepartment,
    OrgPanelProgram,
    OrgPanelProject,
    OrgPanelUser,
    ProgramCreate,
    ProgramRead,
    ProgramSummary,
    ProgramSummaryProject,
    ProgramSummaryRisk,
    ProgramUpdate,
)
from app.services.audit import write_audit
from app.services.pdf_renderer import render_pdf
from app.services.reports.scoped_status import build_scope_status_context

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _ensure_tenant(cu: CurrentUser) -> UUID:
    # BUG-056: superadmin post `joinAsAdmin` tiene `user.tenant_id=None`
    # pero un `active_tenant_id` en el JWT — usar ese como tenant
    # efectivo para que las pantallas /admin/organizations funcionen.
    tid = cu.effective_tenant_id
    if tid is None:
        raise forbidden(detail="Acción no disponible para super admin sin tenant activo")
    return tid


@router.get("/panels", response_model=list[OrganizationPanel])
async def list_org_panels(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Listado de organizaciones con métricas agregadas (US-006).

    Ejecuta queries paralelas de counts por organización para evitar N+1.
    """
    tenant_id = _ensure_tenant(cu)
    base = select(Organization).where(Organization.tenant_id == tenant_id)
    if not cu.is_admin_equivalent:
        visibility = await get_user_visibility(cu.user, db)
        if not visibility.unrestricted:
            if not visibility.org_ids:
                return []
            base = base.where(Organization.id.in_(visibility.org_ids))
    if q:
        base = base.where(func.lower(Organization.name).like(f"%{q.lower()}%"))
    if is_active is not None:
        base = base.where(Organization.is_active == is_active)
    orgs = (await db.execute(base.order_by(Organization.name))).scalars().all()
    if not orgs:
        return []

    org_ids = [o.id for o in orgs]

    bu_counts_rows = (
        await db.execute(
            select(BusinessUnit.organization_id, func.count(BusinessUnit.id))
            .where(
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.organization_id.in_(org_ids),
                BusinessUnit.deleted_at.is_(None),
                BusinessUnit.is_active.is_(True),
            )
            .group_by(BusinessUnit.organization_id)
        )
    ).all()
    bu_counts: dict[str, int] = {str(o): n for o, n in bu_counts_rows}

    dept_counts_rows = (
        await db.execute(
            select(BusinessUnit.organization_id, func.count(Department.id))
            .join(Department, Department.business_unit_id == BusinessUnit.id)
            .where(
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.organization_id.in_(org_ids),
                Department.deleted_at.is_(None),
                Department.is_active.is_(True),
            )
            .group_by(BusinessUnit.organization_id)
        )
    ).all()
    dept_counts: dict[str, int] = {str(o): n for o, n in dept_counts_rows}

    prog_counts_rows = (
        await db.execute(
            select(Program.organization_id, func.count(Program.id))
            .where(
                Program.tenant_id == tenant_id,
                Program.organization_id.in_(org_ids),
                Program.is_active.is_(True),
            )
            .group_by(Program.organization_id)
        )
    ).all()
    prog_counts: dict[str, int] = {str(o): n for o, n in prog_counts_rows}

    proj_rows = (
        await db.execute(
            select(
                Project.organization_id, Project.health_status, func.count(Project.id)
            )
            .where(
                Project.tenant_id == tenant_id,
                Project.organization_id.in_(org_ids),
                Project.deleted_at.is_(None),
                Project.phase != "closed",
            )
            .group_by(Project.organization_id, Project.health_status)
        )
    ).all()
    active_projects: dict[str, int] = {}
    health_map: dict[str, dict[str, int]] = {}
    for org_id, health, n in proj_rows:
        k = str(org_id)
        active_projects[k] = active_projects.get(k, 0) + int(n)
        hm = health_map.setdefault(k, {"green": 0, "yellow": 0, "red": 0})
        if health in hm:
            hm[health] += int(n)

    panels: list[OrganizationPanel] = []
    for o in orgs:
        oid = str(o.id)
        panels.append(
            OrganizationPanel(
                id=o.id,
                name=o.name,
                logo_url=o.logo_url,
                industry=o.industry,
                country=o.country,
                is_active=o.is_active,
                business_unit_count=bu_counts.get(oid, 0),
                department_count=dept_counts.get(oid, 0),
                program_count=prog_counts.get(oid, 0),
                active_project_count=active_projects.get(oid, 0),
                portfolio_health=OrganizationPanelHealth(**health_map.get(oid, {})),
            )
        )
    return panels


@router.get("", response_model=list[OrganizationRead])
async def list_orgs(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    stmt = select(Organization).where(Organization.tenant_id == tenant_id)
    if not cu.is_admin_equivalent:
        visibility = await get_user_visibility(cu.user, db)
        if not visibility.unrestricted:
            if not visibility.org_ids:
                return []
            stmt = stmt.where(Organization.id.in_(visibility.org_ids))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Organization.name).like(like))
    if is_active is not None:
        stmt = stmt.where(Organization.is_active == is_active)
    rows = (await db.execute(stmt.order_by(Organization.name))).scalars().all()
    return [OrganizationRead.model_validate(o) for o in rows]


@router.post("", response_model=OrganizationRead, status_code=201)
async def create_org(
    body: OrganizationCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    existing = (
        await db.execute(
            select(Organization).where(Organization.tenant_id == tenant_id, Organization.name == body.name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise conflict("Organización con ese nombre ya existe")
    org = Organization(tenant_id=tenant_id, **body.model_dump())
    db.add(org)
    await db.flush()
    await write_audit(
        db, action="organization.create", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="organization", entity_id=str(org.id),
        details={"name": body.name},
    )
    await db.commit()
    return OrganizationRead.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_org(
    org_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(Organization.id == str(org_id), Organization.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    return OrganizationRead.model_validate(org)


@router.get("/{org_id}/panel", response_model=OrganizationPanelDetail)
async def get_org_panel(
    org_id: UUID,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Panel read-only de recursos reales de la organización (US-033).

    Cualquier usuario autenticado del tenant puede verlo. Cross-tenant → 404.
    El botón "Editar" en la UI se muestra sólo a admins; esta API no hace
    esa distinción — expone todo como data, y la edición vive en otros
    endpoints con permisos más estrictos.
    """
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(org_id),
                Organization.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")

    bus = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.organization_id == str(org_id),
                BusinessUnit.deleted_at.is_(None),
            ).order_by(BusinessUnit.name)
        )
    ).scalars().all()
    bu_ids = [bu.id for bu in bus]
    depts_rows = (
        await db.execute(
            select(Department).where(
                Department.tenant_id == tenant_id,
                Department.business_unit_id.in_(bu_ids) if bu_ids else Department.id.is_(None),
                Department.deleted_at.is_(None),
            ).order_by(Department.name)
        )
    ).scalars().all()
    depts_by_bu: dict[str, list[Department]] = {}
    for d in depts_rows:
        depts_by_bu.setdefault(str(d.business_unit_id), []).append(d)

    # US-168: visibility filter for PM users
    panel_visibility = None
    if not cu.is_admin_equivalent:
        panel_visibility = await get_user_visibility(cu.user, db)

    prog_stmt = select(Program).where(
        Program.tenant_id == tenant_id,
        Program.organization_id == str(org_id),
    )
    if panel_visibility and not panel_visibility.unrestricted:
        if not panel_visibility.program_ids:
            prog_stmt = prog_stmt.where(Program.id.is_(None))  # empty
        else:
            prog_stmt = prog_stmt.where(Program.id.in_(panel_visibility.program_ids))
    programs = (await db.execute(prog_stmt.order_by(Program.name))).scalars().all()
    # Count active projects per program
    prog_ids = [p.id for p in programs]
    prog_proj_counts: dict[str, int] = {}
    if prog_ids:
        rows = (
            await db.execute(
                select(Project.program_id, func.count(Project.id))
                .where(
                    Project.tenant_id == tenant_id,
                    Project.program_id.in_(prog_ids),
                    Project.deleted_at.is_(None),
                    Project.phase != "closed",
                )
                .group_by(Project.program_id)
            )
        ).all()
        prog_proj_counts = {str(pid): int(n) for pid, n in rows}

    proj_stmt = select(Project).where(
        Project.tenant_id == tenant_id,
        Project.organization_id == str(org_id),
        Project.deleted_at.is_(None),
    )
    if panel_visibility and not panel_visibility.unrestricted:
        if not panel_visibility.project_ids:
            proj_stmt = proj_stmt.where(Project.id.is_(None))  # empty
        else:
            proj_stmt = proj_stmt.where(Project.id.in_(panel_visibility.project_ids))
    projects = (await db.execute(proj_stmt.order_by(Project.name))).scalars().all()
    pm_ids = {p.pm_id for p in projects if p.pm_id}
    pm_rows = (
        await db.execute(
            select(User.id, User.full_name, User.email).where(User.id.in_(pm_ids))
        )
    ).all() if pm_ids else []
    pm_map: dict[str, tuple[str | None, str | None]] = {
        str(uid): (name, email) for uid, name, email in pm_rows
    }

    # Users: PMs + project members de cualquier proyecto de la org
    user_role: dict[str, str] = {}
    for p in projects:
        if p.pm_id:
            user_role[str(p.pm_id)] = "pm"
    project_ids = [p.id for p in projects]
    if project_ids:
        member_rows = (
            await db.execute(
                select(ProjectMember.user_id, ProjectMember.role_in_project)
                .where(ProjectMember.project_id.in_(project_ids))
            )
        ).all()
        for uid, rip in member_rows:
            key = str(uid)
            if key not in user_role:
                user_role[key] = rip or "team"
    users_list: list[OrgPanelUser] = []
    if user_role:
        rows = (
            await db.execute(
                select(User.id, User.full_name, User.email).where(
                    User.id.in_(list(user_role.keys()))
                )
            )
        ).all()
        rows_sorted = sorted(rows, key=lambda r: (r[1] or r[2] or "").lower())
        users_list = [
            OrgPanelUser(
                id=r[0], full_name=r[1], email=r[2], role=user_role[str(r[0])],
            )
            for r in rows_sorted
        ]

    return OrganizationPanelDetail(
        id=org.id,
        name=org.name,
        reason_social=org.reason_social,
        industry=org.industry,
        country=org.country,
        contact_email=org.contact_email,
        logo_url=org.logo_url,
        client_logo_url=org.client_logo_url,
        is_active=org.is_active,
        business_units=[
            OrgPanelBusinessUnit(
                id=bu.id,
                name=bu.name,
                description=bu.description,
                is_active=bu.is_active,
                departments=[
                    OrgPanelDepartment(
                        id=d.id,
                        business_unit_id=d.business_unit_id,
                        name=d.name,
                        is_active=d.is_active,
                    )
                    for d in depts_by_bu.get(str(bu.id), [])
                ],
            )
            for bu in bus
        ],
        programs=[
            OrgPanelProgram(
                id=p.id,
                name=p.name,
                description=p.description,
                is_active=p.is_active,
                active_project_count=prog_proj_counts.get(str(p.id), 0),
            )
            for p in programs
        ],
        projects=[
            OrgPanelProject(
                id=p.id,
                folio=p.folio,
                name=p.name,
                phase=p.phase,
                health_status=p.health_status,
                program_id=p.program_id,
                pm_id=p.pm_id,
                pm_name=pm_map.get(str(p.pm_id), (None, None))[0] if p.pm_id else None,
            )
            for p in projects
        ],
        users=users_list,
    )


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_org(
    org_id: UUID,
    body: OrganizationUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(Organization.id == str(org_id), Organization.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    await write_audit(
        db, action="organization.update", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="organization", entity_id=str(org.id),
    )
    await db.commit()
    return OrganizationRead.model_validate(org)


@router.delete("/{org_id}", status_code=204)
async def delete_org(
    org_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(Organization.id == str(org_id), Organization.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    org.is_active = False
    await write_audit(
        db, action="organization.delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="organization", entity_id=str(org.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# -- Programs ----
programs_router = APIRouter(prefix="/programs", tags=["programs"])


@programs_router.get("", response_model=list[ProgramRead])
async def list_programs(
    organization_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    stmt = select(Program).where(Program.tenant_id == tenant_id)
    if not cu.is_admin_equivalent:
        visibility = await get_user_visibility(cu.user, db)
        if not visibility.unrestricted:
            if not visibility.program_ids:
                return []
            stmt = stmt.where(Program.id.in_(visibility.program_ids))
    if organization_id:
        stmt = stmt.where(Program.organization_id == str(organization_id))
    if is_active is not None:
        stmt = stmt.where(Program.is_active == is_active)
    rows = (await db.execute(stmt.order_by(Program.name))).scalars().all()
    return [ProgramRead.model_validate(p) for p in rows]


@programs_router.post("", response_model=ProgramRead, status_code=201)
async def create_program(
    body: ProgramCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(body.organization_id), Organization.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise business_rule("La organización no existe o no pertenece al tenant")
    payload = body.model_dump()
    payload["organization_id"] = str(payload["organization_id"])
    prog = Program(tenant_id=tenant_id, **payload)
    db.add(prog)
    await db.flush()
    await write_audit(
        db, action="program.create", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="program", entity_id=str(prog.id),
        details={"name": body.name, "organization_id": str(body.organization_id)},
    )
    await db.commit()
    return ProgramRead.model_validate(prog)


@programs_router.get("/{program_id}/summary", response_model=ProgramSummary)
async def program_summary(
    program_id: UUID,
    cu: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumen agregado del programa (US-034).

    Auth-only; cross-tenant → 404. Devuelve info del programa + agregados
    (counts por fase y salud, presupuestos), lista de proyectos y top 10
    riesgos con severidad >= 13.
    """
    tenant_id = _ensure_tenant(cu)
    prog = (
        await db.execute(
            select(Program).where(
                Program.id == str(program_id), Program.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if prog is None:
        raise not_found("Programa")
    org = (
        await db.execute(
            select(Organization).where(Organization.id == prog.organization_id)
        )
    ).scalar_one_or_none()

    sum_proj_stmt = select(Project).where(
        Project.tenant_id == tenant_id,
        Project.program_id == str(program_id),
        Project.deleted_at.is_(None),
    )
    if not cu.is_admin_equivalent:
        sum_visibility = await get_user_visibility(cu.user, db)
        if not sum_visibility.unrestricted:
            if not sum_visibility.project_ids:
                sum_proj_stmt = sum_proj_stmt.where(Project.id.is_(None))  # empty
            else:
                sum_proj_stmt = sum_proj_stmt.where(Project.id.in_(sum_visibility.project_ids))
    projects = (await db.execute(sum_proj_stmt.order_by(Project.name))).scalars().all()
    pm_ids = {p.pm_id for p in projects if p.pm_id}
    pm_rows = (
        await db.execute(
            select(User.id, User.full_name).where(User.id.in_(pm_ids))
        )
    ).all() if pm_ids else []
    pm_map = {str(uid): name for uid, name in pm_rows}

    total = len(projects)
    active = sum(1 for p in projects if p.phase != "closed")
    closed = sum(1 for p in projects if p.phase == "closed")
    at_risk = sum(1 for p in projects if p.health_status != "green" and p.phase != "closed")
    health_counts = {"green": 0, "yellow": 0, "red": 0}
    for p in projects:
        if p.phase == "closed":
            continue
        if p.health_status in health_counts:
            health_counts[p.health_status] += 1
    budget_planned = float(sum((p.budget or 0) for p in projects))
    budget_actual = float(sum((p.actual_budget or 0) for p in projects))

    project_ids = [p.id for p in projects]
    top_risks: list[ProgramSummaryRisk] = []
    if project_ids:
        risk_rows = (
            await db.execute(
                select(Risk).where(
                    Risk.tenant_id == tenant_id,
                    Risk.project_id.in_(project_ids),
                    Risk.deleted_at.is_(None),
                    Risk.severity.isnot(None),
                    Risk.severity >= 13,
                    Risk.status != "resolved",  # US-179: terminal unificado.
                ).order_by(Risk.severity.desc()).limit(10)
            )
        ).scalars().all()
        proj_name_map = {p.id: p.name for p in projects}
        top_risks = [
            ProgramSummaryRisk(
                id=r.id,
                project_id=r.project_id,
                project_name=proj_name_map.get(r.project_id),
                folio=r.folio,
                title=r.title,
                severity=r.severity,
                status=r.status,
            )
            for r in risk_rows
        ]

    return ProgramSummary(
        id=prog.id,
        name=prog.name,
        description=prog.description,
        organization_id=prog.organization_id,
        organization_name=org.name if org else None,
        is_active=prog.is_active,
        start_date=prog.start_date,
        end_date=prog.end_date,
        project_total=total,
        project_active=active,
        project_at_risk=at_risk,
        project_closed=closed,
        health=OrganizationPanelHealth(**health_counts),
        budget_planned=budget_planned,
        budget_actual=budget_actual,
        projects=[
            ProgramSummaryProject(
                id=p.id,
                folio=p.folio,
                name=p.name,
                phase=p.phase,
                health_status=p.health_status,
                pm_id=p.pm_id,
                pm_name=pm_map.get(str(p.pm_id)) if p.pm_id else None,
                progress=p.progress or 0,
                budget=float(p.budget or 0),
                actual_budget=float(p.actual_budget or 0),
            )
            for p in projects
        ],
        top_risks=top_risks,
    )


@programs_router.patch("/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: UUID,
    body: ProgramUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    prog = (
        await db.execute(
            select(Program).where(Program.id == str(program_id), Program.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if prog is None:
        raise not_found("Programa")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(prog, f, v)
    await write_audit(
        db, action="program.update", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="program", entity_id=str(prog.id),
    )
    await db.commit()
    return ProgramRead.model_validate(prog)


@programs_router.delete("/{program_id}", status_code=204)
async def delete_program(
    program_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    prog = (
        await db.execute(
            select(Program).where(Program.id == str(program_id), Program.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if prog is None:
        raise not_found("Programa")
    prog.is_active = False
    await write_audit(
        db, action="program.delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="program", entity_id=str(prog.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# -- Business Units (US-003) ----
business_units_router = APIRouter(tags=["business-units"])


def _bu_active_filter(stmt):
    return stmt.where(BusinessUnit.deleted_at.is_(None))


def _get_org_or_404(db_result):
    org = db_result.scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    return org


@business_units_router.post(
    "/organizations/{org_id}/business-units",
    response_model=BusinessUnitRead,
    status_code=201,
)
async def create_business_unit(
    org_id: UUID,
    body: BusinessUnitCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = _get_org_or_404(
        await db.execute(
            select(Organization).where(
                Organization.id == str(org_id), Organization.tenant_id == tenant_id
            )
        )
    )
    existing = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.organization_id == org.id,
                BusinessUnit.name == body.name,
                BusinessUnit.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise conflict("Unidad de negocio con ese nombre ya existe en la organización")
    bu = BusinessUnit(
        tenant_id=tenant_id,
        organization_id=str(org.id),
        created_by=str(cu.id),
        **body.model_dump(),
    )
    db.add(bu)
    await db.flush()
    await write_audit(
        db, action="business_unit.create", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="business_unit", entity_id=str(bu.id),
        details={"name": body.name, "organization_id": str(org.id)},
    )
    await db.commit()
    return BusinessUnitRead.model_validate(bu)


@business_units_router.get(
    "/organizations/{org_id}/business-units",
    response_model=list[BusinessUnitRead],
)
async def list_business_units(
    org_id: UUID,
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    _get_org_or_404(
        await db.execute(
            select(Organization).where(
                Organization.id == str(org_id), Organization.tenant_id == tenant_id
            )
        )
    )
    stmt = _bu_active_filter(
        select(BusinessUnit).where(
            BusinessUnit.tenant_id == tenant_id,
            BusinessUnit.organization_id == str(org_id),
        )
    )
    if q:
        stmt = stmt.where(func.lower(BusinessUnit.name).like(f"%{q.lower()}%"))
    if is_active is not None:
        stmt = stmt.where(BusinessUnit.is_active == is_active)
    rows = (await db.execute(stmt.order_by(BusinessUnit.name))).scalars().all()
    return [BusinessUnitRead.model_validate(b) for b in rows]


@business_units_router.get(
    "/business-units/{bu_id}", response_model=BusinessUnitRead
)
async def get_business_unit(
    bu_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    bu = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if bu is None:
        raise not_found("Unidad de negocio")
    return BusinessUnitRead.model_validate(bu)


@business_units_router.patch(
    "/business-units/{bu_id}", response_model=BusinessUnitRead
)
async def update_business_unit(
    bu_id: UUID,
    body: BusinessUnitUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    bu = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if bu is None:
        raise not_found("Unidad de negocio")
    new_name = body.name
    if new_name and new_name != bu.name:
        clash = (
            await db.execute(
                select(BusinessUnit).where(
                    BusinessUnit.tenant_id == tenant_id,
                    BusinessUnit.organization_id == bu.organization_id,
                    BusinessUnit.name == new_name,
                    BusinessUnit.id != bu.id,
                    BusinessUnit.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise conflict("Unidad de negocio con ese nombre ya existe en la organización")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(bu, field, value)
    await write_audit(
        db, action="business_unit.update", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="business_unit", entity_id=str(bu.id),
    )
    await db.commit()
    return BusinessUnitRead.model_validate(bu)


@business_units_router.delete("/business-units/{bu_id}", status_code=204)
async def delete_business_unit(
    bu_id: UUID,
    force: bool = Query(default=False),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    bu = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if bu is None:
        raise not_found("Unidad de negocio")
    active_depts = (
        await db.execute(
            select(Department.id, Department.name).where(
                Department.tenant_id == tenant_id,
                Department.business_unit_id == bu.id,
                Department.deleted_at.is_(None),
                Department.is_active.is_(True),
            )
        )
    ).all()
    if active_depts and not force:
        raise business_rule(
            "La unidad de negocio tiene departamentos activos. "
            "Use force=true para soft-delete con cascada lógica.",
            code="BU_HAS_ACTIVE_DEPARTMENTS",
        )
    bu.is_active = False
    from datetime import datetime

    bu.deleted_at = datetime.now(UTC)
    if force:
        for dept_id, _ in active_depts:
            dept = (
                await db.execute(select(Department).where(Department.id == dept_id))
            ).scalar_one()
            dept.is_active = False
            dept.deleted_at = bu.deleted_at
    await write_audit(
        db, action="business_unit.delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="business_unit", entity_id=str(bu.id),
        details={"force": force, "cascaded_departments": [d for _, d in active_depts]},
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# -- Departments (US-004) ----
departments_router = APIRouter(tags=["departments"])


def _get_bu_or_404(db_result):
    bu = db_result.scalar_one_or_none()
    if bu is None:
        raise not_found("Unidad de negocio")
    return bu


@departments_router.post(
    "/business-units/{bu_id}/departments",
    response_model=DepartmentRead,
    status_code=201,
)
async def create_department(
    bu_id: UUID,
    body: DepartmentCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    bu = _get_bu_or_404(
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.deleted_at.is_(None),
            )
        )
    )
    existing = (
        await db.execute(
            select(Department).where(
                Department.tenant_id == tenant_id,
                Department.business_unit_id == bu.id,
                Department.name == body.name,
                Department.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise conflict("Departamento con ese nombre ya existe en la unidad de negocio")
    dept = Department(
        tenant_id=tenant_id,
        business_unit_id=str(bu.id),
        created_by=str(cu.id),
        **body.model_dump(),
    )
    db.add(dept)
    await db.flush()
    await write_audit(
        db, action="department.create", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="department", entity_id=str(dept.id),
        details={"name": body.name, "business_unit_id": str(bu.id)},
    )
    await db.commit()
    return DepartmentRead.model_validate(dept)


@departments_router.get(
    "/business-units/{bu_id}/departments",
    response_model=list[DepartmentRead],
)
async def list_departments(
    bu_id: UUID,
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    _get_bu_or_404(
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.deleted_at.is_(None),
            )
        )
    )
    stmt = select(Department).where(
        Department.tenant_id == tenant_id,
        Department.business_unit_id == str(bu_id),
        Department.deleted_at.is_(None),
    )
    if q:
        stmt = stmt.where(func.lower(Department.name).like(f"%{q.lower()}%"))
    if is_active is not None:
        stmt = stmt.where(Department.is_active == is_active)
    rows = (await db.execute(stmt.order_by(Department.name))).scalars().all()
    return [DepartmentRead.model_validate(d) for d in rows]


@departments_router.get(
    "/departments/{dept_id}", response_model=DepartmentRead
)
async def get_department(
    dept_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    dept = (
        await db.execute(
            select(Department).where(
                Department.id == str(dept_id),
                Department.tenant_id == tenant_id,
                Department.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dept is None:
        raise not_found("Departamento")
    return DepartmentRead.model_validate(dept)


@departments_router.patch(
    "/departments/{dept_id}", response_model=DepartmentRead
)
async def update_department(
    dept_id: UUID,
    body: DepartmentUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    dept = (
        await db.execute(
            select(Department).where(
                Department.id == str(dept_id),
                Department.tenant_id == tenant_id,
                Department.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dept is None:
        raise not_found("Departamento")
    new_name = body.name
    if new_name and new_name != dept.name:
        clash = (
            await db.execute(
                select(Department).where(
                    Department.tenant_id == tenant_id,
                    Department.business_unit_id == dept.business_unit_id,
                    Department.name == new_name,
                    Department.id != dept.id,
                    Department.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise conflict("Departamento con ese nombre ya existe en la unidad de negocio")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(dept, field, value)
    await write_audit(
        db, action="department.update", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="department", entity_id=str(dept.id),
    )
    await db.commit()
    return DepartmentRead.model_validate(dept)


@departments_router.delete("/departments/{dept_id}", status_code=204)
async def delete_department(
    dept_id: UUID,
    force: bool = Query(default=False),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    dept = (
        await db.execute(
            select(Department).where(
                Department.id == str(dept_id),
                Department.tenant_id == tenant_id,
                Department.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dept is None:
        raise not_found("Departamento")

    active_programs = (
        await db.execute(
            select(func.count(Program.id)).where(
                Program.tenant_id == tenant_id,
                Program.department_id == dept.id,
                Program.is_active.is_(True),
            )
        )
    ).scalar_one()
    active_projects = (
        await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == tenant_id,
                Project.department_id == dept.id,
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    if (active_programs or active_projects) and not force:
        raise business_rule(
            "El departamento tiene programas o proyectos activos. "
            f"Programas: {active_programs}, Proyectos: {active_projects}. "
            "Use force=true para soft-delete.",
            code="DEPT_HAS_ACTIVE_CHILDREN",
        )

    from datetime import datetime

    dept.is_active = False
    dept.deleted_at = datetime.now(UTC)
    await write_audit(
        db, action="department.delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="department", entity_id=str(dept.id),
        details={
            "force": force,
            "active_programs": active_programs,
            "active_projects": active_projects,
        },
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# =============================================================================
# US-088 — Hard delete (segundo paso) para org/program/BU/dept
# =============================================================================
# Patrón: requiere is_active=False + ?confirm=<slug> exacto.
# Cascada explícita por entidad (FK CASCADE no cubre todos los casos — ver
# ADR-017). Cada endpoint loguea action `<entity>.hard_delete` con el conteo
# real de filas borradas.
# -----------------------------------------------------------------------------


async def _project_count_for_program(db: AsyncSession, tenant_id, program_id: str) -> int:
    return (
        await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == tenant_id, Project.program_id == program_id
            )
        )
    ).scalar_one()


async def _delete_projects_in(db: AsyncSession, tenant_id, where) -> int:
    """Hard-delete físico de Projects que matcheen el predicado.

    Devuelve count borrado. Itera con `db.delete()` para que SQLAlchemy
    dispare las CASCADE de modules/charter/tasks/areas/members/scheduled.
    """
    rows = (
        await db.execute(
            select(Project).where(Project.tenant_id == tenant_id, where)
        )
    ).scalars().all()
    count = len(rows)
    for p in rows:
        await db.delete(p)
    await db.flush()
    return count


@programs_router.get(
    "/{program_id}/hard-delete-preview", response_model=HardDeletePreview
)
async def preview_hard_delete_program(
    program_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    prog = (
        await db.execute(
            select(Program).where(
                Program.id == str(program_id), Program.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if prog is None:
        raise not_found("Programa")
    projects = await _project_count_for_program(db, tenant_id, prog.id)
    return HardDeletePreview(
        entity_type="program",
        entity_id=str(prog.id),
        entity_name=prog.name,
        is_active=prog.is_active,
        confirm_slug=confirm_slug("program", prog.name),
        cascades={"projects": projects},
    )


@programs_router.delete("/{program_id}/permanent", status_code=204)
async def hard_delete_program(
    program_id: UUID,
    confirm: str = Query(...),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    prog = (
        await db.execute(
            select(Program).where(
                Program.id == str(program_id), Program.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if prog is None:
        raise not_found("Programa")
    ensure_inactive(prog.is_active, "Programa")
    projects = await _project_count_for_program(db, tenant_id, prog.id)
    preview = {"projects": projects}
    ensure_confirm(confirm, confirm_slug("program", prog.name), preview=preview)

    deleted_projects = await _delete_projects_in(
        db, tenant_id, Project.program_id == prog.id
    )
    await db.delete(prog)
    await write_audit(
        db, action="program.hard_delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="program",
        entity_id=str(prog.id),
        details={"name": prog.name, "cascades": {"projects": deleted_projects}},
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get(
    "/{org_id}/hard-delete-preview", response_model=HardDeletePreview
)
async def preview_hard_delete_org(
    org_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(org_id), Organization.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    bu = (await db.execute(
        select(func.count(BusinessUnit.id)).where(
            BusinessUnit.tenant_id == tenant_id, BusinessUnit.organization_id == org.id
        )
    )).scalar_one()
    progs = (await db.execute(
        select(func.count(Program.id)).where(
            Program.tenant_id == tenant_id, Program.organization_id == org.id
        )
    )).scalar_one()
    projects = (await db.execute(
        select(func.count(Project.id)).where(
            Project.tenant_id == tenant_id, Project.organization_id == org.id
        )
    )).scalar_one()
    requests = (await db.execute(
        select(func.count(ProjectRequest.id)).where(
            ProjectRequest.tenant_id == tenant_id,
            ProjectRequest.organization_id == org.id,
        )
    )).scalar_one()
    return HardDeletePreview(
        entity_type="organization",
        entity_id=str(org.id),
        entity_name=org.name,
        is_active=org.is_active,
        confirm_slug=confirm_slug("organization", org.name),
        cascades={
            "business_units": bu,
            "programs": progs,
            "projects": projects,
            "project_requests": requests,
        },
    )


@router.delete("/{org_id}/permanent", status_code=204)
async def hard_delete_org(
    org_id: UUID,
    confirm: str = Query(...),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(org_id), Organization.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    ensure_inactive(org.is_active, "Organización")

    cascades_preview = {
        "business_units": (await db.execute(
            select(func.count(BusinessUnit.id)).where(
                BusinessUnit.tenant_id == tenant_id,
                BusinessUnit.organization_id == org.id,
            )
        )).scalar_one(),
        "programs": (await db.execute(
            select(func.count(Program.id)).where(
                Program.tenant_id == tenant_id, Program.organization_id == org.id
            )
        )).scalar_one(),
        "projects": (await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == tenant_id, Project.organization_id == org.id
            )
        )).scalar_one(),
        "project_requests": (await db.execute(
            select(func.count(ProjectRequest.id)).where(
                ProjectRequest.tenant_id == tenant_id,
                ProjectRequest.organization_id == org.id,
            )
        )).scalar_one(),
    }
    ensure_confirm(
        confirm,
        confirm_slug("organization", org.name),
        preview=cascades_preview,
    )

    deleted_projects = await _delete_projects_in(
        db, tenant_id, Project.organization_id == org.id
    )
    # ProjectRequest.organization_id es NOT NULL sin cascade FK — borrar.
    requests = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.tenant_id == tenant_id,
                ProjectRequest.organization_id == org.id,
            )
        )
    ).scalars().all()
    deleted_requests = len(requests)
    for r in requests:
        await db.delete(r)
    # Charter.organization_id es nullable y los charters ya fueron borrados
    # vía cascade desde Project. El resto cae por FK CASCADE: BUs, programs,
    # exclusions, notifications. Stakeholders.organization_id queda SET NULL.
    await db.flush()
    await db.delete(org)
    await write_audit(
        db, action="organization.hard_delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="organization",
        entity_id=str(org.id),
        details={
            "name": org.name,
            "cascades": {
                **cascades_preview,
                "projects_deleted": deleted_projects,
                "requests_deleted": deleted_requests,
            },
        },
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@business_units_router.get(
    "/business-units/{bu_id}/hard-delete-preview",
    response_model=HardDeletePreview,
)
async def preview_hard_delete_bu(
    bu_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    bu = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if bu is None:
        raise not_found("Unidad de negocio")
    depts = (await db.execute(
        select(func.count(Department.id)).where(
            Department.tenant_id == tenant_id, Department.business_unit_id == bu.id
        )
    )).scalar_one()
    proj_links = (await db.execute(
        select(func.count(Project.id)).where(
            Project.tenant_id == tenant_id, Project.business_unit_id == bu.id
        )
    )).scalar_one()
    return HardDeletePreview(
        entity_type="business_unit",
        entity_id=str(bu.id),
        entity_name=bu.name,
        # `is_active` puede estar en True aunque ya tenga `deleted_at`. Para
        # el gate consideramos que un BU con deleted_at ya fue desactivado.
        is_active=bu.is_active and bu.deleted_at is None,
        confirm_slug=confirm_slug("business_unit", bu.name),
        cascades={
            "departments": depts,
            "project_links_to_unset": proj_links,
        },
    )


@business_units_router.delete(
    "/business-units/{bu_id}/permanent", status_code=204
)
async def hard_delete_bu(
    bu_id: UUID,
    confirm: str = Query(...),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update

    tenant_id = _ensure_tenant(cu)
    bu = (
        await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.id == str(bu_id),
                BusinessUnit.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if bu is None:
        raise not_found("Unidad de negocio")
    is_inactive_state = (not bu.is_active) or bu.deleted_at is not None
    if not is_inactive_state:
        ensure_inactive(True, "Unidad de negocio")  # lanza siempre

    depts = (await db.execute(
        select(func.count(Department.id)).where(
            Department.tenant_id == tenant_id, Department.business_unit_id == bu.id
        )
    )).scalar_one()
    proj_links = (await db.execute(
        select(func.count(Project.id)).where(
            Project.tenant_id == tenant_id, Project.business_unit_id == bu.id
        )
    )).scalar_one()
    ensure_confirm(
        confirm,
        confirm_slug("business_unit", bu.name),
        preview={"departments": depts, "project_links_to_unset": proj_links},
    )

    # Desreferenciar tablas con FK nullable que no cascadea.
    await db.execute(
        update(Project).where(Project.business_unit_id == bu.id).values(business_unit_id=None)
    )
    await db.execute(
        update(ProjectCharter).where(ProjectCharter.business_unit_id == bu.id).values(business_unit_id=None)
    )
    await db.execute(
        update(ProjectRequest).where(ProjectRequest.business_unit_id == bu.id).values(business_unit_id=None)
    )
    await db.flush()
    # Departments cascadea por FK ondelete=CASCADE.
    await db.delete(bu)
    await write_audit(
        db, action="business_unit.hard_delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="business_unit",
        entity_id=str(bu.id),
        details={
            "name": bu.name,
            "cascades": {"departments": depts, "project_links_unset": proj_links},
        },
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@departments_router.get(
    "/departments/{dept_id}/hard-delete-preview",
    response_model=HardDeletePreview,
)
async def preview_hard_delete_dept(
    dept_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    dept = (
        await db.execute(
            select(Department).where(
                Department.id == str(dept_id),
                Department.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if dept is None:
        raise not_found("Departamento")
    progs = (await db.execute(
        select(func.count(Program.id)).where(
            Program.tenant_id == tenant_id, Program.department_id == dept.id
        )
    )).scalar_one()
    projs = (await db.execute(
        select(func.count(Project.id)).where(
            Project.tenant_id == tenant_id, Project.department_id == dept.id
        )
    )).scalar_one()
    return HardDeletePreview(
        entity_type="department",
        entity_id=str(dept.id),
        entity_name=dept.name,
        is_active=dept.is_active and dept.deleted_at is None,
        confirm_slug=confirm_slug("department", dept.name),
        cascades={
            "program_links_to_unset": progs,
            "project_links_to_unset": projs,
        },
    )


@departments_router.delete(
    "/departments/{dept_id}/permanent", status_code=204
)
async def hard_delete_dept(
    dept_id: UUID,
    confirm: str = Query(...),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update

    tenant_id = _ensure_tenant(cu)
    dept = (
        await db.execute(
            select(Department).where(
                Department.id == str(dept_id),
                Department.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if dept is None:
        raise not_found("Departamento")
    is_inactive_state = (not dept.is_active) or dept.deleted_at is not None
    if not is_inactive_state:
        ensure_inactive(True, "Departamento")

    progs = (await db.execute(
        select(func.count(Program.id)).where(
            Program.tenant_id == tenant_id, Program.department_id == dept.id
        )
    )).scalar_one()
    projs = (await db.execute(
        select(func.count(Project.id)).where(
            Project.tenant_id == tenant_id, Project.department_id == dept.id
        )
    )).scalar_one()
    ensure_confirm(
        confirm,
        confirm_slug("department", dept.name),
        preview={"program_links_to_unset": progs, "project_links_to_unset": projs},
    )

    await db.execute(
        update(Program).where(Program.department_id == dept.id).values(department_id=None)
    )
    await db.execute(
        update(Project).where(Project.department_id == dept.id).values(department_id=None)
    )
    await db.execute(
        update(ProjectCharter).where(ProjectCharter.department_id == dept.id).values(department_id=None)
    )
    await db.execute(
        update(ProjectRequest).where(ProjectRequest.department_id == dept.id).values(department_id=None)
    )
    await db.flush()
    await db.delete(dept)
    await write_audit(
        db, action="department.hard_delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="department",
        entity_id=str(dept.id),
        details={
            "name": dept.name,
            "cascades": {"program_links_unset": progs, "project_links_unset": projs},
        },
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


# ===========================================================================
# US-160 — Reportes de Status Nivel 2 (Organización / Programa) en PDF.
# Viven fuera del Report Builder; se descargan desde la página del scope.
# Admin-equivalente (agregan datos de todo el scope).
# ===========================================================================


@router.post("/{org_id}/reports/status")
async def organization_status_report(
    org_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    ctx = await build_scope_status_context(
        db, tenant_id, "organization", org_id, restrict_project_ids=role_ids
    )
    pdf = render_pdf("reports/scope_status.html", ctx)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="status-organizacion.pdf"'},
    )


@programs_router.post("/{program_id}/reports/status")
async def program_status_report(
    program_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    role_ids = await scoped_project_ids(cu, db, tenant_id)
    ctx = await build_scope_status_context(
        db, tenant_id, "program", program_id, restrict_project_ids=role_ids
    )
    pdf = render_pdf("reports/scope_status.html", ctx)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="status-programa.pdf"'},
    )
