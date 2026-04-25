"""US-059 + US-060 + US-076 — role_type simplificado + capabilities endpoint.

Post-DEC-024 el modelo es capability-based. Los tests validan:
- `capabilities_for` devuelve las 5 admin capabilities solo a admin.
- `flat_permissions` en admin lista las 5 capabilities.
- El shim legacy `legacy_permissions_shim` devuelve strings module:action
  para compat con el frontend pre-US-078.
- viewer fue eliminado.
"""
import pytest

from app.core.permissions import (
    ADMIN_CAPABILITIES,
    capabilities_for,
    flat_permissions,
    legacy_permissions_shim,
)
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_capabilities_admin_has_all_five():
    caps = capabilities_for("admin")
    assert caps == ADMIN_CAPABILITIES
    assert len(caps) == 5


def test_capabilities_user_is_empty():
    assert capabilities_for("user") == frozenset()


def test_capabilities_unknown_role_is_empty():
    # viewer eliminado (DEC-024) + cualquier string extraño → set vacío (fail-safe).
    assert capabilities_for("viewer") == frozenset()
    assert capabilities_for("random-garbage") == frozenset()
    assert capabilities_for(None) == frozenset()


def test_flat_permissions_admin_lists_capabilities():
    flat = flat_permissions("admin")
    assert flat == sorted(ADMIN_CAPABILITIES)
    assert "organizations.delete" in flat
    assert "users.manage" in flat


def test_flat_permissions_user_is_empty():
    assert flat_permissions("user") == []


def test_legacy_shim_user_has_projects_crud():
    shim = legacy_permissions_shim("user")
    assert "projects:read" in shim
    assert "projects:create" in shim
    assert "projects:update" in shim
    assert "projects:delete" in shim
    # User puede crear org (solo delete es admin).
    assert "organizations:read" in shim
    assert "organizations:create" in shim
    assert "organizations:update" in shim
    assert "organizations:delete" not in shim


def test_legacy_shim_admin_has_delete_org_plus_all_user_perms():
    shim = legacy_permissions_shim("admin")
    assert "organizations:delete" in shim
    assert "users:read" in shim
    assert "users:create" in shim
    assert "users:update" in shim
    assert "users:delete" in shim
    assert "audit:read" in shim
    # Los strings legacy que el frontend viejo todavía espera.
    assert "admin.users:read" in shim
    assert "admin.roles:read" in shim


def test_legacy_shim_includes_ai_generate_and_documents_upload():
    """Los mismatches que motivaron DEC-024 quedan cubiertos por el shim."""
    shim_user = legacy_permissions_shim("user")
    assert "ai.generate:create" in shim_user
    assert "documents:upload" in shim_user


@pytest.mark.asyncio
async def test_me_permissions_endpoint_admin(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    u = await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    u.role_type = "admin"
    await db_session.commit()
    auth = await login(client, "admin", "Str0ng-Admin-1!")

    r = await client.get("/api/v1/auth/me/permissions", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role_type"] == "admin"
    # Capabilities del vocabulario nuevo.
    assert "organizations.delete" in body["capabilities"]
    assert "users.manage" in body["capabilities"]
    # Shim legacy — frontend pre-US-078 sigue funcionando.
    assert "organizations:create" in body["permissions"]
    assert "projects:read" in body["permissions"]
    assert "organizations:delete" in body["permissions"]


@pytest.mark.asyncio
async def test_user_role_type_can_create_org_but_not_delete(client, db_session):
    """Post-DEC-024 un user regular puede crear/editar organizaciones. Solo
    el delete es admin-only (capability `organizations.delete`)."""
    from app.models.role import Role

    t = await create_tenant(db_session)
    # Rol legacy vacío — el comportamiento ahora depende solo de role_type.
    open_role = Role(
        tenant_id=t.id,
        name="OpenRole",
        description="",
        permissions={},
        is_system=False,
    )
    db_session.add(open_role)
    await db_session.flush()
    u = await create_user(
        db_session,
        tenant=t,
        username="someuser",
        email="some@acme.example.com",
        password="Str0ng-User-1!",
        roles=[open_role],
    )
    u.role_type = "user"
    await db_session.commit()
    auth = await login(client, "someuser", "Str0ng-User-1!")

    # User PUEDE crear una organización (DEC-024).
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "UserCreatedOrg"},
        headers=auth["_authz"],
    )
    assert r.status_code in (200, 201), r.text
    org_id = r.json()["id"]

    # Pero NO puede borrarla (capability organizations.delete).
    r = await client.delete(
        f"/api/v1/organizations/{org_id}", headers=auth["_authz"]
    )
    assert r.status_code == 403

    # /me/permissions muestra el estado correcto.
    perms = await client.get(
        "/api/v1/auth/me/permissions", headers=auth["_authz"]
    )
    assert perms.status_code == 200
    body = perms.json()
    assert body["role_type"] == "user"
    assert body["capabilities"] == []
    flat = body["permissions"]
    assert "projects:create" in flat
    assert "organizations:create" in flat
    assert "organizations:delete" not in flat
