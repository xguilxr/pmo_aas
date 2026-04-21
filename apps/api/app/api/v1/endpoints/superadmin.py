import secrets
import string
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_superadmin
from app.core.errors import business_rule, conflict, forbidden, not_found, validation_error
from app.core.security import (
    create_access_token,
    hash_password,
    validate_password_policy,
)
from app.db.session import get_db
from app.models.organization import Program
from app.models.role import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.organization import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRead,
)
from app.services.audit import write_audit
from app.services.seed import SYSTEM_ROLES

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    # Garantizar cumple política
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        ok, _ = validate_password_policy(pwd)
        if ok:
            return pwd


@router.post("/provision", response_model=TenantProvisionResponse, status_code=201)
async def provision_tenant(
    body: TenantProvisionRequest,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    slug = body.slug.lower()
    existing = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if existing is not None:
        raise conflict("slug de tenant duplicado", code="SLUG_DUPLICATE")

    tenant = Tenant(slug=slug, name=body.name, is_active=True, settings={})
    db.add(tenant)
    await db.flush()

    admin_role = None
    for r in SYSTEM_ROLES:
        role = Role(
            tenant_id=tenant.id, name=r["name"], description=r["description"],
            permissions=r["permissions"], is_system=True,
        )
        db.add(role)
        await db.flush()
        if r["name"] == "Administrador":
            admin_role = role

    pwd = body.admin_password or _random_password()
    ok, err = validate_password_policy(pwd)
    if not ok:
        raise validation_error("admin_password débil", {"code": err})

    username = (body.admin_username or body.admin_email.split("@")[0]).lower()
    user = User(
        tenant_id=tenant.id,
        username=username,
        email=body.admin_email.lower(),
        full_name=body.admin_full_name,
        password_hash=hash_password(pwd),
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))

    await write_audit(
        db, action="tenant.provisioned", module="superadmin", user_id=cu.id,
        entity_type="tenant", entity_id=str(tenant.id),
        details={"slug": slug, "admin_user_id": str(user.id)},
    )
    await db.commit()
    return TenantProvisionResponse(
        tenant_id=tenant.id, slug=slug, admin_user_id=user.id, admin_password=pwd,
    )


