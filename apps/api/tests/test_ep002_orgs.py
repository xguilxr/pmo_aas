"""EP002 — Org Hierarchy tests."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin_setup(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug.title())
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username=f"admin_{slug}", email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


# TC-023
@pytest.mark.asyncio
async def test_tc023_duplicate_org_name(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    r1 = await client.post("/api/v1/organizations", json={"name": "OrgUno"}, headers=auth["_authz"])
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/organizations", json={"name": "OrgUno"}, headers=auth["_authz"])
    assert r2.status_code == 409


# TC-024: soft delete keeps record readable
@pytest.mark.asyncio
async def test_tc024_soft_delete_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    r = await client.post("/api/v1/organizations", json={"name": "OrgSoft"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    dr = await client.delete(f"/api/v1/organizations/{org_id}", headers=auth["_authz"])
    assert dr.status_code == 204
    # Se puede leer aún (soft delete)
    g = await client.get(f"/api/v1/organizations/{org_id}", headers=auth["_authz"])
    assert g.status_code == 200
    assert g.json()["is_active"] is False


# TC-027: program cross-org rejected
@pytest.mark.asyncio
async def test_tc027_program_cross_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    ra = await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"])
    org_a_id = ra.json()["id"]
    # Crear program en org A -> ok
    p = await client.post(
        "/api/v1/programs",
        json={"name": "Prog1", "organization_id": org_a_id},
        headers=auth["_authz"],
    )
    assert p.status_code == 201

    # Program con organization_id inexistente debe fallar
    import uuid

    p2 = await client.post(
        "/api/v1/programs",
        json={"name": "Prog2", "organization_id": str(uuid.uuid4())},
        headers=auth["_authz"],
    )
    assert p2.status_code == 422


# TC-028 filter programs by org
@pytest.mark.asyncio
async def test_tc028_filter_programs_by_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    a = (await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"])).json()
    b = (await client.post("/api/v1/organizations", json={"name": "OrgB"}, headers=auth["_authz"])).json()
    await client.post("/api/v1/programs",
                       json={"name": "PA1", "organization_id": a["id"]}, headers=auth["_authz"])
    await client.post("/api/v1/programs",
                       json={"name": "PB1", "organization_id": b["id"]}, headers=auth["_authz"])
    r = await client.get(f"/api/v1/programs?organization_id={a['id']}", headers=auth["_authz"])
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1 and rows[0]["name"] == "PA1"


# TC-031 provision tenant
@pytest.mark.asyncio
async def test_tc031_provision_tenant(client, db_session):
    # superadmin sin tenant
    super_user = await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.post(
        "/api/v1/superadmin/provision",
        json={
            "name": "New Client Inc",
            "slug": "newco",
            "admin_email": "admin@newco.example.com",
            "admin_full_name": "New Admin",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "newco"
    assert body["admin_password"]

    # El admin nuevo puede hacer login
    login_r = await client.post("/api/v1/auth/login", json={
        "identifier": body.get("admin_email") or "admin@newco.example.com",
        "password": body["admin_password"],
    })
    # identifier debe ser username o email; probemos con email
    login_r2 = await client.post("/api/v1/auth/login", json={
        "identifier": "admin@newco.example.com", "password": body["admin_password"],
    })
    assert login_r2.status_code == 200
    assert login_r2.json()["user"]["must_change_password"] is True


# TC-032 slug duplicado
@pytest.mark.asyncio
async def test_tc032_provision_duplicate_slug(client, db_session):
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    payload = {
        "name": "AA", "slug": "dup", "admin_email": "a@dup.example.com",
        "admin_full_name": "AA",
    }
    r1 = await client.post("/api/v1/superadmin/provision", json=payload, headers=auth["_authz"])
    assert r1.status_code == 201
    payload["admin_email"] = "b@dup.example.com"
    r2 = await client.post("/api/v1/superadmin/provision", json=payload, headers=auth["_authz"])
    assert r2.status_code == 409


# TC-033 slug inválido
@pytest.mark.asyncio
async def test_tc033_provision_invalid_slug(client, db_session):
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.post(
        "/api/v1/superadmin/provision",
        json={"name": "Foo", "slug": "Foo Bar",
              "admin_email": "a@foo.example.com", "admin_full_name": "A"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-038 hard delete wrong slug
@pytest.mark.asyncio
async def test_tc038_hard_delete_wrong_slug(client, db_session):
    t = await create_tenant(db_session, slug="xd", name="xd")
    await db_session.commit()
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.delete(
        f"/api/v1/superadmin/tenants/{t.id}/permanent?confirm_slug=wrong",
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-040 join as admin
@pytest.mark.asyncio
async def test_tc040_join_as_admin(client, db_session):
    t = await create_tenant(db_session, slug="clientx", name="ClientX")
    admin_role = await create_admin_role(db_session, t)  # noqa: F841
    await db_session.commit()
    await create_user(
        db_session, tenant=None, username="root", email="root@pmoaas.example.com",
        password="Str0ng-Root-1!", is_superadmin=True,
    )
    auth = await login(client, "root", "Str0ng-Root-1!")
    r = await client.post(
        f"/api/v1/superadmin/tenants/{t.id}/join-as-admin", headers=auth["_authz"]
    )
    assert r.status_code == 200
    assert r.json()["tenant_slug"] == "clientx"


# TC-MT-001: tenant A admin no ve orgs del tenant B
@pytest.mark.asyncio
async def test_tcmt001_isolation_orgs(client, db_session):
    _, auth_a = await _admin_setup(client, db_session, slug="tenanta")
    _, auth_b = await _admin_setup(client, db_session, slug="tenantb")

    await client.post("/api/v1/organizations", json={"name": "OrgInA"}, headers=auth_a["_authz"])
    r = await client.get("/api/v1/organizations", headers=auth_b["_authz"])
    assert r.status_code == 200
    names = [o["name"] for o in r.json()]
    assert "OrgInA" not in names
