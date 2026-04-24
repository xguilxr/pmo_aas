"""US-042 — Usuarios cross-tenant en panel super admin."""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _superadmin(client, db_session):
    t = await create_tenant(db_session, slug="sa-tenant", name="sa-tenant")
    await create_user(
        db_session, tenant=t, username="sa_root",
        email="root@sa.example.com", password="Str0ng-Super-1!",
        is_superadmin=True,
    )
    auth = await login(client, "sa_root", "Str0ng-Super-1!")
    return t, auth


async def _regular_admin(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth, role


@pytest.mark.asyncio
async def test_us042_list_requires_superadmin(client, db_session):
    _, auth, _ = await _regular_admin(client, db_session, slug="reg-a")
    r = await client.get("/api/v1/superadmin/users", headers=auth["_authz"])
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_us042_list_cross_tenant(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)

    t_a = await create_tenant(db_session, slug="tuser-a", name="A")
    t_b = await create_tenant(db_session, slug="tuser-b", name="B")
    await create_user(db_session, tenant=t_a, username="alice", email="alice@a.com", password="Str0ng-a-1!")
    await create_user(db_session, tenant=t_b, username="bob", email="bob@b.com", password="Str0ng-b-1!")

    r = await client.get("/api/v1/superadmin/users", headers=sa_auth["_authz"])
    assert r.status_code == 200, r.text
    body = r.json()
    usernames = {u["username"] for u in body["items"]}
    assert "alice" in usernames
    assert "bob" in usernames
    # Super admin mismo también aparece
    assert "sa_root" in usernames


@pytest.mark.asyncio
async def test_us042_filter_by_tenant(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)

    t_a = await create_tenant(db_session, slug="ften-a", name="A")
    t_b = await create_tenant(db_session, slug="ften-b", name="B")
    await create_user(db_session, tenant=t_a, username="userA", email="a@ften.com", password="Str0ng-a-1!")
    await create_user(db_session, tenant=t_b, username="userB", email="b@ften.com", password="Str0ng-b-1!")

    r = await client.get(
        f"/api/v1/superadmin/users?tenant_id={t_a.id}",
        headers=sa_auth["_authz"],
    )
    assert r.status_code == 200
    tenant_slugs = {u["tenant_slug"] for u in r.json()["items"]}
    assert tenant_slugs == {"ften-a"}


@pytest.mark.asyncio
async def test_us042_search_q_matches_email_username(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)

    t = await create_tenant(db_session, slug="qsearch", name="Q")
    await create_user(db_session, tenant=t, username="maria", email="maria.lopez@q.com", password="Str0ng-a-1!")

    r = await client.get("/api/v1/superadmin/users?q=lopez", headers=sa_auth["_authz"])
    assert r.status_code == 200
    assert any(u["username"] == "maria" for u in r.json()["items"])


@pytest.mark.asyncio
async def test_us042_patch_user(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)

    t = await create_tenant(db_session, slug="patch-t", name="P")
    u = await create_user(db_session, tenant=t, username="bob2", email="bob2@p.com", password="Str0ng-b-1!")

    r = await client.patch(
        f"/api/v1/superadmin/users/{u.id}",
        json={"full_name": "Bob Nuevo", "email": "bob2-new@p.com"},
        headers=sa_auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["full_name"] == "Bob Nuevo"
    assert body["email"] == "bob2-new@p.com"


@pytest.mark.asyncio
async def test_us042_patch_other_superadmin_forbidden(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)

    t = await create_tenant(db_session, slug="sa2-t", name="S")
    other_sa = await create_user(
        db_session, tenant=t, username="sa_other",
        email="other@s.com", password="Str0ng-b-1!",
        is_superadmin=True,
    )

    r = await client.patch(
        f"/api/v1/superadmin/users/{other_sa.id}",
        json={"full_name": "Hack"},
        headers=sa_auth["_authz"],
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_us042_toggle_active_audits(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)

    t = await create_tenant(db_session, slug="toggle-t", name="T")
    u = await create_user(db_session, tenant=t, username="victim", email="v@t.com", password="Str0ng-b-1!")
    assert u.is_active is True

    r = await client.post(
        f"/api/v1/superadmin/users/{u.id}/toggle-active",
        json={"reason": "Cuenta sospechosa reportada por el tenant"},
        headers=sa_auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_active"] is False

    # Volver a togglear → activo de nuevo
    r2 = await client.post(
        f"/api/v1/superadmin/users/{u.id}/toggle-active",
        json={"reason": "Revisión completada, re-activar"},
        headers=sa_auth["_authz"],
    )
    assert r2.status_code == 200
    assert r2.json()["is_active"] is True

    # Verificar audit
    logs = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "user.superadmin_toggle_active",
                AuditLog.entity_id == str(u.id),
            )
        )
    ).scalars().all()
    assert len(logs) == 2


@pytest.mark.asyncio
async def test_us042_cannot_deactivate_self(client, db_session):
    _, sa_auth = await _superadmin(client, db_session)
    me = (await client.get("/api/v1/auth/me", headers=sa_auth["_authz"])).json()
    r = await client.post(
        f"/api/v1/superadmin/users/{me['id']}/toggle-active",
        json={"reason": "whatever"},
        headers=sa_auth["_authz"],
    )
    assert r.status_code == 422  # business_rule
