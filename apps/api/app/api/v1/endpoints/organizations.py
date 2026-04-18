from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, conflict, forbidden, not_found
from app.db.session import get_db
from app.models.organization import Organization, Program
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _ensure_tenant(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden(detail="Acción no disponible para super admin sin tenant activo")
    return cu.user.tenant_id


@router.get("", response_model=list[OrganizationRead])
async def list_orgs(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    cu: CurrentUser = Depends(require_permission("admin.organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    stmt = select(Organization).where(Organization.tenant_id == tenant_id)
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "create")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "read")),
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


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_org(
    org_id: UUID,
    body: OrganizationUpdate,
    cu: CurrentUser = Depends(require_permission("admin.organizations", "update")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "delete")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _ensure_tenant(cu)
    stmt = select(Program).where(Program.tenant_id == tenant_id)
    if organization_id:
        stmt = stmt.where(Program.organization_id == str(organization_id))
    if is_active is not None:
        stmt = stmt.where(Program.is_active == is_active)
    rows = (await db.execute(stmt.order_by(Program.name))).scalars().all()
    return [ProgramRead.model_validate(p) for p in rows]


@programs_router.post("", response_model=ProgramRead, status_code=201)
async def create_program(
    body: ProgramCreate,
    cu: CurrentUser = Depends(require_permission("admin.organizations", "create")),
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


@programs_router.patch("/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: UUID,
    body: ProgramUpdate,
    cu: CurrentUser = Depends(require_permission("admin.organizations", "update")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "delete")),
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
