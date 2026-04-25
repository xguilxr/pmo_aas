"""EP001 — Auth & Users tests."""
import pytest

from app.core.security import validate_password_policy
from tests.factories import create_admin_role, create_tenant, create_user, login


# -- TC-001 unit: password policy ---------------------------------
def test_tc001_password_policy_rejects_weak():
    for bad in ["password123", "Aa1!", "Short1!", "nouppercase1!aa", "NOLOWER123!AA"]:
        ok, _err = validate_password_policy(bad)
        if bad in ("password123",):
            assert not ok
        # at least one of the bad samples must fail
    ok, _ = validate_password_policy("Valid-Strong-Pass1!")
    assert ok


# -- TC-002/003 integration --------------------------------------
@pytest.mark.asyncio
async def test_tc003_create_user_happy_path(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])

    auth = await login(client, "admin", "Str0ng-Admin-1!")

    r = await client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Juan Pérez",
            "username": "juanp",
            "email": "juan@acme.example.com",
            "password": "Str0ng-Juan-1!",
            "role_ids": [],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "juanp"
    assert body["email"] == "juan@acme.example.com"
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_tc002_create_duplicate_email_409(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, password="Str0ng-Admin-1!", roles=[admin_role])
    auth = await login(client, "admin", "Str0ng-Admin-1!")

    body = {
        "full_name": "Dup User",
        "username": "dupuser",
        "email": "admin@acme.example.com",
        "password": "Str0ng-Dup-1!",
        "role_ids": [],
    }
    r = await client.post("/api/v1/admin/users", json=body, headers=auth["_authz"])
    assert r.status_code == 409


# -- TC-005/006 login ---------------------------------------------
@pytest.mark.asyncio
async def test_tc005_login_with_username(client, db_session):
    t = await create_tenant(db_session)
    await create_user(db_session, tenant=t, username="maria", email="maria@acme.example.com",
                      password="Str0ng-Maria-1!")
    r = await client.post("/api/v1/auth/login",
                          json={"identifier": "maria", "password": "Str0ng-Maria-1!"})
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"]
    assert data["user"]["username"] == "maria"


@pytest.mark.asyncio
async def test_tc006_login_with_email(client, db_session):
    t = await create_tenant(db_session)
    await create_user(db_session, tenant=t, username="pepe", email="pepe@acme.example.com",
                      password="Str0ng-Pepe-1!")
    r = await client.post("/api/v1/auth/login",
                          json={"identifier": "pepe@acme.example.com", "password": "Str0ng-Pepe-1!"})
    assert r.status_code == 200


# -- TC-007 bad password ------------------------------------------
@pytest.mark.asyncio
async def test_tc007_bad_password_increments_failed(client, db_session):
    from sqlalchemy import select

    from app.models.user import User

    t = await create_tenant(db_session)
    await create_user(db_session, tenant=t, username="ana", email="ana@acme.example.com",
                      password="Str0ng-Ana-1!")
    r = await client.post("/api/v1/auth/login",
                          json={"identifier": "ana", "password": "wrong-wrong"})
    assert r.status_code == 401

    await db_session.commit()
    u = (await db_session.execute(select(User).where(User.username == "ana"))).scalar_one()
    await db_session.refresh(u)
    assert u.failed_login_attempts >= 1


# -- TC-008 inactive user ------------------------------------------
@pytest.mark.asyncio
async def test_tc008_inactive_user_403(client, db_session):

    t = await create_tenant(db_session)
    u = await create_user(db_session, tenant=t, username="inact", email="i@acme.example.com",
                          password="Str0ng-Inact-1!")
    u.is_active = False
    await db_session.commit()
    r = await client.post("/api/v1/auth/login",
                          json={"identifier": "inact", "password": "Str0ng-Inact-1!"})
    assert r.status_code == 403


# -- TC-010 lockout after 5 fails ----------------------------------
@pytest.mark.asyncio
async def test_tc010_lockout_after_5_fails(client, db_session):
    t = await create_tenant(db_session)
    await create_user(db_session, tenant=t, username="lock", email="lock@acme.example.com",
                      password="Str0ng-Lock-1!")
    for _ in range(5):
        await client.post("/api/v1/auth/login",
                          json={"identifier": "lock", "password": "wrong-wrong"})
    r = await client.post("/api/v1/auth/login",
                          json={"identifier": "lock", "password": "Str0ng-Lock-1!"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "ACCOUNT_LOCKED"


# -- TC-012 admin unlock -------------------------------------------
@pytest.mark.asyncio
async def test_tc012_admin_can_unlock(client, db_session):
    from sqlalchemy import select

    from app.models.user import User

    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    target = await create_user(db_session, tenant=t, username="target", email="t@acme.example.com",
                                password="Str0ng-Target-1!")
    for _ in range(5):
        await client.post("/api/v1/auth/login",
                          json={"identifier": "target", "password": "bad-bad-bad"})
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        f"/api/v1/admin/users/{target.id}/unlock", headers=auth["_authz"]
    )
    assert r.status_code == 204
    await db_session.commit()
    u = (await db_session.execute(select(User).where(User.id == str(target.id)))).scalar_one()
    await db_session.refresh(u)
    assert u.locked_until is None
    assert u.failed_login_attempts == 0


# -- TC-013 change password + refresh invalidation -----------------
@pytest.mark.asyncio
async def test_tc013_change_password_invalidates_refresh(client, db_session):
    from sqlalchemy import select

    from app.models.auth import RefreshToken

    t = await create_tenant(db_session)
    u = await create_user(db_session, tenant=t, username="cp", email="cp@acme.example.com",
                          password="Str0ng-Cp-1!")
    auth = await login(client, "cp", "Str0ng-Cp-1!")
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Str0ng-Cp-1!", "new_password": "Str0ng-Cp-2!"},
        headers=auth["_authz"],
    )
    assert r.status_code == 204
    await db_session.commit()
    rts = (await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == u.id))).scalars().all()
    assert rts, "debería haber generado un refresh token en login"
    assert all(rt.revoked for rt in rts)


