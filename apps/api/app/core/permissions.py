"""US-076 + DEC-024 — Modelo capability-based para permisos del admin.

Reemplaza la matriz `(role_type × module × action)` del diseño
original (DEC-020) por un set cerrado de **capabilities del admin**.

Rationale: la plataforma es una herramienta de soporte/visualización.
Todos los usuarios autenticados del tenant pueden hacer casi todo;
el admin solo difiere del user en 5 capabilities de metaconfig.

Capabilities del admin:
- `tenant.manage`         — configuración del tenant (branding, settings).
- `ai.configure`          — proveedores y modos de IA del tenant.
- `users.manage`          — alta/edición/reset/desactivación/asignación
                            rol + asignación a orgs del tenant.
- `organizations.delete`  — **solo** eliminar organizaciones.
- `audit.read`            — ver el audit log del tenant.

Todo lo demás (proyectos, tareas, riesgos, issues, change_requests,
documentos, minutas, lecciones, áreas, dashboard, IA generación,
project_requests, charters, reports, scheduled reports, importación de
planes) → cualquier user autenticado del tenant.

`viewer` eliminado (DEC-024). La migración 0028 normaliza cualquier
registro residual a `'user'`.

Integración con el gate:
- `CurrentUser.has_capability(name)` — el check principal.
- `CurrentUser.has(module, action)` — shim legacy: delega a la
  capability correspondiente si el (module, action) mapea a una, o
  devuelve True para cualquier autenticado por fail-soft del refactor.

Overrides por tenant (DEC-021 / US-073) usan el mismo mecanismo pero
con `capability` en `module` y `"grant"` en `action` a nivel de
almacenamiento (back-compat con la tabla existente). Ver `deps.py`.
"""
from __future__ import annotations

from typing import Literal

RoleType = Literal["admin", "user"]

# Set cerrado de capabilities del admin. Cualquier string no listado
# aquí lanza error al construir `require_capability()` (fail-closed).
ADMIN_CAPABILITIES: frozenset[str] = frozenset(
    {
        "tenant.manage",
        "ai.configure",
        "users.manage",
        "organizations.delete",
        "audit.read",
    }
)


def capabilities_for(role_type: RoleType | str | None) -> frozenset[str]:
    """Devuelve las capabilities del rol. Admin recibe todas, el resto
    recibe el set vacío. `None`/valor inválido → `set()` (fail-safe).
    """
    if role_type == "admin":
        return ADMIN_CAPABILITIES
    return frozenset()


def flat_permissions(role_type: RoleType | str | None) -> list[str]:
    """Lista de capability strings para consumo del frontend en
    `/auth/me/permissions`. Admin → 5 entries, user → 0 entries."""
    return sorted(capabilities_for(role_type))


# --- Shim legacy para `CurrentUser.has(module, action)` -----------------
# Mapeo opcional de (module, action) → capability. Solo se listan las
# combinaciones que históricamente diferenciaban admin de user. Cualquier
# combinación no listada se resuelve como "cualquier autenticado puede".

_MODULE_ACTION_TO_CAPABILITY: dict[tuple[str, str], str] = {
    # Tenant config
    ("admin", "read"): "tenant.manage",
    ("admin", "update"): "tenant.manage",
    ("admin", "create"): "tenant.manage",
    ("admin", "delete"): "tenant.manage",
    # Users management
    ("users", "read"): "users.manage",
    ("users", "create"): "users.manage",
    ("users", "update"): "users.manage",
    ("users", "delete"): "users.manage",
    # Roles legacy (deprecated — endpoints se borran en US-077)
    ("roles", "read"): "users.manage",
    ("roles", "create"): "users.manage",
    ("roles", "update"): "users.manage",
    ("roles", "delete"): "users.manage",
    # Organizations: SOLO delete es admin. Resto es authenticated.
    ("organizations", "delete"): "organizations.delete",
    # Audit
    ("audit", "read"): "audit.read",
    # AI config
    ("ai_config", "read"): "ai.configure",
    ("ai_config", "update"): "ai.configure",
}


def module_action_to_capability(module: str, action: str) -> str | None:
    """Resuelve si un par (module, action) del esquema legacy mapea a
    una capability admin. Retorna None si no requiere capability
    específica (cualquier autenticado puede)."""
    return _MODULE_ACTION_TO_CAPABILITY.get((module, action))


# --- Shim legacy del endpoint /auth/me/permissions ---------------------
# El frontend pre-US-076 consume `permissions: string[]` con formato
# `"module:action"`. Mientras US-078 migra el hook `useMyPermissions` al
# vocabulario de capabilities, el endpoint sigue devolviendo este set
# derivado para no romper gating de botones/links. Borrar en US-080/081.

_FREE_MODULES_CRUD = (
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
    "lessons",
    "dashboard",
    "ai",
    "notifications",
)


def legacy_permissions_shim(role_type: RoleType | str | None) -> list[str]:
    """Shim `module:action` para compat con el frontend pre-DEC-024.

    Deriva el listado a partir del modelo nuevo:
    - CRUD libre para cualquier autenticado en `_FREE_MODULES_CRUD`.
    - approve/reject/upload/generate libres para cualquier autenticado.
    - organizations: read/create/update libre; delete solo admin.
    - users/roles/admin/audit/ai_config: solo admin.
    """
    out: set[str] = set()
    for m in _FREE_MODULES_CRUD:
        for a in ("read", "create", "update", "delete"):
            out.add(f"{m}:{a}")
    for m in ("change_requests", "requests", "project_requests"):
        out.add(f"{m}:approve")
        out.add(f"{m}:reject")
    out.add("documents:upload")
    out.add("ai.generate:create")

    for a in ("read", "create", "update"):
        out.add(f"organizations:{a}")
    out.add("programs:read")
    out.add("programs:create")
    out.add("programs:update")

    if role_type == "admin":
        out.add("organizations:delete")
        out.add("programs:delete")
        for a in ("read", "create", "update", "delete"):
            out.add(f"users:{a}")
            out.add(f"admin.users:{a}")
            out.add(f"admin.roles:{a}")
            out.add(f"admin.organizations:{a}")
            out.add(f"roles:{a}")
        out.add("admin:read")
        out.add("admin:update")
        out.add("admin:create")
        out.add("admin:delete")
        out.add("audit:read")
        out.add("ai_config:read")
        out.add("ai_config:update")
    return sorted(out)
