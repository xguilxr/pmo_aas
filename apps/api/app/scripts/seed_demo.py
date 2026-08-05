"""Seed de datos demo para tenants existentes (acme, globex).

Puebla cada tenant con: 1 usuario por rol, 2 organizaciones, 2 programas,
3-5 proyectos por programa, 1 proyecto standalone, solicitudes en cada status,
al menos un RAID de cada tipo (risks, issues, change_requests, documents,
lessons, meeting_minutes), project_members y tasks.

Requisitos previos:
  - Migraciones alembic aplicadas.
  - `run_initial_seed` ya corrido (tenants acme/globex + roles sistema + admins).

Uso:
  cd apps/api
  python -m app.scripts.seed_demo

Idempotente: si un objeto ya existe (por nombre o folio), lo reutiliza en lugar
de fallar. Se puede correr varias veces sin duplicar datos.

Credenciales demo (password uniforme para todos los usuarios creados aqui):
  Password: Demo1234!Seed
  must_change_password = True (se forzara cambio en primer login)

Usuarios creados por tenant (slug ∈ {acme, globex}):
  pmo.<slug>      -> rol PMO Manager
  pm.<slug>       -> rol Project Manager
  viewer.<slug>   -> rol Viewer
  (admin.<slug>   -> ya existe desde run_initial_seed, rol Administrador)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.modules import (
    ChangeRequest,
    Document,
    Issue,
    Lesson,
    MeetingMinute,
    Risk,
)
from app.models.organization import Organization, Program
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_request import ProjectRequest
from app.models.role import Role, UserRole
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User
from app.services.folio import next_folio

logger = logging.getLogger("pmoaas.seed_demo")

DEMO_PASSWORD = "Demo1234!Seed"  # cumple policy (>=12, upper, digit, symbol)

TENANT_SLUGS = ["acme", "globex"]

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


async def _get_tenant(db: AsyncSession, slug: str) -> Tenant:
    t = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if t is None:
        raise RuntimeError(
            f"Tenant '{slug}' no existe. Ejecuta run_initial_seed primero."
        )
    return t


async def _get_roles(db: AsyncSession, tenant_id: str) -> dict[str, Role]:
    rows = (
        await db.execute(select(Role).where(Role.tenant_id == tenant_id))
    ).scalars().all()
    return {r.name: r for r in rows}


async def _ensure_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    username: str,
    email: str,
    full_name: str,
    role: Role,
) -> User:
    existing = (
        await db.execute(
            select(User).where(User.tenant_id == tenant_id, User.username == username)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    u = User(
        tenant_id=tenant_id,
        username=username,
        email=email.lower(),
        password_hash=hash_password(DEMO_PASSWORD),
        full_name=full_name,
        is_active=True,
        is_superadmin=False,
        must_change_password=True,
        locale="es-MX",
    )
    db.add(u)
    await db.flush()
    db.add(UserRole(user_id=u.id, role_id=role.id))
    await db.flush()
    return u


async def _ensure_org(
    db: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    industry: str,
    country: str,
    contact_email: str,
) -> Organization:
    existing = (
        await db.execute(
            select(Organization).where(
                Organization.tenant_id == tenant_id, Organization.name == name
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    o = Organization(
        tenant_id=tenant_id,
        name=name,
        reason_social=f"{name} S.A. de C.V.",
        industry=industry,
        country=country,
        contact_email=contact_email,
        is_active=True,
    )
    db.add(o)
    await db.flush()
    return o


async def _ensure_program(
    db: AsyncSession,
    *,
    tenant_id: str,
    organization_id: str,
    name: str,
    description: str,
    alignment: str,
    start: date,
    end: date,
) -> Program:
    existing = (
        await db.execute(
            select(Program).where(
                Program.tenant_id == tenant_id,
                Program.organization_id == organization_id,
                Program.name == name,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    p = Program(
        tenant_id=tenant_id,
        organization_id=organization_id,
        name=name,
        description=description,
        strategic_alignment=alignment,
        start_date=start,
        end_date=end,
        is_active=True,
    )
    db.add(p)
    await db.flush()
    return p


async def _ensure_project(
    db: AsyncSession,
    *,
    tenant_id: str,
    organization_id: str,
    program_id: str | None,
    name: str,
    ptype: str,
    phase: str,
    health: str,
    progress: int,
    pm_id: str | None,
    sponsor: str,
    start: date,
    end: date,
    budget: Decimal,
) -> Project:
    existing = (
        await db.execute(
            select(Project).where(
                Project.tenant_id == tenant_id, Project.name == name
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    folio = await next_folio(db, tenant_id=tenant_id, prefix="PROJ")
    p = Project(
        tenant_id=tenant_id,
        organization_id=organization_id,
        program_id=program_id,
        folio=folio,
        name=name,
        description=f"Proyecto demo '{name}' generado por seed_demo.",
        type=ptype,
        priority=3,
        phase=phase,
        pm_id=pm_id,
        sponsor=sponsor,
        start_date=start,
        end_date=end,
        budget=budget,
        actual_budget=budget * Decimal("0.35"),
        progress=progress,
        health_status=health,
    )
    db.add(p)
    await db.flush()
    return p


async def _ensure_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    organization_id: str,
    requested_by: str,
    reviewed_by: str | None,
    title: str,
    status: str,
) -> ProjectRequest:
    existing = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.tenant_id == tenant_id,
                ProjectRequest.title == title,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    folio = await next_folio(db, tenant_id=tenant_id, prefix="REQ")
    now = datetime.now(UTC)
    review_map = {
        "in_review": (None, None, None),
        "approve": (reviewed_by, now, "Aprobado por comite PMO."),
        "reject": (reviewed_by, now, "Rechazado: no se alinea con estrategia."),
        "needs_info": (reviewed_by, now, "Requiere plan de beneficios detallado."),
    }
    rev_by, rev_at, rev_comment = review_map[status]
    r = ProjectRequest(
        tenant_id=tenant_id,
        folio=folio,
        title=title,
        description=f"Descripcion de la solicitud '{title}'.",
        objective="Habilitar nuevas capacidades de negocio.",
        organization_id=organization_id,
        business_unit="Tecnologia",
        department="Transformacion Digital",
        sponsor="Direccion General",
        benefits="Reduccion de costos, mejora de CX, time-to-market.",
        budget=Decimal("500000.00"),
        scope="Incluye descubrimiento, diseño, implementacion y estabilizacion.",
        requested_by=requested_by,
        requested_at=now - timedelta(days=5),
        status=status,
        reviewed_by=rev_by,
        reviewed_at=rev_at,
        review_comment=rev_comment,
        attachments=[],
    )
    db.add(r)
    await db.flush()
    return r


# ----------------------------------------------------------------------------
# RAID y extras sobre un proyecto dado
# ----------------------------------------------------------------------------


async def _seed_raid_for_project(
    db: AsyncSession,
    *,
    tenant_id: str,
    project: Project,
    pm: User,
    created_by: User,
) -> None:
    now = datetime.now(UTC)
    today = now.date()

    # RISK
    folio_r = await next_folio(db, tenant_id=tenant_id, prefix="RISK")
    db.add(
        Risk(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_r,
            title="Dependencia critica con proveedor externo",
            description="El proveedor X podria retrasar entregables clave.",
            status="in_progress",  # US-179
            created_by=created_by.id,
            category="proveedor",
            probability=3,
            impact=4,
            severity=12,
            mitigation_strategy="Contrato con SLA y plan B con proveedor alterno.",
            owner_id=pm.id,
            identified_at=today - timedelta(days=10),
            due_date=today + timedelta(days=30),
        )
    )

    # ISSUE (type=issue)
    folio_i = await next_folio(db, tenant_id=tenant_id, prefix="ISS")
    db.add(
        Issue(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_i,
            title="Ambiente de QA intermitente",
            description="El ambiente de QA presenta caidas aleatorias.",
            status="in_progress",
            created_by=created_by.id,
            type="issue",
            priority=2,
            reported_at=now - timedelta(days=3),
            owner_id=pm.id,
            comments=[],
        )
    )
    # ACTION (type=action)
    folio_i2 = await next_folio(db, tenant_id=tenant_id, prefix="ISS")
    db.add(
        Issue(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_i2,
            title="Programar sesion de kickoff con stakeholders",
            description="Coordinar agenda con stakeholders clave.",
            status="open",
            created_by=created_by.id,
            type="action",
            priority=3,
            reported_at=now - timedelta(days=1),
            owner_id=pm.id,
            comments=[],
        )
    )
    # DECISION (type=decision)
    folio_i3 = await next_folio(db, tenant_id=tenant_id, prefix="ISS")
    db.add(
        Issue(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_i3,
            title="Adoptar arquitectura event-driven",
            description="Decision tomada en comite de arquitectura.",
            status="resolved",
            created_by=created_by.id,
            type="decision",
            priority=2,
            reported_at=now - timedelta(days=7),
            resolution="Aprobado: se migra a event-driven por fases.",
            owner_id=pm.id,
            comments=[],
        )
    )

    # CHANGE REQUEST
    folio_c = await next_folio(db, tenant_id=tenant_id, prefix="CHG")
    db.add(
        ChangeRequest(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_c,
            title="Ampliar alcance: modulo de reportes ejecutivos",
            description="Se solicita incluir dashboards ejecutivos.",
            status="in_review",
            created_by=created_by.id,
            type="scope",
            impact="+3 semanas, +$80k USD.",
            requested_by=created_by.id,
            requested_at=now - timedelta(days=2),
        )
    )

    # DOCUMENT
    folio_d = await next_folio(db, tenant_id=tenant_id, prefix="DOC")
    db.add(
        Document(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_d,
            title="Project Charter",
            description="Acta constitutiva del proyecto.",
            status="published",
            created_by=created_by.id,
            category="plan",
            file_url="https://example.local/docs/charter.pdf",
            mime_type="application/pdf",
            size_bytes=245_678,
            version=1,
            uploaded_by=created_by.id,
            uploaded_at=now - timedelta(days=15),
            is_current=True,
        )
    )

    # LESSON
    folio_l = await next_folio(db, tenant_id=tenant_id, prefix="LES")
    db.add(
        Lesson(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_l,
            title="Involucrar a operaciones desde descubrimiento",
            description="Integrar al area de operaciones en fases tempranas reduce re-trabajo.",
            status="published",
            created_by=created_by.id,
            category="improvement",
            phase="planning",
            recommendation="Incluir representante de ops en todos los kickoffs.",
            tags=["stakeholders", "operaciones"],
        )
    )

    # MEETING MINUTE
    folio_m = await next_folio(db, tenant_id=tenant_id, prefix="MIN")
    db.add(
        MeetingMinute(
            tenant_id=tenant_id,
            project_id=project.id,
            folio=folio_m,
            title="Kickoff del proyecto",
            description="Reunion de arranque con stakeholders.",
            status="published",
            created_by=created_by.id,
            meeting_date=now - timedelta(days=14),
            participants=[
                {"name": pm.full_name, "role": "PM"},
                {"name": "Sponsor", "role": "Sponsor"},
            ],
            topics=["Alcance", "Equipo", "Riesgos iniciales"],
            agreements=[
                {"text": "Cadencia semanal los martes 10am", "owner": pm.full_name}
            ],
            next_meeting_date=(now + timedelta(days=7)).date(),
            attachments=[],
            generated_by_ai=False,
        )
    )

    await db.flush()


async def _seed_tasks_for_project(
    db: AsyncSession,
    *,
    tenant_id: str,
    project: Project,
    owner: User,
) -> None:
    start = project.start_date or date.today()
    base = [
        ("1", "Descubrimiento", 10, True),
        ("2", "Diseño", 15, False),
        ("3", "Implementacion", 30, False),
        ("4", "Pruebas y UAT", 10, False),
        ("5", "Go-live", 1, True),
    ]
    offset = 0
    for wbs_code, name, dur, milestone in base:
        db.add(
            Task(
                tenant_id=tenant_id,
                project_id=project.id,
                wbs_code=wbs_code,
                name=name,
                description=f"Fase {name} del proyecto.",
                start_date=start + timedelta(days=offset),
                end_date=start + timedelta(days=offset + dur),
                duration_days=dur,
                progress=50 if wbs_code in ("1", "2") else 0,
                is_milestone=milestone,
                owner_id=owner.id,
                priority=3,
                status="in_progress" if wbs_code == "1" else "not_started",
                source="manual",
            )
        )
        offset += dur
    await db.flush()


# ----------------------------------------------------------------------------
# Orquestacion por tenant
# ----------------------------------------------------------------------------


async def _seed_tenant(db: AsyncSession, slug: str) -> dict:
    tenant = await _get_tenant(db, slug)
    tid = tenant.id
    logger.info("[seed_demo] ==> tenant=%s id=%s", slug, tid)

    roles = await _get_roles(db, tid)
    for rname in ("Administrador", "PMO Manager", "Project Manager", "Viewer"):
        if rname not in roles:
            raise RuntimeError(
                f"Rol sistema '{rname}' no existe en tenant {slug}. "
                "Ejecuta run_initial_seed primero."
            )

    # 1) Usuarios por rol (admin ya existe desde bootstrap)
    admin_user = (
        await db.execute(
            select(User).where(User.tenant_id == tid, User.username == "admin")
        )
    ).scalar_one()

    pmo_user = await _ensure_user(
        db,
        tenant_id=tid,
        username=f"pmo.{slug}",
        email=f"pmo@{slug}.pmoaas.local",
        full_name=f"PMO Manager {slug.title()}",
        role=roles["PMO Manager"],
    )
    pm_user = await _ensure_user(
        db,
        tenant_id=tid,
        username=f"pm.{slug}",
        email=f"pm@{slug}.pmoaas.local",
        full_name=f"Project Manager {slug.title()}",
        role=roles["Project Manager"],
    )
    viewer_user = await _ensure_user(
        db,
        tenant_id=tid,
        username=f"viewer.{slug}",
        email=f"viewer@{slug}.pmoaas.local",
        full_name=f"Viewer {slug.title()}",
        role=roles["Viewer"],
    )

    # 2) Organizaciones (2)
    org_a = await _ensure_org(
        db,
        tenant_id=tid,
        name=f"{slug.title()} Digital",
        industry="Tecnologia",
        country="Mexico",
        contact_email=f"digital@{slug}.pmoaas.local",
    )
    org_b = await _ensure_org(
        db,
        tenant_id=tid,
        name=f"{slug.title()} Operaciones",
        industry="Servicios",
        country="Mexico",
        contact_email=f"ops@{slug}.pmoaas.local",
    )

    # 3) Programas (2, uno por organizacion)
    today = date.today()
    prog_1 = await _ensure_program(
        db,
        tenant_id=tid,
        organization_id=org_a.id,
        name="Transformacion Digital 2026",
        description="Modernizacion de plataformas digitales y datos.",
        alignment="OKR: duplicar canales digitales.",
        start=today - timedelta(days=60),
        end=today + timedelta(days=300),
    )
    prog_2 = await _ensure_program(
        db,
        tenant_id=tid,
        organization_id=org_b.id,
        name="Excelencia Operativa",
        description="Automatizacion de procesos operativos.",
        alignment="OKR: reducir costo operativo 15%.",
        start=today - timedelta(days=30),
        end=today + timedelta(days=240),
    )

    # 4) Proyectos: 4 en prog_1, 3 en prog_2, 1 standalone
    project_specs = [
        # (name, program, org, type, phase, health, progress)
        ("Portal de clientes v2", prog_1, org_a, "transformation", "execution", "green", 35),
        ("Motor de recomendaciones IA", prog_1, org_a, "innovation", "planning", "yellow", 10),
        ("Migracion a cloud", prog_1, org_a, "transformation", "execution", "yellow", 45),
        ("App movil empleados", prog_1, org_a, "innovation", "planning", "green", 5),
        ("Automatizacion de nomina", prog_2, org_b, "operation", "execution", "green", 60),
        ("Dashboards de operacion", prog_2, org_b, "bau", "hypercare", "green", 90),
        ("Integracion ERP-CRM", prog_2, org_b, "transformation", "execution", "red", 25),
        ("Iniciativa independiente", None, org_a, "innovation", "planning", "green", 0),
    ]
    projects: list[Project] = []
    for (name, prog, org, ptype, phase, health, progress) in project_specs:
        p = await _ensure_project(
            db,
            tenant_id=tid,
            organization_id=org.id,
            program_id=prog.id if prog else None,
            name=f"{name} ({slug})",
            ptype=ptype,
            phase=phase,
            health=health,
            progress=progress,
            pm_id=pm_user.id,
            sponsor=f"Sponsor {slug.title()}",
            start=today - timedelta(days=30),
            end=today + timedelta(days=180),
            budget=Decimal("1000000.00"),
        )
        projects.append(p)

        # Project members: pm, viewer, pmo
        for u, role_in in (
            (pm_user, "pm"),
            (viewer_user, "viewer"),
            (pmo_user, "stakeholder"),
        ):
            exists = (
                await db.execute(
                    select(ProjectMember).where(
                        ProjectMember.project_id == p.id,
                        ProjectMember.user_id == u.id,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                db.add(
                    ProjectMember(
                        project_id=p.id, user_id=u.id, role_in_project=role_in
                    )
                )
    await db.flush()

    # 5) Solicitudes en cada status (4)
    for title, status in [
        (f"Solicitud en revision ({slug})", "in_review"),
        (f"Solicitud aprobada ({slug})", "approve"),
        (f"Solicitud rechazada ({slug})", "reject"),
        (f"Solicitud pide info ({slug})", "needs_info"),
    ]:
        await _ensure_request(
            db,
            tenant_id=tid,
            organization_id=org_a.id,
            requested_by=pmo_user.id,
            reviewed_by=admin_user.id,
            title=title,
            status=status,
        )

    # 6) RAID y tasks sobre el primer proyecto (existe siempre)
    target = projects[0]
    # Evita duplicar RAID si ya corrio: solo corre si no hay risks aun en este proyecto
    has_risk = (
        await db.execute(select(Risk).where(Risk.project_id == target.id))
    ).first()
    if not has_risk:
        await _seed_raid_for_project(
            db, tenant_id=tid, project=target, pm=pm_user, created_by=admin_user
        )

    has_task = (
        await db.execute(select(Task).where(Task.project_id == target.id))
    ).first()
    if not has_task:
        await _seed_tasks_for_project(
            db, tenant_id=tid, project=target, owner=pm_user
        )

    return {
        "tenant": slug,
        "users": [u.email for u in (pmo_user, pm_user, viewer_user)],
        "organizations": [org_a.name, org_b.name],
        "programs": [prog_1.name, prog_2.name],
        "projects": [p.name for p in projects],
    }


async def run_demo_seed() -> None:
    async with SessionLocal() as db:
        summary = []
        for slug in TENANT_SLUGS:
            summary.append(await _seed_tenant(db, slug))
        await db.commit()

    banner = "\n" + "=" * 72 + "\n"
    banner += "[seed_demo] DATOS DEMO SEMBRADOS\n"
    banner += "=" * 72 + "\n"
    banner += f"Password uniforme de usuarios nuevos: {DEMO_PASSWORD}\n"
    banner += "(Se forzara cambio de password en primer login.)\n"
    banner += "-" * 72 + "\n"
    for s in summary:
        banner += f"  tenant={s['tenant']}\n"
        banner += f"    users (nuevos): {', '.join(s['users'])}\n"
        banner += f"    orgs: {', '.join(s['organizations'])}\n"
        banner += f"    programs: {', '.join(s['programs'])}\n"
        banner += f"    projects: {len(s['projects'])}\n"
    banner += "=" * 72
    logger.warning(banner)
    print(banner)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(run_demo_seed())
