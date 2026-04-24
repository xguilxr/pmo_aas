"""US-059 + US-060 — role_type simplificado + permissions endpoint."""
import pytest

from app.core.permissions import ROLE_PERMISSIONS, flat_permissions, permissions_for
from tests.factories import create_admin_role, create_tenant, create_user, login


def test_permissions_admin_has_organizations_crud():
    p = permissions_for("admin")
    assert {"create", "read", "update", "delete"}.issubset(p["organizations"])


def test_permissions_user_cannot_crud_organizations():
    p = permissions_for("user")
    assert "create" not in p.get("organizations", set())
    assert "read" in p["organizations"]


def test_permissions_user_can_crud_projects():
    p = permissions_for("user")
    assert {"create", "read", "update", "delete"}.issubset(p["projects"])


def test_permissions_viewer_read_only():
    p = permissions_for("viewer")
    for module, actions in p.items():
        assert actions == {"read"}, f"viewer tiene acciones no-read en {module}"


def test_permissions_invalid_role_type_falls_back_to_viewer():
    p = permissions_for("random-garbage")
    assert p == ROLE_PERMISSIONS["viewer"]


def test_flat_permissions_shape():
    flat = flat_permissions("user")
    assert "projects:read" in flat
    assert "organizations:read" in flat
    assert "organizations:create" not in flat


@pytest.mark.asyncio
async def test_me_permissions_endpoint(client, db_session):
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
    assert "organizations:create" in body["permissions"]
    assert "projects:read" in body["permissions"]


@pytest.mark.asyncio
async def test_user_role_type_blocks_admin_endpoints(client, db_session):
    from app.models.role import Role, UserRole

    t = await create_tenant(db_session)
    # Rol ultra-permisivo legacy — pero el user tendrá role_type=user,
    # que en deps.py tiene precedencia → bloquea.
    open_role = Role(
        tenant_id=t.id,
        name="OpenRole",
        description="",
        permissions={"organizations": ["read", "create", "update", "delete"]},
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

    # User intenta crear Organization → 403 (gate por role_type).
    r = await client.post(
        "/api/v1/organizations",
        json={"name": "NoPuede"},
        headers=auth["_authz"],
    )
    assert r.status_code == 403

    # Pero SÍ puede crear un proyecto (tras crear la org con admin real,
    # aquí nos basta con verificar el gate del module).
    perms = await client.get(
        "/api/v1/auth/me/permissions", headers=auth["_authz"]
    )
    assert perms.status_code == 200
    flat = perms.json()["permissions"]
    assert "projects:create" in flat
    assert "organizations:create" not in flat