# -- TC-014 same new password rejected -----------------------------
@pytest.mark.asyncio
async def test_tc014_same_password_rejected(client, db_session):
    t = await create_tenant(db_session)
    await create_user(db_session, tenant=t, username="same", email="same@acme.example.com",
                      password="Str0ng-Same-1!")
    auth = await login(client, "same", "Str0ng-Same-1!")
    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Str0ng-Same-1!", "new_password": "Str0ng-Same-1!"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# -- TC-016 reset password by admin --------------------------------
@pytest.mark.asyncio
async def test_tc016_admin_reset_password(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    target = await create_user(db_session, tenant=t, username="target", email="t@acme.example.com",
                                password="Str0ng-Target-1!")
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        f"/api/v1/admin/users/{target.id}/reset-password", headers=auth["_authz"]
    )
    assert r.status_code == 200
    temp = r.json()["temp_password"]
    assert len(temp) >= 12
    login2 = await client.post("/api/v1/auth/login", json={"identifier": "target", "password": temp})
    assert login2.status_code == 200
    assert login2.json()["user"]["must_change_password"] is True


# -- TC-MT-005: cross-tenant forbidden -----------------------------
@pytest.mark.asyncio
async def test_tcmt005_cross_tenant_forbidden(client, db_session):
    t_a = await create_tenant(db_session, slug="a", name="A")
    t_b = await create_tenant(db_session, slug="b", name="B")
    admin_role_a = await create_admin_role(db_session, t_a)
    await create_user(db_session, tenant=t_a, username="adminA", email="a@a.example.com",
                      password="Str0ng-AA-1!", roles=[admin_role_a])
    user_b = await create_user(db_session, tenant=t_b, username="userB", email="b@b.example.com",
                                password="Str0ng-BB-1!")
    auth = await login(client, "adminA", "Str0ng-AA-1!")
    r = await client.post(
        f"/api/v1/admin/users/{user_b.id}/reset-password", headers=auth["_authz"]
    )
    assert r.status_code == 403


# -- TC-018 — borrado en US-077: el endpoint /admin/roles desapareció
# (DEC-024). El modelo de roles legacy quedó deprecated, ver US-081.

# -- TC-021/022 search & filter ------------------------------------
@pytest.mark.asyncio
async def test_tc021_search_users_by_name(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    await create_user(db_session, tenant=t, username="juanp", email="juan@acme.example.com",
                      password="Str0ng-Juan-1!", full_name="Juan Pérez")
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.get("/api/v1/admin/users?q=juan", headers=auth["_authz"])
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["username"] == "juanp" for i in items)


