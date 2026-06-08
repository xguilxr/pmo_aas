"""US-167/168 — Utilidad de visibilidad de recursos por usuario.

Para usuarios PM (role_type='user') la visibilidad está restringida a los
recursos asignados en `user_scope_assignments`, con herencia hacia abajo:
- Org → todos sus programas y proyectos del tenant.
- Program → todos sus proyectos + la org padre (visible como contexto).
- Project → solo ese proyecto + programa y org padre (visible como contexto).

Admin, pm_sr y superadmin ignoran la tabla — siempre ven todo (retorna None).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import _ADMIN_EQUIVALENT_ROLES
from app.models.organization import Program
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
        return VisibilityScope(org_ids=set(), program_ids=set(), project_ids=set())

    assignments = (
        await db.execute(
            select(UserScopeAssignment).where(
                UserScopeAssignment.user_id == str(user.id),
            )
        )
    ).scalars().all()

    if not assignments:
        return VisibilityScope(org_ids=set(), program_ids=set(), project_ids=set())

    org_ids: set[str] = set()
    program_ids: set[str] = set()
    project_ids: set[str] = set()

    direct_org_ids: set[str] = set()
    direct_program_ids: set[str] = set()
    direct_project_ids: set[str] = set()

    for a in assignments:
        if a.scope_type == "organization":
            direct_org_ids.add(a.scope_id)
        elif a.scope_type == "program":
            direct_program_ids.add(a.scope_id)
        elif a.scope_type == "project":
            direct_project_ids.add(a.scope_id)

    # Expand org → all programs + all projects in those programs
    if direct_org_ids:
        org_ids.update(direct_org_ids)
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

    # Expand program → all projects + org visible as context
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

    # Expand project → org + program visible as context
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
            if p.program_id:
                program_ids.add(str(p.program_id))  # program visible as context

    return VisibilityScope(
        org_ids=org_ids,
        program_ids=program_ids,
        project_ids=project_ids,
    )
