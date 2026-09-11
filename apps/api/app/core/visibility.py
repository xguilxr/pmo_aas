"""US-167/168 — Utilidad de visibilidad de recursos por usuario.

Para usuarios PM (role_type='user') la visibilidad está restringida a los
recursos asignados en `user_scope_assignments`, con herencia hacia abajo:
- Org → todos sus portafolios, programas y proyectos del tenant.
- Portfolio (ENH-204 — afecta US-167): todos sus programas y proyectos +
  la org padre (visible como contexto). No hereda a otros portafolios de
  la misma org ni al resto del contenido de la org.
- Program → todos sus proyectos + org y portafolio padres (visibles como
  contexto).
- Project → solo ese proyecto + programa, portafolio y org padres
  (visibles como contexto).

Admin, pm_sr y superadmin ignoran la tabla — siempre ven todo (retorna None).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import _ADMIN_EQUIVALENT_ROLES
from app.models.organization import Portfolio, Program
from app.models.project import Project
from app.models.user import User
from app.models.user_scope_assignment import UserScopeAssignment


@dataclass
class VisibilityScope:
    """IDs de recursos visibles para un PM.

    None significa "sin restricción" (admin/pm_sr/superadmin).
    Un set vacío significa "no ve nada" (PM sin asignaciones).
    """
    org_ids: set[str] | None = None
    portfolio_ids: set[str] | None = None
    program_ids: set[str] | None = None
    project_ids: set[str] | None = None

    @property
    def unrestricted(self) -> bool:
        return self.org_ids is None


async def get_user_visibility(
    user: User,
    db: AsyncSession,
) -> VisibilityScope:
    """Retorna el scope de visibilidad del usuario.

    Para admin/pm_sr/superadmin: VisibilityScope con None en todos los campos.
    Para PM (user): calcula org_ids, program_ids, project_ids visibles
    expandiendo la herencia de asignaciones.
    """
    if user.is_superadmin or (user.role_type in _ADMIN_EQUIVALENT_ROLES):
        return VisibilityScope()  # None fields = sin restricción

    tenant_id = str(user.tenant_id) if user.tenant_id else None
    if tenant_id is None:
        return VisibilityScope(
            org_ids=set(), portfolio_ids=set(), program_ids=set(), project_ids=set()
        )

    assignments = (
        await db.execute(
            select(UserScopeAssignment).where(
                UserScopeAssignment.user_id == str(user.id),
            )
        )
    ).scalars().all()

    if not assignments:
        return VisibilityScope(
            org_ids=set(), portfolio_ids=set(), program_ids=set(), project_ids=set()
        )

    org_ids: set[str] = set()
    portfolio_ids: set[str] = set()
    program_ids: set[str] = set()
    project_ids: set[str] = set()

    direct_org_ids: set[str] = set()
    direct_portfolio_ids: set[str] = set()
    direct_program_ids: set[str] = set()
    direct_project_ids: set[str] = set()

    for a in assignments:
        if a.scope_type == "organization":
            direct_org_ids.add(a.scope_id)
        elif a.scope_type == "portfolio":
            direct_portfolio_ids.add(a.scope_id)
        elif a.scope_type == "program":
            direct_program_ids.add(a.scope_id)
        elif a.scope_type == "project":
            direct_project_ids.add(a.scope_id)

    # Expand org → all portfolios + all programs + all projects
    if direct_org_ids:
        org_ids.update(direct_org_ids)
        ports = (
            await db.execute(
                select(Portfolio).where(
                    Portfolio.organization_id.in_(direct_org_ids),
                    Portfolio.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        for pf in ports:
            portfolio_ids.add(str(pf.id))
        progs = (
            await db.execute(
                select(Program).where(
                    Program.organization_id.in_(direct_org_ids),
                    Program.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        for p in progs:
            program_ids.add(str(p.id))
        # Projects in those programs
        if program_ids:
            projs = (
                await db.execute(
                    select(Project).where(
                        Project.program_id.in_(program_ids),
                        Project.tenant_id == tenant_id,
                        Project.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
            for p in projs:
                project_ids.add(str(p.id))
        # Also projects directly under the org with no program
        projs_no_prog = (
            await db.execute(
                select(Project).where(
                    Project.organization_id.in_(direct_org_ids),
                    Project.program_id.is_(None),
                    Project.tenant_id == tenant_id,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        for p in projs_no_prog:
            project_ids.add(str(p.id))

    # Expand portfolio → all programs + all projects + org visible as
    # context. No lateral reach into other portfolios of the same org.
    if direct_portfolio_ids:
        portfolio_ids.update(direct_portfolio_ids)
        ports = (
            await db.execute(
                select(Portfolio).where(
                    Portfolio.id.in_(direct_portfolio_ids),
                    Portfolio.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        for pf in ports:
            org_ids.add(str(pf.organization_id))  # org visible as context
        progs = (
            await db.execute(
                select(Program).where(
                    Program.portfolio_id.in_(direct_portfolio_ids),
                    Program.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        portfolio_program_ids: set[str] = set()
        for p in progs:
            program_ids.add(str(p.id))
            portfolio_program_ids.add(str(p.id))
        if portfolio_program_ids:
            projs = (
                await db.execute(
                    select(Project).where(
                        Project.program_id.in_(portfolio_program_ids),
                        Project.tenant_id == tenant_id,
                        Project.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
            for p in projs:
                project_ids.add(str(p.id))
        # Projects hanging directly off the portfolio (no program).
        projs_no_prog = (
            await db.execute(
                select(Project).where(
                    Project.portfolio_id.in_(direct_portfolio_ids),
                    Project.program_id.is_(None),
                    Project.tenant_id == tenant_id,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        for p in projs_no_prog:
            project_ids.add(str(p.id))

    # Expand program → all projects + org and portfolio visible as context
    if direct_program_ids:
        program_ids.update(direct_program_ids)
        progs = (
            await db.execute(
                select(Program).where(
                    Program.id.in_(direct_program_ids),
                    Program.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        for p in progs:
            org_ids.add(str(p.organization_id))  # org visible as context
            portfolio_ids.add(str(p.portfolio_id))  # portfolio visible as context
        projs = (
            await db.execute(
                select(Project).where(
                    Project.program_id.in_(direct_program_ids),
                    Project.tenant_id == tenant_id,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        for p in projs:
            project_ids.add(str(p.id))

    # Expand project → org, portfolio and program visible as context
    if direct_project_ids:
        project_ids.update(direct_project_ids)
        projs = (
            await db.execute(
                select(Project).where(
                    Project.id.in_(direct_project_ids),
                    Project.tenant_id == tenant_id,
                )
            )
        ).scalars().all()
        for p in projs:
            org_ids.add(str(p.organization_id))  # org visible as context
            if p.portfolio_id:
                portfolio_ids.add(str(p.portfolio_id))  # portfolio visible as context
            if p.program_id:
                program_ids.add(str(p.program_id))  # program visible as context

    return VisibilityScope(
        org_ids=org_ids,
        portfolio_ids=portfolio_ids,
        program_ids=program_ids,
        project_ids=project_ids,
    )