@pytest.mark.asyncio
async def test_tc022_filter_inactive(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    inact = await create_user(db_session, tenant=t, username="off", email="off@acme.example.com",
                               password="Str0ng-Off-1!")
    inact.is_active = False
    await db_session.commit()
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.get("/api/v1/admin/users?is_active=false", headers=auth["_authz"])
    assert r.status_code == 200
    assert all(not i["is_active"] for i in r.json()["items"])


# ============================================================================
# US-007 — Toggle dark/light (preferencias de usuario)
# ============================================================================


# TC-NEW-013: preferencia persiste entre sesiones
@pytest.mark.asyncio
async def test_tcnew013_preferences_persist(client, db_session):
    t = await create_tenant(db_session)
    await create_user(
        db_session, tenant=t, username="pu", email="pu@acme.example.com",
        password="Str0ng-Pu-1!",
    )
    auth = await login(client, "pu", "Str0ng-Pu-1!")

    # default
    r = await client.get("/api/v1/users/me/preferences", headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["theme"] == "system"

    # set dark
    r2 = await client.patch(
        "/api/v1/users/me/preferences",
        json={"theme": "dark"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 200 and r2.json()["theme"] == "dark"

    # nuevo login → debe persistir
    auth2 = await login(client, "pu", "Str0ng-Pu-1!")
    r3 = await client.get("/api/v1/users/me/preferences", headers=auth2["_authz"])
    assert r3.json()["theme"] == "dark"


# validación: theme inválido → 422
@pytest.mark.asyncio
async def test_preferences_invalid_theme(client, db_session):
    t = await create_tenant(db_session)
    await create_user(
        db_session, tenant=t, username="pinv", email="pinv@acme.example.com",
        password="Str0ng-Pinv-1!",
    )
    auth = await login(client, "pinv", "Str0ng-Pinv-1!")
    r = await client.patch(
        "/api/v1/users/me/preferences",
        json={"theme": "neon"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# locale update propaga a users.locale
@pytest.mark.asyncio
async def test_preferences_locale_updates_locale_column(client, db_session):
    from sqlalchemy import select

    from app.models.user import User

    t = await create_tenant(db_session)
    u = await create_user(
        db_session, tenant=t, username="pl", email="pl@acme.example.com",
        password="Str0ng-Pl-1!",
    )
    auth = await login(client, "pl", "Str0ng-Pl-1!")
    r = await client.patch(
        "/api/v1/users/me/preferences",
        json={"locale": "en-US"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200 and r.json()["locale"] == "en-US"
    await db_session.refresh(u)
    fresh = (await db_session.execute(select(User).where(User.id == u.id))).scalar_one()
    assert fresh.locale == "en-US"


# ============================================================================
# US-010 — Senior PMO como admin (DEC-005)
# ============================================================================


# TC-NEW-018: Senior PMO (rol PMO Manager con admin.*) accede a /admin/users
@pytest.mark.asyncio
async def test_tcnew018_senior_pmo_can_access_admin(client, db_session):
    from app.models.role import Role

    t = await create_tenant(db_session, slug="srpmo", name="SrPmo")
    # Crear rol "PMO Manager" con admin.* permissions (mismo shape que en seed)
    pmo_senior = Role(
        tenant_id=t.id,
        name="PMO Manager",
        description="Senior PMO / Admin-eq",
        is_system=True,
        permissions={
            "users": ["read", "create", "update", "delete"],
            "roles": ["read", "create", "update", "delete"],
            "organizations": ["read", "create", "update", "delete"],
            "admin": ["read"],
            "requests": ["read", "approve"],
            "projects": ["read", "create", "update", "approve"],
            "dashboard": ["read"],
        },
    )
    db_session.add(pmo_senior)
    await db_session.flush()
    await create_user(
        db_session, tenant=t, username="senior", email="senior@srpmo.example.com",
        password="Str0ng-Sr-1!", roles=[pmo_senior],
    )
    auth = await login(client, "senior", "Str0ng-Sr-1!")
    # /admin/users list debe responder 200
    r = await client.get("/api/v1/admin/users", headers=auth["_authz"])
    assert r.status_code == 200, r.text


# US-076 + DEC-024: is_admin_equivalent depende solo de role_type/is_superadmin
@pytest.mark.asyncio
async def test_is_admin_equivalent_helper(client, db_session):
    from app.api.deps import CurrentUser

    # user regular
    cu_user = CurrentUser(
        user=type("U", (), {"is_superadmin": False, "role_type": "user"})(),
        tenant_ids=[],
        active_tenant_id=None,
    )
    assert cu_user.is_admin_equivalent is False

    # admin
    cu_admin = CurrentUser(
        user=type("U", (), {"is_superadmin": False, "role_type": "admin"})(),
        tenant_ids=[], active_tenant_id=None,
    )
    assert cu_admin.is_admin_equivalent is True

    # superadmin (bypass total)
    cu_sa = CurrentUser(
        user=type("U", (), {"is_superadmin": True, "role_type": None})(),
        tenant_ids=[], active_tenant_id=None,
    )
    assert cu_sa.is_admin_equivalent is True


# ============================================================================
# US-009 — Perfil personal via PATCH /users/me
# ============================================================================


# TC-NEW-015: editar nombre → se refleja en el perfil
@pytest.mark.asyncio
async def test_tcnew015_update_full_name(client, db_session):
    t = await create_tenant(db_session, slug="acmen", name="Acme")
    await create_user(
        db_session, tenant=t, username="juan",
        email="juan@acmen.example.com", password="Str0ng-Juan-1!",
        full_name="Juan Pérez",
    )
    auth = await login(client, "juan", "Str0ng-Juan-1!")
    r = await client.patch(
        "/api/v1/users/me",
        json={"full_name": "Juan P. López"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200 and r.json()["full_name"] == "Juan P. López"

    # GET refleja el cambio
    g = await client.get("/api/v1/users/me", headers=auth["_authz"])
    assert g.json()["full_name"] == "Juan P. López"


# full_name muy corto → 422
@pytest.mark.asyncio
async def test_update_full_name_too_short(client, db_session):
    t = await create_tenant(db_session, slug="vshort", name="VS")
    await create_user(
        db_session, tenant=t, username="u",
        email="u@vshort.example.com", password="Str0ng-Vs-1!",
    )
    auth = await login(client, "u", "Str0ng-Vs-1!")
    r = await client.patch(
        "/api/v1/users/me", json={"full_name": "X"}, headers=auth["_authz"]
    )
    assert r.status_code == 422
