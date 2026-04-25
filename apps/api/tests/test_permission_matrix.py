"""US-079 + DEC-024 — test de matriz role × endpoint.

Verifica dos garantías:

1. **Inventario completo** — cada endpoint protegido del API cae en
   una de las 8 categorías conocidas (5 capabilities admin +
   `authenticated` + `superadmin` + `public`). Si aparece un endpoint
   con un gate desconocido (ej. cualquier `Depends(...)` que no marque
   `__pmoaas_gate__`) o sin marcar como público, el test falla con un
   mensaje explícito. Esto previene los bugs que motivaron DEC-024:
   un endpoint pidiendo `ai.generate:create` sin entrada en el
   mapping → 403 silencioso para todos.

2. **Comportamiento por actor** — un sample dirigido por cada
   categoría confirma que admin/user/anon reciben el status esperado.
   No se ejerce el set completo de 188 endpoints porque construir
   bodies válidos para todos es prohibitivo; el sample por categoría
   más el inventario estático garantiza cobertura semántica.

Para que un endpoint pase la verificación de inventario, su
dependency tree debe incluir uno de:
- `require_capability("X")`, donde X ∈ ADMIN_CAPABILITIES.
- `require_authenticated()`.
- `get_current_user` (uso legacy, equivalente a authenticated).
- `get_superadmin`.
- O estar listado en `PUBLIC_ENDPOINTS` abajo.
"""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from app.api.deps import CurrentUser
from app.core.permissions import ADMIN_CAPABILITIES
from app.main import app
from tests.factories import create_admin_role, create_tenant, create_user, login

pytestmark = pytest.mark.permissions

# ---------------------------------------------------------------------
# Inventario estático
# ---------------------------------------------------------------------

# Endpoints sin auth — listado explícito. Cualquier endpoint nuevo sin
# `__pmoaas_gate__` que no esté aquí hace fallar el test.
PUBLIC_ENDPOINTS: set[tuple[str, str]] = {
    ("GET", "/health"),
    ("GET", "/api/v1/ping"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/forgot-password"),  # US-063
    ("POST", "/api/v1/auth/reset-password"),  # US-063
}


def _route_gate_label(route: APIRoute) -> str | None:
    """Inspecciona el dependency tree de la ruta y devuelve un label
    canónico de la categoría de gate. None si no hay gate identificado.
    """
    deps = list(getattr(route.dependant, "dependencies", []) or [])
    seen: set[int] = set()
    while deps:
        d = deps.pop()
        cb = getattr(d, "call", None)
        if cb is None or id(cb) in seen:
            continue
        seen.add(id(cb))
        gate = getattr(cb, "__pmoaas_gate__", None)
        if gate is not None:
            kind = gate[0]
            if kind == "capability":
                return f"capability:{gate[1]}"
            return kind  # authenticated | superadmin
        # Recurse en dependencias internas.
        deps.extend(getattr(d, "dependencies", []) or [])
    return None


def _all_protected_routes() -> list[tuple[str, str, str]]:
    """Lista `(method, path, gate_label)` para cada ruta del API."""
    out: list[tuple[str, str, str]] = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        for method in r.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            gate = _route_gate_label(r)
            if gate is None:
                if (method, r.path) in PUBLIC_ENDPOINTS:
                    out.append((method, r.path, "public"))
                else:
                    out.append((method, r.path, "UNKNOWN"))
            else:
                out.append((method, r.path, gate))
    return out


def test_inventario_completo_cada_endpoint_tiene_gate_clasificable():
    """Un endpoint sin `__pmoaas_gate__` y sin entrada en
    PUBLIC_ENDPOINTS → fallo explícito con la lista de huérfanos.
    """
    rows = _all_protected_routes()
    unknown = [(m, p) for m, p, g in rows if g == "UNKNOWN"]
    assert not unknown, (
        f"Endpoints sin gate clasificable ({len(unknown)}). Agregar a "
        f"PUBLIC_ENDPOINTS o usar require_capability/require_authenticated/"
        f"get_superadmin: {unknown[:10]}"
    )


def test_inventario_solo_5_capabilities_admin():
    """Cualquier `capability:X` debe ser una de las 5 oficiales. Si
    aparece `capability:foo.bar` el test falla — fail-closed contra
    strings inexistentes (la causa raíz de DEC-024)."""
    rows = _all_protected_routes()
    bad: list[tuple[str, str, str]] = []
    for m, p, g in rows:
        if g.startswith("capability:"):
            cap = g.split(":", 1)[1]
            if cap not in ADMIN_CAPABILITIES:
                bad.append((m, p, g))
    assert not bad, (
        f"Endpoints con capability fuera del set ADMIN_CAPABILITIES: {bad}"
    )


def test_inventario_distribucion_de_categorias_es_razonable():
    """Spot-check: que existan endpoints en cada categoría esperada y
    no haya migraciones perdidas."""
    rows = _all_protected_routes()
    by_label: dict[str, int] = {}
    for _m, _p, g in rows:
        by_label[g] = by_label.get(g, 0) + 1
    assert by_label.get("authenticated", 0) > 50, (
        f"Esperaba muchos endpoints `authenticated` post-DEC-024, "
        f"distribución: {by_label}"
    )
    assert by_label.get("capability:users.manage", 0) >= 5
    assert by_label.get("capability:tenant.manage", 0) >= 2
    assert by_label.get("capability:ai.configure", 0) >= 1
    assert by_label.get("capability:organizations.delete", 0) >= 1
    assert by_label.get("capability:audit.read", 0) >= 1
    assert by_label.get("superadmin", 0) >= 5
    assert by_label.get("public", 0) >= 5


def test_currentuser_construye_correctamente():
    """Smoke-test mínimo del helper que se usa en el resto del file."""
    u = type("U", (), {"is_superadmin": False, "role_type": "admin"})()
    cu = CurrentUser(user=u, tenant_ids=[], active_tenant_id=None)
    assert cu.has_capability("users.manage")
    assert not cu.has_capability("organizations.delete") is False  # admin sí
    u2 = type("U", (), {"is_superadmin": False, "role_type": "user"})()
    cu2 = CurrentUser(user=u2, tenant_ids=[], active_tenant_id=None)
    assert not cu2.has_capability("users.manage")


# ---------------------------------------------------------------------
# Smoke dinámico — sample dirigido por categoría
# ---------------------------------------------------------------------


@pytest.fixture
async def actors(client, db_session):
    """Crea tenant + admin + user + sus auth headers."""
    t = await create_tenant(db_session, slug="permmatrix")
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="matrixadmin",
        email="matrixadmin@perm.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
        role_type="admin",
    )
    await create_user(
        db_session,
        tenant=t,
        username="matrixuser",
        email="matrixuser@perm.example.com",
        password="Str0ng-User-1!",
        role_type="user",
    )
    admin_auth = await login(client, "matrixadmin", "Str0ng-Admin-1!")
    user_auth = await login(client, "matrixuser", "Str0ng-User-1!")
    return {"tenant": t, "admin": admin_auth, "user": user_auth}


