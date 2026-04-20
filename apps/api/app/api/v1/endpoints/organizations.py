from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, conflict, forbidden, not_found
from app.db.session import get_db
from app.models.organization import BusinessUnit, Department, Organization, Program
from app.schemas.organization import (
    BusinessUnitCreate,
    BusinessUnitRead,
    BusinessUnitUpdate,
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


# -- Business Units (US-NEW-003) ----
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "update")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "read")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "read")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "update")),
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
    cu: CurrentUser = Depends(require_permission("admin.organizations", "delete")),
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
    from datetime import datetime, timezone

    bu.deleted_at = datetime.now(timezone.utc)
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
