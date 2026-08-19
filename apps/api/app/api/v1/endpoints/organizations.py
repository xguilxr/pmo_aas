from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import Result, Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_authenticated, require_capability
from app.api.v1.endpoints.dashboard import scoped_project_ids
from app.core.errors import business_rule, conflict, forbidden, mensaje, not_found
from app.core.hard_delete import confirm_slug, ensure_confirm, ensure_inactive
from app.core.visibility import get_user_visibility
from app.db.session import get_db
from app.dominio.moneda import agregar as agregar_por_moneda
from app.dominio.moneda import resolver as resolver_moneda
from app.models.area import Actor
from app.models.modules import Risk
from app.models.organization import Organization, Portfolio, Program
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.models.project_member import ProjectMember
from app.models.project_request import ProjectRequest
from app.models.user import User
from app.schemas.hard_delete import HardDeletePreview
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationPanel,
    OrganizationPanelDetail,
    OrganizationPanelHealth,
    OrganizationRead,
    OrganizationUpdate,
    OrgPanelPortfolio,
    OrgPanelProgram,
    OrgPanelProject,
    OrgPanelUser,
    PortfolioCreate,
    PortfolioRead,
    PortfolioUpdate,
    ProgramCreate,
    ProgramRead,
    ProgramSummary,
    ProgramSummaryProject,
    ProgramSummaryRisk,
    ProgramUpdate,
)
from app.services.audit import write_audit
from app.services.jerarquia import (
    portafolio_general,
    validar_portafolio_de_organizacion,
)
from app.services.moneda_tenant import preferida as moneda_preferida
from app.services.pdf_renderer import render_pdf
from app.services.reports.scoped_status import build_scope_status_context

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _panel_program(prog: Program, conteos: dict[str, int]) -> OrgPanelProgram:
    """El programa como lo pinta el panel. US-199: sale dos veces —dentro de su
    portafolio y en la lista plana— y construirlo dos veces es cómo las dos
    copias se desincronizan."""
    return OrgPanelProgram(
        id=prog.id,
        name=prog.name,
        description=prog.description,
        is_active=prog.is_active,
        active_project_count=conteos.get(str(prog.id), 0),
        portfolio_id=prog.portfolio_id,
    )


