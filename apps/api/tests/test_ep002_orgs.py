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


# ==============================================================================
# US-NEW-003 — CRUD Business Units
# ==============================================================================


async def _create_org(client, auth, name="OrgRoot"):
    r = await client.post("/api/v1/organizations", json={"name": name}, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


# TC-NEW-003: nombre BU duplicado en misma org → 409
@pytest.mark.asyncio
async def test_tcnew003_bu_duplicate_name(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)

    r1 = await client.post(
        f"/api/v1/organizations/{org_id}/business-units",
        json={"name": "Comercial"},
        headers=auth["_authz"],
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        f"/api/v1/organizations/{org_id}/business-units",
        json={"name": "Comercial"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409


# TC-NEW-005: listar BUs filtradas por org
@pytest.mark.asyncio
async def test_tcnew005_list_bus_by_org(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_a = await _create_org(client, auth, name="OrgAlpha")
    org_b = await _create_org(client, auth, name="OrgBeta")

    await client.post(
        f"/api/v1/organizations/{org_a}/business-units",
        json={"name": "BU-Alpha-1"},
        headers=auth["_authz"],
    )
    await client.post(
        f"/api/v1/organizations/{org_b}/business-units",
        json={"name": "BU-Beta-1"},
        headers=auth["_authz"],
    )

    r = await client.get(
        f"/api/v1/organizations/{org_a}/business-units", headers=auth["_authz"]
    )
    assert r.status_code == 200
    names = [b["name"] for b in r.json()]
    assert names == ["BU-Alpha-1"]


# BU patch + nombre duplicado al editar
@pytest.mark.asyncio
async def test_bu_update_and_conflict(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu1 = (
        await client.post(
            f"/api/v1/organizations/{org_id}/business-units",
            json={"name": "Finanzas"},
            headers=auth["_authz"],
        )
    ).json()
    bu2 = (
        await client.post(
            f"/api/v1/organizations/{org_id}/business-units",
            json={"name": "Operaciones"},
            headers=auth["_authz"],
        )
    ).json()

    # Edición OK
    r = await client.patch(
        f"/api/v1/business-units/{bu1['id']}",
        json={"description": "Área de finanzas"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Área de finanzas"

    # Renombrar a uno existente → 409
    r2 = await client.patch(
        f"/api/v1/business-units/{bu1['id']}",
        json={"name": bu2["name"]},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409


# Soft-delete BU sin departamentos
@pytest.mark.asyncio
async def test_bu_soft_delete_no_depts(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu = (
        await client.post(
            f"/api/v1/organizations/{org_id}/business-units",
            json={"name": "RRHH"},
            headers=auth["_authz"],
        )
    ).json()
    r = await client.delete(
        f"/api/v1/business-units/{bu['id']}", headers=auth["_authz"]
    )
    assert r.status_code == 204
    g = await client.get(
        f"/api/v1/business-units/{bu['id']}", headers=auth["_authz"]
    )
    # post-soft-delete, ya no listable como activo
    assert g.status_code == 404


# Aislamiento multi-tenant en BUs
@pytest.mark.asyncio
async def test_bu_tenant_isolation(client, db_session):
    _, auth_a = await _admin_setup(client, db_session, slug="bu_t_a")
    _, auth_b = await _admin_setup(client, db_session, slug="bu_t_b")
    org_a = await _create_org(client, auth_a, name="OrgEnA")
    await client.post(
        f"/api/v1/organizations/{org_a}/business-units",
        json={"name": "BUDeA"},
        headers=auth_a["_authz"],
    )
    # Tenant B no puede ver la BU de A ni la org
    r = await client.get(
        f"/api/v1/organizations/{org_a}/business-units", headers=auth_b["_authz"]
    )
    assert r.status_code == 404


# ==============================================================================
# US-NEW-004 — CRUD Departments
# ==============================================================================


async def _create_bu(client, auth, org_id, name):
    r = await client.post(
        f"/api/v1/organizations/{org_id}/business-units",
        json={"name": name},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# TC-NEW-006: nombre Depto duplicado en misma BU → 409
@pytest.mark.asyncio
async def test_tcnew006_dept_duplicate_name(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu_id = await _create_bu(client, auth, org_id, "Comercial")

    r1 = await client.post(
        f"/api/v1/business-units/{bu_id}/departments",
        json={"name": "Ventas"},
        headers=auth["_authz"],
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        f"/api/v1/business-units/{bu_id}/departments",
        json={"name": "Ventas"},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409


# Listar deptos filtrados por BU
@pytest.mark.asyncio
async def test_list_depts_by_bu(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu_a = await _create_bu(client, auth, org_id, "BU-A")
    bu_b = await _create_bu(client, auth, org_id, "BU-B")

    await client.post(
        f"/api/v1/business-units/{bu_a}/departments",
        json={"name": "Dept-A1"}, headers=auth["_authz"],
    )
    await client.post(
        f"/api/v1/business-units/{bu_b}/departments",
        json={"name": "Dept-B1"}, headers=auth["_authz"],
    )
    r = await client.get(
        f"/api/v1/business-units/{bu_a}/departments", headers=auth["_authz"]
    )
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert names == ["Dept-A1"]


# PATCH de depto y rename conflict
@pytest.mark.asyncio
async def test_dept_update_and_rename_conflict(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu_id = await _create_bu(client, auth, org_id, "BU1")
    d1 = (
        await client.post(
            f"/api/v1/business-units/{bu_id}/departments",
            json={"name": "Uno"}, headers=auth["_authz"],
        )
    ).json()
    d2 = (
        await client.post(
            f"/api/v1/business-units/{bu_id}/departments",
            json={"name": "Dos"}, headers=auth["_authz"],
        )
    ).json()

    r = await client.patch(
        f"/api/v1/departments/{d1['id']}",
        json={"description": "desc"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200 and r.json()["description"] == "desc"

    r2 = await client.patch(
        f"/api/v1/departments/{d1['id']}",
        json={"name": d2["name"]},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409


# TC-NEW-007: soft-delete depto con programa activo → 422
@pytest.mark.asyncio
async def test_tcnew007_dept_delete_with_active_program(client, db_session):
    from app.models.organization import Program
    from app.db.base import new_uuid

    t, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu_id = await _create_bu(client, auth, org_id, "BU")
    dept = (
        await client.post(
            f"/api/v1/business-units/{bu_id}/departments",
            json={"name": "DeptoConProg"},
            headers=auth["_authz"],
        )
    ).json()

    prog = Program(
        id=new_uuid(),
        tenant_id=t.id,
        organization_id=org_id,
        department_id=dept["id"],
        name="ProgDelDept",
        is_active=True,
    )
    db_session.add(prog)
    await db_session.commit()

    # Sin force → 422
    r = await client.delete(
        f"/api/v1/departments/{dept['id']}", headers=auth["_authz"]
    )
    assert r.status_code == 422
    # Con force → 204
    r2 = await client.delete(
        f"/api/v1/departments/{dept['id']}?force=true", headers=auth["_authz"]
    )
    assert r2.status_code == 204


# Soft-delete sin hijos
@pytest.mark.asyncio
async def test_dept_soft_delete(client, db_session):
    _, auth = await _admin_setup(client, db_session)
    org_id = await _create_org(client, auth)
    bu_id = await _create_bu(client, auth, org_id, "BU")
    d = (
        await client.post(
            f"/api/v1/business-units/{bu_id}/departments",
            json={"name": "Legal"}, headers=auth["_authz"],
        )
    ).json()
    r = await client.delete(
        f"/api/v1/departments/{d['id']}", headers=auth["_authz"]
    )
    assert r.status_code == 204
    g = await client.get(
        f"/api/v1/departments/{d['id']}", headers=auth["_authz"]
    )
    assert g.status_code == 404
