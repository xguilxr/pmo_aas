"""US-078 + DEC-024 — gestión de users + capability users.manage +
membership opt-out de organizaciones.

Tests críticos del scope:
- Create con role_type explícito.
- Update de role_type via PATCH.
- Force password change (sin tocar password actual).
- Excluded organizations: GET, PUT (replace), default = ninguna.
- Aislamiento: tenant A no puede excluir orgs de tenant B.
"""
import pytest

from app.models.organization import Organization
from app.models.organization_user_exclusion import OrganizationUserExclusion
from sqlalchemy import select
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin_setup(client, db_session, slug="us078"):
    t = await create_tenant(db_session, slug=slug)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin78",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
        role_type="admin",
    )
    auth = await login(client, "admin78", "Str0ng-Admin-1!")
    return t, auth


async def _make_org(db_session, tenant, name):
    o = Organization(tenant_id=tenant.id, name=name, is_active=True)
    db_session.add(o)
    await db_session.commit()
    return o


@pytest.mark.asyncio
async def test_create_user_with_role_type_admin(client, db_session):
    _t, auth = await _admin_setup(client, db_session, slug="us078a")
    r = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "New Admin",
            "username": "newadmin",
            "email": "newadmin@us078a.example.com",
            "password": "Str0ng-NewA-1!",
            "role_ids": [],
            "is_active": True,
            "role_type": "admin",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role_type"] == "admin"


@pytest.mark.asyncio
async def test_update_user_role_type_admin_to_user(client, db_session):
    t, auth = await _admin_setup(client, db_session, slug="us078b")
    target = await create_user(
        db_session,
        tenant=t,
        username="targetuser",
        email="target@us078b.example.com",
        password="Str0ng-Targ-1!",
        role_type="admin",
    )
    r = await client.patch(
        f"/api/v1/admin/users/{target.id}",
        json={"role_type": "user"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["role_type"] == "user"


@pytest.mark.asyncio
async def test_force_password_change_does_not_touch_password(client, db_session):
    t, auth = await _admin_setup(client, db_session, slug="us078c")
    target = await create_user(
        db_session,
        tenant=t,
        username="userforce",
        email="userforce@us078c.example.com",
        password="Str0ng-Force-1!",
    )
    original_hash = target.password_hash

    r = await client.post(
        f"/api/v1/admin/users/{target.id}/force-password-change",
        headers=auth["_authz"],
    )
    assert r.status_code == 204

    # Password actual sigue funcionando + must_change_password = True.
    auth_target = await login(client, "userforce", "Str0ng-Force-1!")
    assert auth_target["user"]["must_change_password"] is True

    # Hash en DB no cambió (only flag).
    await db_session.refresh(target)
    assert target.password_hash == original_hash
    assert target.must_change_password is True


@pytest.mark.asyncio
async def test_force_password_change_via_patch_only_flag(client, db_session):
    """`PATCH /admin/users/{id}` con `must_change_password=true` también
    funciona (mismo efecto que el endpoint dedicado). Permite UI más
    flexible."""
    t, auth = await _admin_setup(client, db_session, slug="us078d")
    target = await create_user(
        db_session,
        tenant=t,
        username="userpatch",
        email="userpatch@us078d.example.com",
        password="Str0ng-Patch-1!",
    )
    r = await client.patch(
        f"/api/v1/admin/users/{target.id}",
        json={"must_change_password": True},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_excluded_organizations_default_empty(client, db_session):
    t, auth = await _admin_setup(client, db_session, slug="us078e")
    target = await create_user(
        db_session,
        tenant=t,
        username="userexcl",
        email="userexcl@us078e.example.com",
        password="Str0ng-Excl-1!",
    )
    r = await client.get(
        f"/api/v1/admin/users/{target.id}/excluded-organizations",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["organization_ids"] == []


@pytest.mark.asyncio
async def test_excluded_organizations_replace_set(client, db_session):
    t, auth = await _admin_setup(client, db_session, slug="us078f")
    target = await create_user(
        db_session,
        tenant=t,
        username="userexclrepl",
        email="userexclrepl@us078f.example.com",
        password="Str0ng-Excl-1!",
    )
    org_a = await _make_org(db_session, t, "OrgA")
    org_b = await _make_org(db_session, t, "OrgB")

    # PUT con [org_a, org_b]
    r = await client.put(
        f"/api/v1/admin/users/{target.id}/excluded-organizations",
        json={"organization_ids": [str(org_a.id), str(org_b.id)]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert set(r.json()["organization_ids"]) == {str(org_a.id), str(org_b.id)}

    # PUT con [] limpia
    r = await client.put(
        f"/api/v1/admin/users/{target.id}/excluded-organizations",
        json={"organization_ids": []},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["organization_ids"] == []

    # En DB no hay residuo.
    rows = (
        await db_session.execute(
            select(OrganizationUserExclusion).where(
                OrganizationUserExclusion.user_id == str(target.id)
            )
        )
    ).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_excluded_organizations_rejects_org_from_other_tenant(
    client, db_session
):
    """No permitir excluir una org de un tenant ajeno (validación)."""
    t_a, auth_a = await _admin_setup(client, db_session, slug="us078g-a")
    t_b = await create_tenant(db_session, slug="us078g-b")
    target = await create_user(
        db_session,
        tenant=t_a,
        username="usergh",
        email="usergh@us078g-a.example.com",
        password="Str0ng-User-1!",
    )
    org_other = await _make_org(db_session, t_b, "OrgOther")

    r = await client.put(
        f"/api/v1/admin/users/{target.id}/excluded-organizations",
        json={"organization_ids": [str(org_other.id)]},
        headers=auth_a["_authz"],
    )
    # `validation_error()` del backend retorna 400 con code VALIDATION_ERROR.
    assert r.status_code == 400, r.text
    assert "no pertenecen" in r.text.lower()


@pytest.mark.asyncio
async def test_user_regular_no_puede_gestionar_users(client, db_session):
    t, _admin_auth = await _admin_setup(client, db_session, slug="us078h")
    await create_user(
        db_session,
        tenant=t,
        username="regular78",
        email="regular@us078h.example.com",
        password="Str0ng-Reg-1!",
        role_type="user",
    )
    auth = await login(client, "regular78", "Str0ng-Reg-1!")

    r = await client.get("/api/v1/admin/users", headers=auth["_authz"])
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_user_with_excluded_organizations_at_creation(
    client, db_session
):
    """Alta directa con un set de orgs excluidas."""
    t, auth = await _admin_setup(client, db_session, slug="us078i")
    org_a = await _make_org(db_session, t, "OrgA-i")
    org_b = await _make_org(db_session, t, "OrgB-i")

    r = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "User With Exclusions",
            "username": "userwexcl",
            "email": "userwexcl@us078i.example.com",
            "password": "Str0ng-User-1!",
            "role_ids": [],
            "is_active": True,
            "role_type": "user",
            "excluded_organization_ids": [str(org_a.id), str(org_b.id)],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    new_id = r.json()["id"]

    rows = (
        await db_session.execute(
            select(OrganizationUserExclusion).where(
                OrganizationUserExclusion.user_id == new_id
            )
        )
    ).scalars().all()
    assert len(rows) == 2
    assert {r.organization_id for r in rows} == {str(org_a.id), str(org_b.id)}