@router.get("/tenants", response_model=list[TenantRead])
async def list_tenants(
    include_inactive: bool = Query(default=False),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.organization import Organization
    from app.models.project import Project

    stmt = select(Tenant)
    if not include_inactive:
        stmt = stmt.where(Tenant.is_active.is_(True))
    tenants = (await db.execute(stmt.order_by(Tenant.slug))).scalars().all()
    if not tenants:
        return []

    tenant_ids = [t.id for t in tenants]

    # Counts por tenant en batch (US-025).
    def grouped(stmt):
        return {str(tid): int(n) for tid, n in stmt}

    users_rows = (
        await db.execute(
            select(User.tenant_id, func.count(User.id))
            .where(User.tenant_id.in_(tenant_ids))
            .group_by(User.tenant_id)
        )
    ).all()
    user_counts = grouped(users_rows)

    orgs_rows = (
        await db.execute(
            select(Organization.tenant_id, func.count(Organization.id))
            .where(Organization.tenant_id.in_(tenant_ids))
            .group_by(Organization.tenant_id)
        )
    ).all()
    org_counts = grouped(orgs_rows)

    progs_rows = (
        await db.execute(
            select(Program.tenant_id, func.count(Program.id))
            .where(Program.tenant_id.in_(tenant_ids))
            .group_by(Program.tenant_id)
        )
    ).all()
    program_counts = grouped(progs_rows)

    projs_rows = (
        await db.execute(
            select(Project.tenant_id, func.count(Project.id))
            .where(
                Project.tenant_id.in_(tenant_ids), Project.deleted_at.is_(None)
            )
            .group_by(Project.tenant_id)
        )
    ).all()
    project_counts = grouped(projs_rows)

    out: list[TenantRead] = []
    for t in tenants:
        tid = str(t.id)
        out.append(
            TenantRead(
                id=t.id,
                slug=t.slug,
                name=t.name,
                is_active=t.is_active,
                user_count=user_counts.get(tid, 0),
                organization_count=org_counts.get(tid, 0),
                program_count=program_counts.get(tid, 0),
                project_count=project_counts.get(tid, 0),
            )
        )
    return out


@router.get("/tenants/{tenant_id}/detail")
async def tenant_detail(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    users = (
        await db.execute(
            select(User.id, User.username, User.email, User.is_active).where(User.tenant_id == t.id)
        )
    ).all()
    from app.models.organization import Organization

    orgs = (
        await db.execute(
            select(Organization.id, Organization.name, Organization.is_active).where(
                Organization.tenant_id == t.id
            )
        )
    ).all()
    programs = (
        await db.execute(
            select(Program.id, Program.name, Program.organization_id).where(Program.tenant_id == t.id)
        )
    ).all()
    # Jerarquía: counts globales por tenant (US-025).
    from app.models.organization import BusinessUnit, Department
    from app.models.project import Project

    bu_count = (
        await db.execute(
            select(func.count(BusinessUnit.id)).where(
                BusinessUnit.tenant_id == t.id, BusinessUnit.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0
    dept_count = (
        await db.execute(
            select(func.count(Department.id)).where(
                Department.tenant_id == t.id, Department.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0
    project_count = (
        await db.execute(
            select(func.count(Project.id)).where(
                Project.tenant_id == t.id, Project.deleted_at.is_(None)
            )
        )
    ).scalar_one() or 0

    return {
        "tenant": {"id": str(t.id), "slug": t.slug, "name": t.name, "is_active": t.is_active},
        "users": [{"id": str(r.id), "username": r.username, "email": r.email, "is_active": r.is_active} for r in users],
        "organizations": [{"id": str(r.id), "name": r.name, "is_active": r.is_active} for r in orgs],
        "programs": [{"id": str(r.id), "name": r.name, "organization_id": str(r.organization_id)} for r in programs],
        "hierarchy": {
            "organization_count": len(orgs),
            "business_unit_count": int(bu_count),
            "department_count": int(dept_count),
            "program_count": len(programs),
            "project_count": int(project_count),
        },
    }


@router.delete("/tenants/{tenant_id}", status_code=204)
async def soft_delete_tenant(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    t.is_active = False
    await write_audit(
        db, action="tenant.soft_delete", module="superadmin", user_id=cu.id,
        entity_type="tenant", entity_id=str(t.id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.delete("/tenants/{tenant_id}/permanent", status_code=204)
async def hard_delete_tenant(
    tenant_id: UUID,
    confirm_slug: str = Query(...),
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    if confirm_slug != t.slug:
        raise business_rule("confirm_slug no coincide con el slug del tenant")
    await write_audit(
        db, action="tenant.hard_delete", module="superadmin", user_id=cu.id,
        entity_type="tenant", entity_id=str(t.id), details={"slug": t.slug},
    )
    await db.delete(t)  # cascade elimina todo
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)


@router.post("/tenants/{tenant_id}/join-as-admin")
async def join_as_admin(
    tenant_id: UUID,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    admin_role = (
        await db.execute(
            select(Role).where(Role.tenant_id == t.id, Role.name == "Administrador")
        )
    ).scalar_one_or_none()
    if admin_role is None:
        raise business_rule("Tenant no tiene rol Administrador; re-seed")

    existing_ur = (
        await db.execute(
            select(UserRole).where(UserRole.user_id == cu.id, UserRole.role_id == admin_role.id)
        )
    ).scalar_one_or_none()
    if existing_ur is None:
        db.add(UserRole(user_id=cu.id, role_id=admin_role.id))

    await write_audit(
        db, action="superadmin.join_as_admin", module="superadmin", user_id=cu.id,
        tenant_id=t.id, entity_type="tenant", entity_id=str(t.id),
    )
    await db.commit()

    access = create_access_token(
        subject=cu.id,
        tenant_ids=[str(t.id)],
        active_tenant_id=str(t.id),
        is_superadmin=True,
        roles=cu.roles + ["Administrador"],
    )
    return {"access_token": access, "active_tenant_id": str(t.id), "tenant_slug": t.slug}
