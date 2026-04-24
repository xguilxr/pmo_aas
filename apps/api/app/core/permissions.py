"""US-059 + US-060 — Sistema de roles fijos (DEC-020).

Tras DEC-020 la plataforma deja de tener roles jerárquicos dinámicos
y usa sólo 3 roles estáticos:

- `admin`: full access. Único que puede tocar Organizations, Programs
  y Users.
- `user` (default): CRUD de todo excepto Organizations / Programs /
  Users.
- `viewer`: read-only en todo.

El mapping vive en código (no BD) para evitar UI de edición compleja
en v1.3. Un admin puede ajustar casos puntuales editando el
`Role.permissions` del rol legacy asignado al usuario, pero el
comportamiento por defecto sigue este mapping.

Integración con `require_permission(module, action)`:
el `CurrentUser.has(module, action)` revisa primero `role_type` del
usuario (campo nuevo `users.role_type`) y, si está seteado, usa este
mapping. Si está en `NULL` (usuarios legacy aún sin migrar), cae a los
permisos del `Role` legacy asignado vía `user_roles`.
"""
from __future__ import annotations

from typing import Literal

RoleType = Literal["admin", "user", "viewer"]

# Acciones estándar del RBAC del backend (ver app/api/deps.py).
_CRUD = {"read", "create", "update", "delete"}
_READ = {"read"}

# Módulos que SOLO el admin puede tocar (gate duro post-DEC-020).
ADMIN_ONLY_MODULES = {
    "organizations",
    "programs",
    "users",
    "roles",
    "admin",
}

# Módulos que User puede CRUD libremente.
USER_MODULES = {
    "projects",
    "project_requests",
    "requests",
    "tasks",
    "risks",
    "issues",
    "change_requests",
    "changes",
    "documents",
    "minutes",
    "meeting_minutes",
    "reports",
    "areas",
    "project_areas",
    "lessons",
    "dashboard",
    "ai",
    "audit",
    "notifications",
}


def _admin_permissions() -> dict[str, set[str]]:
    perms: dict[str, set[str]] = {}
    for m in ADMIN_ONLY_MODULES | USER_MODULES:
        perms[m] = set(_CRUD)
    # Granularidad extra por si algún endpoint requiere acciones
    # específicas (ej. approve en change_requests, requests).
    perms.setdefault("change_requests", set()).update({"approve", "reject"})
    perms.setdefault("requests", set()).update({"approve", "reject"})
    perms.setdefault("project_requests", set()).update({"approve", "reject"})
    return perms


def _user_permissions() -> dict[str, set[str]]:
    perms: dict[str, set[str]] = {m: set(_CRUD) for m in USER_MODULES}
    # Puede aprobar en su scope (proyectos que administra como PM).
    perms.setdefault("change_requests", set()).update({"approve", "reject"})
    perms.setdefault("requests", set()).update({"approve", "reject"})
    perms.setdefault("project_requests", set()).update({"approve", "reject"})
    # Read-only en modules admin-only (puede verlos para navegación).
    for m in ADMIN_ONLY_MODULES:
        perms[m] = set(_READ)
    return perms


def _viewer_permissions() -> dict[str, set[str]]:
    perms: dict[str, set[str]] = {m: set(_READ) for m in USER_MODULES}
    for m in ADMIN_ONLY_MODULES:
        perms[m] = set(_READ)
    return perms


ROLE_PERMISSIONS: dict[RoleType, dict[str, set[str]]] = {
    "admin": _admin_permissions(),
    "user": _user_permissions(),
    "viewer": _viewer_permissions(),
}


def permissions_for(role_type: RoleType | str | None) -> dict[str, set[str]]:
    """Devuelve el mapa de permisos para un role_type. Si el role_type es
    inválido o None, retorna `viewer` (fail-safe: lo mínimo)."""
    if role_type in ROLE_PERMISSIONS:
        return ROLE_PERMISSIONS[role_type]  # type: ignore[index]
    return ROLE_PERMISSIONS["viewer"]


def flat_permissions(role_type: RoleType | str | None) -> list[str]:
    """Lista `module:action` para consumo del frontend."""
    perms = permissions_for(role_type)
    out: list[str] = []
    for m, actions in perms.items():
        for a in sorted(actions):
            out.append(f"{m}:{a}")
    return sorted(out)
