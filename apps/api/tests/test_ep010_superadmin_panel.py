"""EP010 — Superadmin Panel tests."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _make_super(client, db_session):
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    return await login(client, "root", "Str0ng-Root-1!")


# TC-140 KPIs exactos
@pytest.mark.asyncio
async def test_tc140_platform_dashboard_kpis(client, db_session):
    t1 = await create_tenant(db_session, slug="t1", name="T1")
    t2 = await create_tenant(db_session, slug="t2", name="T2")
    t2.is_active = False
    await db_session.commit()
    auth = await _make_super(client, db_session)
    r = await client.get("/api/v1/superadmin/dashboard", headers=auth["_authz"])
    assert r.status_code == 200
    kpi = r.json()["kpis"]
    assert kpi["tenants_total"] >= 2
    assert kpi["tenants_active"] >= 1
    assert kpi["tenants_inactive"] >= 1


# TC-143 filtros búsqueda de tenants
@pytest.mark.asyncio
async def test_tc143_tenants_search(client, db_session):
    await create_tenant(db_session, slug="acme", name="Acme Corp")
    await create_tenant(db_session, slug="beta", name="Beta SA")
    auth = await _make_super(client, db_session)
    r = await client.get("/api/v1/superadmin/tenants/search?q=acme", headers=auth["_authz"])
    assert r.status_code == 200
    slugs = [x["slug"] for x in r.json()["items"]]
    assert "acme" in slugs and "beta" not in slugs


# TC-146 full detail include filtering
@pytest.mark.asyncio
async def test_tc146_full_detail_include(client, db_session):
    t = await create_tenant(db_session, slug="tdd", name="Td")
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="adm", email="adm@tdd.example.com",
        password="Str0ng-Adm-1!", roles=[admin_role],
    )
    auth = await _make_super(client, db_session)
    r = await client.get(
        f"/api/v1/superadmin/tenants/{t.id}/full-detail?include=users",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert "users" in body
    assert "projects" not in body


# TC-148 full detail 404 on missing
@pytest.mark.asyncio
async def test_tc148_missing_tenant_404(client, db_session):
    import uuid

    auth = await _make_super(client, db_session)
    r = await client.get(
        f"/api/v1/superadmin/tenants/{uuid.uuid4()}/full-detail",
        headers=auth["_authz"],
    )
    assert r.status_code == 404


# Freeze / unfreeze
@pytest.mark.asyncio
async def test_freeze_unfreeze(client, db_session):
    t = await create_tenant(db_session, slug="frz", name="Frz")
    auth = await _make_super(client, db_session)
    f = await client.post(f"/api/v1/superadmin/tenants/{t.id}/freeze", headers=auth["_authz"])
    assert f.status_code == 200
    assert f.json()["frozen"] is True
    u = await client.post(f"/api/v1/superadmin/tenants/{t.id}/unfreeze", headers=auth["_authz"])
    assert u.json()["frozen"] is False


# Platform logs filter by tenant
@pytest.mark.asyncio
async def test_platform_logs_filter(client, db_session):
    t = await create_tenant(db_session, slug="lx", name="Lx")
    auth = await _make_super(client, db_session)
    # Generar un evento: freeze
    await client.post(f"/api/v1/superadmin/tenants/{t.id}/freeze", headers=auth["_authz"])
    r = await client.get("/api/v1/superadmin/logs/platform?action=tenant.frozen",
                          headers=auth["_authz"])
    assert r.status_code == 200
    actions = [x["action"] for x in r.json()]
    assert "tenant.frozen" in actions


# Non-superadmin cannot access panel
@pytest.mark.asyncio
async def test_non_superadmin_denied(client, db_session):
    t = await create_tenant(db_session, slug="reg", name="Reg")
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username="reg", email="reg@reg.example.com",
                      password="Str0ng-Reg-1!", roles=[admin_role])
    auth = await login(client, "reg", "Str0ng-Reg-1!")
    r = await client.get("/api/v1/superadmin/dashboard", headers=auth["_authz"])
    assert r.status_code == 403


# Health endpoint
@pytest.mark.asyncio
async def test_health_endpoint(client, db_session):
    auth = await _make_super(client, db_session)
    r = await client.get("/api/v1/superadmin/health", headers=auth["_authz"])
    assert r.status_code == 200
    body = r.json()
    assert body["db"] is True
