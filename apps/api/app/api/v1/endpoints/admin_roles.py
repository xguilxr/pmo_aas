from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.errors import business_rule, conflict, forbidden, not_found, validation_error
from app.db.session import get_db
from app.models.role import Role
from app.schemas.user import RoleCreate, RoleRead, RoleUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/roles", tags=["admin.roles"])

VALID_MODULES = {
    "projects", "risks", "issues", "change_requests", "documents", "lessons", "minutes",
    "admin.users", "admin.roles", "admin.organizations", "admin.projects", "ai.generate",
    "dashboard", "admin.requests",
}
VALID_ACTIONS = {"read", "create", "update", "delete", "approve", "upload", "minute", "report"}


def _validate_permissions(perms: dict[str, list[str]]) -> None:
    for module, actions in perms.items():
        if module not in VALID_MODULES:
            raise validation_error(f"Módulo inválido: {module}")
        for a in actions:
            if a not in VALID_ACTIONS:
                raise validation_error(f"Acción inválida: {a}")


@router.get("", response_model=list[RoleRead])
async def list_roles(
    cu: CurrentUser = Depends(require_permission("admin.roles", "read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Role)
    if not cu.is_superadmin:
        stmt = stmt.where(Role.tenant_id == cu.user.tenant_id)
    rows = (await db.execute(stmt.order_by(Role.name))).scalars().all()
    return [RoleRead.model_validate(r) for r in rows]


@router.post("", response_model=RoleRead, status_code=201)
async def create_role(
    body: RoleCreate,
    cu: CurrentUser = Depends(require_permission("admin.roles", "create")),
    db: AsyncSession = Depends(get_db),
):
    if cu.user.tenant_id is None:
        raise forbidden()
    _validate_permissions(body.permissions)
    existing = (
        await db.execute(
            select(Role).where(Role.tenant_id == cu.user.tenant_id, Role.name == body.name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise conflict("Nombre de rol duplicado")

    role = Role(
        tenant_id=cu.user.tenant_id, name=body.name, description=body.description,
        permissions=body.permissions, is_system=False,
    )
    db.add(role)
    await db.flush()
    await write_audit(
        db, action="role.create", module="admin.roles", user_id=cu.id, tenant_id=cu.user.tenant_id,
        entity_type="role", entity_id=str(role.id), details={"name": role.name},
    )
    await db.commit()
    return RoleRead.model_validate(role)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: UUID,
    cu: CurrentUser = Depends(require_permission("admin.roles", "read")),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(select(Role).where(Role.id == str(role_id)))).scalar_one_or_none()
    if r is None:
        raise not_found("Rol")
    if not cu.is_superadmin and r.tenant_id != cu.user.tenant_id:
        raise forbidden()
    return RoleRead.model_validate(r)


@router.patch("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: UUID,
    body: RoleUpdate,
    cu: CurrentUser = Depends(require_permission("admin.roles", "update")),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(select(Role).where(Role.id == str(role_id)))).scalar_one_or_none()
    if r is None:
        raise not_found("Rol")
    if not cu.is_superadmin and r.tenant_id != cu.user.tenant_id:
        raise forbidden()
    if body.permissions is not None:
        _validate_permissions(body.permissions)
        r.permissions = body.permissions
    if body.name is not None:
        r.name = body.name
    if body.description is not None:
        r.description = body.description
    await write_audit(
        db, action="role.update", module="admin.roles", user_id=cu.id, tenant_id=r.tenant_id,
        entity_type="role", entity_id=str(r.id),
    )
    await db.commit()
    return RoleRead.model_validate(r)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    cu: CurrentUser = Depends(require_permission("admin.roles", "delete")),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(select(Role).where(Role.id == str(role_id)))).scalar_one_or_none()
    if r is None:
        raise not_found("Rol")
    if not cu.is_superadmin and r.tenant_id != cu.user.tenant_id:
        raise forbidden()
    if r.is_system:
        raise business_rule("No se puede borrar un rol sistema")
    await db.delete(r)
    await write_audit(
        db, action="role.delete", module="admin.roles", user_id=cu.id, tenant_id=r.tenant_id,
        entity_type="role", entity_id=str(role_id),
    )
    await db.commit()
    from fastapi.responses import Response

    return Response(status_code=204)
