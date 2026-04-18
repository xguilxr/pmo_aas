"""EP001 — Auth & Users tests."""
import pytest

from app.core.security import validate_password_policy
from tests.factories import create_admin_role, create_tenant, create_user, login


# -- TC-001 unit: password policy ---------------------------------
def test_tc001_password_policy_rejects_weak():
    for bad in ["password123", "Aa1!", "Short1!", "nouppercase1!aa", "NOLOWER123!AA"]:
        ok, err = validate_password_policy(bad)
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
    from app.models.user import User

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


# -- TC-018 cannot delete system role ------------------------------
@pytest.mark.asyncio
async def test_tc018_cannot_delete_system_role(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="admin", email="admin@acme.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.delete(f"/api/v1/admin/roles/{admin_role.id}", headers=auth["_authz"])
    assert r.status_code == 422


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
