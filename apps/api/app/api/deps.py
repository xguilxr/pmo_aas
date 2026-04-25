from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import forbidden, unauthorized
from app.core.permissions import (
    ADMIN_CAPABILITIES,
    capabilities_for,
    module_action_to_capability,
)
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.tenant_permission import TenantRolePermissionOverride
from app.models.user import User


class CurrentUser:
    def __init__(
        self,
        user: User,
        tenant_ids: list[UUID],
        active_tenant_id: UUID | None,
        # US-073 + DEC-021: overrides de capabilities por tenant.
        # Estructura post-DEC-024: {role_type: {capability: granted_bool}}.
        # Compatibilidad: las filas existentes de la tabla usan
        # (role_type, module, action, granted); a partir de ahora
        # `module` contiene la capability completa y `action` se setea
        # en `"grant"`. Ver `_load_overrides()`.
        capability_overrides: dict[str, dict[str, bool]] | None = None,
    ) -> None:
        self.user = user
        self.tenant_ids = tenant_ids
        self.active_tenant_id = active_tenant_id
        self.capability_overrides = capability_overrides or {}

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def is_superadmin(self) -> bool:
        return self.user.is_superadmin

    @property
    def role_type(self) -> str | None:
        """US-059 + US-076 — rol fijo ∈ {admin, user}. viewer eliminado
        por DEC-024 (migración 0028 normaliza cualquier residual a
        'user'). None solo para users pre-migración aún sin role_type."""
        return getattr(self.user, "role_type", None)

    def has_capability(self, name: str) -> bool:
        """Chequeo principal post-DEC-024. Aplica overrides de tenant
        si existen. Fail-closed: capability no listada en
        `ADMIN_CAPABILITIES` devuelve False salvo superadmin."""
        if self.is_superadmin:
            return True
        if name not in ADMIN_CAPABILITIES:
            return False
        rt = self.role_type or "user"
        base = name in capabilities_for(rt)
        override = self.capability_overrides.get(rt, {}).get(name)
        if override is True:
            return True
        if override is False:
            return False
        return base

    def has(self, module: str, action: str) -> bool:
        """Shim legacy. Post-DEC-024 el gate real es
        `has_capability()`. Esta función:

        1. Superadmin → True.
        2. Si (module, action) mapea a una capability conocida → delega
           a `has_capability()`.
        3. Si no mapea → True para cualquier user autenticado (modelo
           "todos pueden todo salvo las 5 capabilities admin").
        """
        if self.is_superadmin:
            return True
        cap = module_action_to_capability(module, action)
        if cap is not None:
            return self.has_capability(cap)
        # Por default cualquier user autenticado puede.
        return True

    @property
    def is_admin_equivalent(self) -> bool:
        """True si el user tiene role_type admin o es superadmin.
        Post-DEC-024 ya no depende de roles legacy ni de strings
        `admin.*` en el JSON permissions."""
        if self.is_superadmin:
            return True
        return self.role_type == "admin"

    @property
    def roles(self) -> list[str]:
        """Shim legacy. Pre-DEC-024 era la lista de nombres de Role del
        user; hoy se deriva de `role_type`. Lo usan 2 endpoints para
        propagar el claim al access_token. Borrar en US-081."""
        if self.is_superadmin:
            return ["superadmin"]
        if self.role_type == "admin":
            return ["Administrador"]
        return []


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

    tenant_ids_raw = payload.get("tenant_ids", []) or []
    active_raw = payload.get("active_tenant_id")
    active_tenant_id = UUID(active_raw) if active_raw else None

    # US-073 + DEC-021 + DEC-024: precargar overrides de capabilities
    # del tenant activo. La tabla `tenant_role_permission_overrides`
    # se reinterpreta: `module` guarda la capability completa
    # (ej. "organizations.delete") y `action` se usa como discriminante
    # fijo. Filas legacy con action ≠ "grant" se ignoran (se limpiarán
    # en US-080/081).
    capability_overrides: dict[str, dict[str, bool]] = {}
    if active_tenant_id is not None and not user.is_superadmin:
        rows = (
            await db.execute(
                select(TenantRolePermissionOverride).where(
                    TenantRolePermissionOverride.tenant_id == str(active_tenant_id)
                )
            )
        ).scalars().all()
        for r in rows:
            # Solo overrides "grant" sobre capabilities conocidas del
            # modelo nuevo. Los legacy (module/action arbitrarios) se
            # ignoran silenciosamente.
            if r.module in ADMIN_CAPABILITIES:
                capability_overrides.setdefault(r.role_type, {})[r.module] = r.granted

    return CurrentUser(
        user=user,
        tenant_ids=[UUID(t) for t in tenant_ids_raw],
        active_tenant_id=active_tenant_id,
        capability_overrides=capability_overrides,
    )


def require_capability(name: str):
    """Dependencia FastAPI que exige una capability específica.

    Fail-closed: si `name` no está en `ADMIN_CAPABILITIES`, lanza
    `ValueError` al construir la dependencia (error de programación)
    para prevenir strings inexistentes como los que causaron el bug
    que motivó DEC-024 (`ai.generate`, `documents.upload`).
    """
    if name not in ADMIN_CAPABILITIES:
        raise ValueError(
            f"capability desconocida: {name!r}. Lista válida: "
            f"{sorted(ADMIN_CAPABILITIES)}"
        )

    async def _checker(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not cu.has_capability(name):
            raise forbidden(code="FORBIDDEN", detail=f"Falta capability {name}")
        return cu

    # US-079: marca para que `test_permission_matrix.py` clasifique este
    # gate sin parsear closures.
    _checker.__pmoaas_gate__ = ("capability", name)  # type: ignore[attr-defined]
    return _checker


def require_authenticated():
    """Cualquier user autenticado del tenant. No chequea capability."""

    async def _checker(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        return cu

    _checker.__pmoaas_gate__ = ("authenticated",)  # type: ignore[attr-defined]
    return _checker


def require_permission(module: str, action: str):
    """Shim legacy. Se mantiene para compat con tests o llamadas no
    migradas aún. Resuelve internamente a `require_capability()` o
    `require_authenticated()` según el mapping de DEC-024.

    TODO US-081 — borrar esta función y sus usos residuales.
    """
    cap = module_action_to_capability(module, action)

    async def _checker(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if cap is not None:
            if not cu.has_capability(cap):
                raise forbidden(
                    code="FORBIDDEN", detail=f"Falta capability {cap}"
                )
        return cu

    _checker.__pmoaas_gate__ = (  # type: ignore[attr-defined]
        ("capability", cap) if cap is not None else ("authenticated",)
    )
    return _checker


async def get_superadmin(cu: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not cu.is_superadmin:
        raise forbidden(code="FORBIDDEN", detail="Solo super admin")
    return cu


# Marca para `get_superadmin` y `get_current_user` (no son factory, son
# funciones directas).
get_superadmin.__pmoaas_gate__ = ("superadmin",)  # type: ignore[attr-defined]
get_current_user.__pmoaas_gate__ = ("authenticated",)  # type: ignore[attr-defined]