def _ensure_tenant(cu: CurrentUser) -> UUID:
    # BUG-056: superadmin post `joinAsAdmin` tiene `user.tenant_id=None`
    # pero un `active_tenant_id` en el JWT — usar ese como tenant
    # efectivo para que las pantallas /admin/organizations funcionen.
    tid = cu.effective_tenant_id
    if tid is None:
        raise forbidden(detail=mensaje(
            que="Acción no disponible para super admin sin tenant activo",
            porque="La cuenta de plataforma no está mirando ninguna organización y esta acción escribe en una.",
            accion="Elige una organización en el selector y repítela.",
        ))
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

    # US-199 — la tarjeta cuenta portafolios, no unidades de negocio (ADR-037).
    portfolio_counts_rows = (
        await db.execute(
            select(Portfolio.organization_id, func.count(Portfolio.id))
            .where(
                Portfolio.tenant_id == tenant_id,
                Portfolio.organization_id.in_(org_ids),
                Portfolio.deleted_at.is_(None),
                Portfolio.is_active.is_(True),
            )
            .group_by(Portfolio.organization_id)
        )
    ).all()
    portfolio_counts: dict[str, int] = {str(o): n for o, n in portfolio_counts_rows}

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
                portfolio_count=portfolio_counts.get(oid, 0),
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
        raise conflict(mensaje(
            que="Organización con ese nombre ya existe",
            porque="El nombre identifica la organización en toda la interfaz y no puede repetirse.",
            accion="Elige otro nombre, o edita la existente.",
        ))
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

    # US-199 — la jerarquía del panel es portafolio ⊃ programa (ADR-037).
    portfolios = (
        await db.execute(
            select(Portfolio).where(
                Portfolio.tenant_id == tenant_id,
                Portfolio.organization_id == str(org_id),
                Portfolio.deleted_at.is_(None),
            ).order_by(Portfolio.name)
        )
    ).scalars().all()

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
        portfolios=[
            OrgPanelPortfolio(
                id=pf.id,
                name=pf.name,
                code=pf.code,
                description=pf.description,
                is_active=pf.is_active,
                programs=[
                    _panel_program(p, prog_proj_counts)
                    for p in programs
                    if str(p.portfolio_id) == str(pf.id)
                ],
                # El conteo del portafolio suma los proyectos de sus programas
                # **y** los que cuelgan directo de él: si solo sumara los de
                # los programas, un portafolio sin programas se vería vacío
                # teniendo proyectos.
                active_project_count=sum(
                    prog_proj_counts.get(str(p.id), 0)
                    for p in programs
                    if str(p.portfolio_id) == str(pf.id)
                )
                + sum(
                    1
                    for pr in projects
                    if pr.program_id is None and str(pr.portfolio_id) == str(pf.id)
                ),
            )
            for pf in portfolios
        ],
        programs=[_panel_program(p, prog_proj_counts) for p in programs],
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
        raise business_rule(mensaje(
            que="La organización no existe o no pertenece al tenant",
            porque="La referencia apunta fuera de tu organización y quedaría rota.",
            accion="Elige una organización de tu tenant.",
        ))
    payload = body.model_dump()
    payload["organization_id"] = str(payload["organization_id"])
    # US-199 — el portafolio llega en el payload; si no viene, el programa cae
    # en el «Portafolio General» de su organización (DEC-030). Nadie tiene que
    # inventarse una taxonomía para dar de alta su primer programa.
    pedido = payload.pop("portfolio_id", None)
    if pedido is not None:
        await validar_portafolio_de_organizacion(
            db,
            tenant_id=tenant_id,
            organization_id=payload["organization_id"],
            portfolio_id=pedido,
        )
        portfolio_id = str(pedido)
    else:
        pf = await portafolio_general(
            db,
            tenant_id=tenant_id,
            organization_id=payload["organization_id"],
            created_by=cu.id,
        )
        portfolio_id = str(pf.id)
    prog = Program(tenant_id=tenant_id, portfolio_id=portfolio_id, **payload)
    db.add(prog)
    await db.flush()
    await write_audit(
        db, action="program.create", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="program", entity_id=str(prog.id),
        details={
            "name": body.name,
            "organization_id": str(body.organization_id),
            "portfolio_id": portfolio_id,
        },
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
    # US-199 — el resumen dice de qué portafolio es el programa: es el dato con
    # el que se sube un nivel desde esta pantalla.
    portafolio = (
        await db.execute(
            select(Portfolio).where(Portfolio.id == prog.portfolio_id)
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
    # BUG-092 — por moneda. Un programa con proyectos en monedas distintas no
    # tiene un presupuesto único, y el número que salía antes era la suma de
    # cantidades que no comparten unidad.
    preferida = await moneda_preferida(db, tenant_id)
    monedas_del_programa = {resolver_moneda(p.currency, preferida) for p in projects}
    planeado_por_moneda = agregar_por_moneda(
        (resolver_moneda(p.currency, preferida), p.budget) for p in projects
    )
    real_por_moneda = agregar_por_moneda(
        (resolver_moneda(p.currency, preferida), p.actual_budget) for p in projects
    )
    # Los campos escalares sobreviven mientras el programa sea de una sola
    # moneda —el caso de todos los inquilinos de hoy— y valen 0 con varias,
    # acompañados del desglose. La pantalla decide qué pintar.
    una_sola = len(monedas_del_programa) <= 1
    budget_planned = float(sum(planeado_por_moneda.values())) if una_sola else 0.0
    budget_actual = float(sum(real_por_moneda.values())) if una_sola else 0.0

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
        portfolio_id=prog.portfolio_id,
        portfolio_name=portafolio.name if portafolio else None,
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
        budget_planned_by_currency={m: float(v) for m, v in planeado_por_moneda.items()},
        budget_actual_by_currency={m: float(v) for m, v in real_por_moneda.items()},
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
    cambios = body.model_dump(exclude_none=True)
    destino = cambios.pop("portfolio_id", None)
    if destino is not None and str(destino) != str(prog.portfolio_id):
        # US-199 — mover un programa de portafolio **arrastra sus proyectos**.
        # Sin eso, los proyectos se quedarían apuntando al portafolio viejo y
        # violarían la regla de consistencia en el instante siguiente: la
        # vista del portafolio nuevo mostraría el programa sin sus proyectos.
        await validar_portafolio_de_organizacion(
            db,
            tenant_id=tenant_id,
            organization_id=prog.organization_id,
            portfolio_id=destino,
        )
        # `Mapped[UUID]` sobre una columna `String(36)`: la convención del
        # repo es guardar el texto (ver `db/base.py::type_annotation_map`).
        prog.portfolio_id = cast(UUID, str(destino))
        await db.execute(
            update(Project)
            .where(Project.tenant_id == tenant_id, Project.program_id == prog.id)
            .values(portfolio_id=str(destino))
        )
    for f, v in cambios.items():
        setattr(prog, f, v)
    await write_audit(
        db, action="program.update", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="program", entity_id=str(prog.id),
        details={"portfolio_id": str(destino)} if destino is not None else None,
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


# -- Portafolios (US-199 / ADR-037) ----
# Reemplazan a los sub-routers de unidades de negocio y departamentos, que
# modelaban el organigrama del cliente y nunca se usaron en producción. Las
# rutas viejas dejan de existir: responden 404, que es lo correcto — un 410 o
# un redirect mantendría vivo un concepto retirado.
portfolios_router = APIRouter(tags=["portfolios"])


def _portfolio_vivo(stmt: Select[tuple[Portfolio]]) -> Select[tuple[Portfolio]]:
    return stmt.where(Portfolio.deleted_at.is_(None))


def _get_org_or_404(db_result: Result[tuple[Organization]]) -> Organization:
    org: Organization | None = db_result.scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    return org


async def _org_del_tenant(db: AsyncSession, tenant_id: UUID, org_id: UUID) -> Organization:
    return _get_org_or_404(
        await db.execute(
            select(Organization).where(
                Organization.id == str(org_id), Organization.tenant_id == tenant_id
            )
        )
    )


async def _portafolio_o_404(db: AsyncSession, tenant_id: UUID, portfolio_id: UUID) -> Portfolio:
    pf: Portfolio | None = (
        await db.execute(
            _portfolio_vivo(
                select(Portfolio).where(
                    Portfolio.id == str(portfolio_id),
                    Portfolio.tenant_id == tenant_id,
                )
            )
        )
    ).scalar_one_or_none()
    if pf is None:
        raise not_found("Portafolio")
    return pf


async def _validar_actor_dueno(
    db: AsyncSession, tenant_id: UUID, owner_actor_id: str | UUID | None
) -> None:
    """El dueño del portafolio tiene que ser un actor del propio inquilino.

    Sin esta comprobación, el identificador de un actor ajeno se guardaría tal
    cual y el nombre del sponsor de otra empresa aparecería en la ficha.
    """
    if owner_actor_id is None:
        return
    existe = (
        await db.execute(
            select(Actor.id).where(
                Actor.id == str(owner_actor_id), Actor.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if existe is None:
        raise business_rule(
            mensaje(
                que="La persona indicada como dueña del portafolio no está en tu catálogo",
                porque="La referencia apunta fuera de tu inquilino y quedaría rota.",
                accion="Elige a alguien del directorio de personas de tu inquilino.",
            )
        )


async def _conteos_de_portafolios(
    db: AsyncSession, tenant_id: UUID, portfolio_ids: list[str]
) -> tuple[dict[str, int], dict[str, int]]:
    """Programas y proyectos activos por portafolio.

    Dos consultas agrupadas y no una por portafolio: el panel de una
    organización con veinte portafolios haría cuarenta viajes a la base para
    pintar dos números por fila.
    """
    if not portfolio_ids:
        return {}, {}
    filas_prog = (
        await db.execute(
            select(Program.portfolio_id, func.count(Program.id))
            .where(
                Program.tenant_id == tenant_id,
                Program.portfolio_id.in_(portfolio_ids),
                Program.is_active.is_(True),
            )
            .group_by(Program.portfolio_id)
        )
    ).all()
    filas_proy = (
        await db.execute(
            select(Project.portfolio_id, func.count(Project.id))
            .where(
                Project.tenant_id == tenant_id,
                Project.portfolio_id.in_(portfolio_ids),
                Project.deleted_at.is_(None),
                Project.phase != "closed",
            )
            .group_by(Project.portfolio_id)
        )
    ).all()
    return (
        {str(pid): int(n) for pid, n in filas_prog},
        {str(pid): int(n) for pid, n in filas_proy},
    )


def _portfolio_read(
    pf: Portfolio, progs: dict[str, int], proys: dict[str, int]
) -> PortfolioRead:
    leido = PortfolioRead.model_validate(pf)
    leido.program_count = progs.get(str(pf.id), 0)
    leido.active_project_count = proys.get(str(pf.id), 0)
    return leido


@portfolios_router.post(
    "/organizations/{org_id}/portfolios",
    response_model=PortfolioRead,
    status_code=201,
)
async def create_portfolio(
    org_id: UUID,
    body: PortfolioCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    org = await _org_del_tenant(db, tenant_id, org_id)
    existente = (
        await db.execute(
            _portfolio_vivo(
                select(Portfolio).where(
                    Portfolio.tenant_id == tenant_id,
                    Portfolio.organization_id == org.id,
                    Portfolio.name == body.name,
                )
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise conflict(mensaje(
            que="Ya hay un portafolio con ese nombre en la organización",
            porque="Dos portafolios con el mismo nombre serían indistinguibles al clasificar.",
            accion="Elige otro nombre, o edita el que ya existe.",
        ))
    await _validar_actor_dueno(db, tenant_id, body.owner_actor_id)
    datos = body.model_dump()
    if datos.get("owner_actor_id") is not None:
        datos["owner_actor_id"] = str(datos["owner_actor_id"])
    pf = Portfolio(
        tenant_id=tenant_id,
        organization_id=str(org.id),
        created_by=str(cu.id),
        **datos,
    )
    db.add(pf)
    await db.flush()
    await write_audit(
        db, action="portfolio.create", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="portfolio", entity_id=str(pf.id),
        details={"name": body.name, "organization_id": str(org.id)},
    )
    await db.commit()
    return _portfolio_read(pf, {}, {})


@portfolios_router.get(
    "/organizations/{org_id}/portfolios",
    response_model=list[PortfolioRead],
)
async def list_portfolios(
    org_id: UUID,
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    await _org_del_tenant(db, tenant_id, org_id)
    stmt = _portfolio_vivo(
        select(Portfolio).where(
            Portfolio.tenant_id == tenant_id,
            Portfolio.organization_id == str(org_id),
        )
    )
    if q:
        stmt = stmt.where(func.lower(Portfolio.name).like(f"%{q.lower()}%"))
    if is_active is not None:
        stmt = stmt.where(Portfolio.is_active == is_active)
    filas = (await db.execute(stmt.order_by(Portfolio.name))).scalars().all()
    progs, proys = await _conteos_de_portafolios(
        db, tenant_id, [str(pf.id) for pf in filas]
    )
    return [_portfolio_read(pf, progs, proys) for pf in filas]


@portfolios_router.get("/portfolios/{portfolio_id}", response_model=PortfolioRead)
async def get_portfolio(
    portfolio_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    pf = await _portafolio_o_404(db, tenant_id, portfolio_id)
    progs, proys = await _conteos_de_portafolios(db, tenant_id, [str(pf.id)])
    return _portfolio_read(pf, progs, proys)


@portfolios_router.patch("/portfolios/{portfolio_id}", response_model=PortfolioRead)
async def update_portfolio(
    portfolio_id: UUID,
    body: PortfolioUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    pf = await _portafolio_o_404(db, tenant_id, portfolio_id)
    if body.name and body.name != pf.name:
        choque = (
            await db.execute(
                _portfolio_vivo(
                    select(Portfolio).where(
                        Portfolio.tenant_id == tenant_id,
                        Portfolio.organization_id == pf.organization_id,
                        Portfolio.name == body.name,
                        Portfolio.id != pf.id,
                    )
                )
            )
        ).scalar_one_or_none()
        if choque is not None:
            raise conflict(mensaje(
                que="Ya hay un portafolio con ese nombre en la organización",
                porque="Dos portafolios con el mismo nombre serían indistinguibles al clasificar.",
                accion="Elige otro nombre, o edita el que ya existe.",
            ))
    if body.owner_actor_id is not None:
        await _validar_actor_dueno(db, tenant_id, body.owner_actor_id)
    for campo, valor in body.model_dump(exclude_none=True).items():
        setattr(pf, campo, str(valor) if campo == "owner_actor_id" else valor)
    await write_audit(
        db, action="portfolio.update", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="portfolio", entity_id=str(pf.id),
    )
    await db.commit()
    progs, proys = await _conteos_de_portafolios(db, tenant_id, [str(pf.id)])
    return _portfolio_read(pf, progs, proys)


@portfolios_router.delete("/portfolios/{portfolio_id}", status_code=204)
async def delete_portfolio(
    portfolio_id: UUID,
    force: bool = Query(default=False),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Primer paso de la papelera (ADR-017): desactiva, no borra.

    Con programas activos dentro exige `force=true`, igual que hacía la unidad
    de negocio con sus departamentos: retirar el portafolio sin decirlo dejaría
    sus programas colgando de algo que ninguna pantalla lista.
    """
    tenant_id = _ensure_tenant(cu)
    pf = await _portafolio_o_404(db, tenant_id, portfolio_id)
    programas_activos = (
        await db.execute(
            select(Program.id, Program.name).where(
                Program.tenant_id == tenant_id,
                Program.portfolio_id == pf.id,
                Program.is_active.is_(True),
            )
        )
    ).all()
    if programas_activos and not force:
        raise business_rule(
            mensaje(
                que=(
                    f"El portafolio tiene {len(programas_activos)} programa(s) "
                    "activo(s). Usa force=true para desactivarlos en cascada."
                ),
                porque="Retirar el portafolio dejaría sus programas colgando de nada.",
                accion="Mueve o cierra los programas, o repite con `force=true`.",
            ),
            code="PORTFOLIO_HAS_ACTIVE_PROGRAMS",
        )
    ahora = datetime.now(UTC)
    pf.is_active = False
    pf.deleted_at = ahora
    if force:
        await db.execute(
            update(Program)
            .where(Program.tenant_id == tenant_id, Program.portfolio_id == pf.id)
            .values(is_active=False)
        )
    await write_audit(
        db, action="portfolio.delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="portfolio", entity_id=str(pf.id),
        details={
            "force": force,
            "cascaded_programs": [nombre for _, nombre in programas_activos],
        },
    )
    await db.commit()
    return Response(status_code=204)


# =============================================================================
# US-088 — Hard delete (segundo paso) para org/portafolio/programa
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


async def _desreferenciar_clasificacion(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    portfolio_ids: list[str] | None = None,
    program_ids: list[str] | None = None,
) -> None:
    """Suelta las solicitudes y actas que apuntan a lo que está por borrarse.

    `project_requests.{portfolio_id, program_id}` y las dos equivalentes de
    `project_charters` son claves ajenas **sin** `ondelete`, así que borrar el
    portafolio o el programa con una solicitud apuntándole revienta contra la
    restricción — un 500 en la cara de quien confirmó el borrado.

    Se desreferencian en vez de borrarse porque una solicitud es un registro
    histórico de lo que alguien pidió: pierde su clasificación, no su
    existencia. Las actas de proyectos que sí se borran caen por su propia
    cascada; esta pasada cubre a las de los proyectos que sobreviven.
    """
    for modelo in (ProjectRequest, ProjectCharter):
        if portfolio_ids:
            await db.execute(
                update(modelo)
                .where(
                    modelo.tenant_id == tenant_id,
                    modelo.portfolio_id.in_(portfolio_ids),
                )
                .values(portfolio_id=None)
            )
        if program_ids:
            await db.execute(
                update(modelo)
                .where(
                    modelo.tenant_id == tenant_id,
                    modelo.program_id.in_(program_ids),
                )
                .values(program_id=None)
            )
    await db.flush()


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
    # US-199 — una solicitud puede apuntar a este programa sin haber llegado a
    # proyecto. Sin soltarla, el borrado choca contra su clave ajena.
    await _desreferenciar_clasificacion(db, tenant_id, program_ids=[str(prog.id)])
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
    portafolios = (await db.execute(
        select(func.count(Portfolio.id)).where(
            Portfolio.tenant_id == tenant_id, Portfolio.organization_id == org.id
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
            "portfolios": portafolios,
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
        "portfolios": (await db.execute(
            select(func.count(Portfolio.id)).where(
                Portfolio.tenant_id == tenant_id,
                Portfolio.organization_id == org.id,
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
    # vía cascade desde Project. El resto cae por FK CASCADE: portafolios,
    # programs, exclusions, notifications. Stakeholders.organization_id queda
    # SET NULL.
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


@portfolios_router.get(
    "/portfolios/{portfolio_id}/hard-delete-preview",
    response_model=HardDeletePreview,
)
async def preview_hard_delete_portfolio(
    portfolio_id: UUID,
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    # Sin filtro de `deleted_at`: el segundo paso opera precisamente sobre lo
    # que el primero mandó a la papelera.
    pf = (
        await db.execute(
            select(Portfolio).where(
                Portfolio.id == str(portfolio_id), Portfolio.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pf is None:
        raise not_found("Portafolio")
    programas, proyectos_de_programa, proyectos_directos = await _cascada_de_portafolio(
        db, tenant_id, pf
    )
    return HardDeletePreview(
        entity_type="portfolio",
        entity_id=str(pf.id),
        entity_name=pf.name,
        # `is_active` puede seguir en True con `deleted_at` puesto. Para el
        # gate, un portafolio con fecha de borrado ya fue desactivado.
        is_active=pf.is_active and pf.deleted_at is None,
        confirm_slug=confirm_slug("portfolio", pf.name),
        cascades={
            "programs": programas,
            "projects_in_programs": proyectos_de_programa,
            "projects_direct": proyectos_directos,
        },
    )


async def _cascada_de_portafolio(
    db: AsyncSession, tenant_id: UUID, pf: Portfolio
) -> tuple[int, int, int]:
    """Qué se lleva por delante el borrado permanente de un portafolio.

    Tres números y no uno, porque son tres cosas distintas de aceptar:
    programas, los proyectos que cuelgan de esos programas, y los proyectos que
    cuelgan del portafolio sin programa. Un total agregado esconde justo lo que
    hay que leer antes de escribir el nombre para confirmar.
    """
    programas = (
        await db.execute(
            select(Program.id).where(
                Program.tenant_id == tenant_id, Program.portfolio_id == pf.id
            )
        )
    ).scalars().all()
    if programas:
        en_programas = (
            await db.execute(
                select(func.count(Project.id)).where(
                    Project.tenant_id == tenant_id, Project.program_id.in_(programas)
                )
            )
        ).scalar_one()
    else:
        en_programas = 0
    directos = (
        await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == tenant_id,
                Project.portfolio_id == pf.id,
                Project.program_id.is_(None),
            )
        )
    ).scalar_one()
    return len(programas), int(en_programas), int(directos)


@portfolios_router.delete("/portfolios/{portfolio_id}/permanent", status_code=204)
async def hard_delete_portfolio(
    portfolio_id: UUID,
    confirm: str = Query(...),
    cu: CurrentUser = Depends(require_capability("organizations.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Segundo paso: borrado físico, con su cascada explícita (ADR-017).

    **Borra proyectos.** `programs.portfolio_id` es NOT NULL, así que no hay
    forma de dejar un programa sin portafolio: o se mueve antes, o cae con él,
    y con él caen sus proyectos. Es la misma cascada que ya tenía el borrado
    permanente de un programa. Los proyectos que cuelgan directo del portafolio
    **no** se borran: su `portfolio_id` admite nulo, así que se desreferencian
    y siguen existiendo — borrar un proyecto por su clasificación sería
    perderlo por un cambio de taxonomía.
    """
    tenant_id = _ensure_tenant(cu)
    pf = (
        await db.execute(
            select(Portfolio).where(
                Portfolio.id == str(portfolio_id), Portfolio.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pf is None:
        raise not_found("Portafolio")
    if pf.is_active and pf.deleted_at is None:
        ensure_inactive(True, "Portafolio")  # lanza siempre

    programas, en_programas, directos = await _cascada_de_portafolio(db, tenant_id, pf)
    ensure_confirm(
        confirm,
        confirm_slug("portfolio", pf.name),
        preview={
            "programs": programas,
            "projects_in_programs": en_programas,
            "projects_direct": directos,
        },
    )

    # Los proyectos que cuelgan directo se quedan; pierden la clasificación.
    await db.execute(
        update(Project)
        .where(
            Project.tenant_id == tenant_id,
            Project.portfolio_id == pf.id,
            Project.program_id.is_(None),
        )
        .values(portfolio_id=None)
    )
    filas_programa = (
        await db.execute(
            select(Program).where(
                Program.tenant_id == tenant_id, Program.portfolio_id == pf.id
            )
        )
    ).scalars().all()
    await _desreferenciar_clasificacion(
        db,
        tenant_id,
        portfolio_ids=[str(pf.id)],
        program_ids=[str(prog.id) for prog in filas_programa],
    )
    borrados = 0
    for prog in filas_programa:
        borrados += await _delete_projects_in(db, tenant_id, Project.program_id == prog.id)
        await db.delete(prog)
    await db.flush()
    await db.delete(pf)
    await write_audit(
        db, action="portfolio.hard_delete", module="organizations",
        user_id=cu.id, tenant_id=tenant_id, entity_type="portfolio",
        entity_id=str(pf.id),
        details={
            "name": pf.name,
            "cascades": {
                "programs": len(filas_programa),
                "projects_deleted": borrados,
                "projects_unset": directos,
            },
        },
    )
    await db.commit()
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