@pytest.mark.asyncio
async def test_anon_recibe_401_en_endpoint_protegido(client):
    """Sin Authorization header, cualquier endpoint protegido → 401."""
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_pasa_capability_users_manage(client, actors):
    """admin con users.manage puede listar users."""
    r = await client.get(
        "/api/v1/admin/users", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_user_falla_capability_users_manage(client, actors):
    """user sin capability recibe 403 en /admin/users."""
    r = await client.get(
        "/api/v1/admin/users", headers=actors["user"]["_authz"]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_pasa_capability_tenant_manage(client, actors):
    """admin con tenant.manage puede leer config del tenant."""
    r = await client.get(
        "/api/v1/admin/tenant", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_user_falla_capability_tenant_manage(client, actors):
    r = await client.get(
        "/api/v1/admin/tenant", headers=actors["user"]["_authz"]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_pasa_capability_ai_configure(client, actors):
    r = await client.get(
        "/api/v1/admin/ai/provider", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_user_falla_capability_ai_configure(client, actors):
    r = await client.get(
        "/api/v1/admin/ai/provider", headers=actors["user"]["_authz"]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_pasa_capability_audit_read(client, actors):
    r = await client.get(
        "/api/v1/admin/audit-logs", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_user_falla_capability_audit_read(client, actors):
    r = await client.get(
        "/api/v1/admin/audit-logs", headers=actors["user"]["_authz"]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_user_puede_crear_organizacion_pero_no_borrar(client, actors):
    """`organizations.delete` es la única capability admin sobre orgs.
    Crear/editar lo hace cualquier user."""
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "MatrixOrg"},
        headers=actors["user"]["_authz"],
    )
    assert r.status_code in (200, 201), r.text
    org_id = r.json()["id"]
    r = await client.delete(
        f"/api/v1/organizations/{org_id}", headers=actors["user"]["_authz"]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_puede_borrar_organizacion(client, actors):
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "ToDelete"},
        headers=actors["admin"]["_authz"],
    )
    assert r.status_code in (200, 201)
    org_id = r.json()["id"]
    r = await client.delete(
        f"/api/v1/organizations/{org_id}", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_endpoint_authenticated_no_requiere_capability(client, actors):
    """Cualquier user autenticado del tenant puede listar proyectos."""
    r = await client.get(
        "/api/v1/projects", headers=actors["user"]["_authz"]
    )
    assert r.status_code == 200, r.text
    r = await client.get(
        "/api/v1/projects", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_endpoint_ai_generate_ya_no_es_admin_only(client, actors):
    """El bug que motivó DEC-024 quedó resuelto: user puede llamar
    /ai/generate (era 403 con `ai.generate:create` huérfano)."""
    # POST sin body válido → 422 esperado, NO 403. Ese es el indicador
    # de que el gate dejó pasar al user.
    r = await client.post(
        "/api/v1/ai/generate-minute",
        json={},
        headers=actors["user"]["_authz"],
    )
    assert r.status_code != 403, (
        f"user fue rechazado por gate en /ai/generate-minute (status "
        f"{r.status_code}). Esperaba 422/200/4xx (gate ok)."
    )


@pytest.mark.asyncio
async def test_superadmin_endpoints_rechazan_admin_normal(client, actors):
    """admin tenant != superadmin: gate `get_superadmin` rechaza."""
    r = await client.get(
        "/api/v1/superadmin/tenants", headers=actors["admin"]["_authz"]
    )
    assert r.status_code == 403
