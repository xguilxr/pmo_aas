from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.role import Role, UserRole
from app.models.user import User


class CurrentUser:
    def __init__(
        self,
        user: User,
        tenant_ids: list[UUID],
        active_tenant_id: UUID | None,
        roles: list[str],
        permissions: dict[str, set[str]],
    ) -> None:
        self.user = user
        self.tenant_ids = tenant_ids
        self.active_tenant_id = active_tenant_id
        self.roles = roles
        self.permissions = permissions

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def is_superadmin(self) -> bool:
        return self.user.is_superadmin

    def has(self, module: str, action: str) -> bool:
        if self.is_superadmin:
            return True
        return action in self.permissions.get(module, set())


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized()
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise unauthorized()
    if payload.get("type") != "access":
        raise unauthorized()
    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized()

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized(code="USER_INACTIVE", detail="Usuario inactivo")

    role_rows = (
        await db.execute(
            select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        )
    ).scalars().all()
    role_names = [r.name for r in role_rows]
    perms: dict[str, set[str]] = {}
    for r in role_rows:
        for module, actions in (r.permissions or {}).items():
            perms.setdefault(module, set()).update(actions)

    tenant_ids_raw = payload.get("tenant_ids", []) or []
    active_raw = payload.get("active_tenant_id")
    return CurrentUser(
        user=user,
        tenant_ids=[UUID(t) for t in tenant_ids_raw],
        active_tenant_id=UUID(active_raw) if active_raw else None,
        roles=role_names,
        permissions=perms,
    )


def require_permission(module: str, action: str):
    async def _checker(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not cu.has(module, action):
            raise forbidden(code="FORBIDDEN", detail=f"Falta permiso {module}:{action}")
        return cu

    return _checker


async def get_superadmin(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not cu.is_superadmin:
        raise forbidden(code="FORBIDDEN", detail="Solo super admin")
    return cu
