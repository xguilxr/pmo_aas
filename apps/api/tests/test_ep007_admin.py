"""EP007 — Admin Panel tests."""
import pytest

from app.models.role import Role
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="acme"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    admin_role = await create_admin_role(db_session, t)
    await create_user(db_session, tenant=t, username=f"admin_{slug}",
                      email=f"admin@{slug}.example.com",
                      password="Str0ng-Admin-1!", roles=[admin_role])
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth, admin_role


# TC-098 cannot deactivate self
@pytest.mark.asyncio
async def test_tc098_cannot_deactivate_self(client, db_session):
    t, auth, _ = await _admin(client, db_session)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/admin/users/bulk/deactivate",
        json={"user_ids": [me.json()["id"]]},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-099 bulk assign role
@pytest.mark.asyncio
async def test_tc099_bulk_assign_role(client, db_session):
    t, auth, admin_role = await _admin(client, db_session)
    user_ids = []
    for i in range(5):
        u = await create_user(
            db_session, tenant=t, username=f"u{i}", email=f"u{i}@acme.example.com",
            password="Str0ng-Uu-1!",
        )
        user_ids.append(str(u.id))
    # crear otro rol
    r2 = Role(tenant_id=t.id, name="Marketing", description="m",
              permissions={"projects": ["read"]}, is_system=False)
    db_session.add(r2)
    await db_session.commit()
    resp = await client.post(
        "/api/v1/admin/users/bulk/assign-role",
        json={"user_ids": user_ids, "role_id": str(r2.id)},
        headers=auth["_authz"],
    )
    assert resp.status_code == 200
    assert resp.json()["affected"] == 5


# TC-103 role duplicate
@pytest.mark.asyncio
async def test_tc103_role_duplicate(client, db_session):
    _, auth, admin_role = await _admin(client, db_session)
    r = await client.post(
        f"/api/v1/admin/roles/{admin_role.id}/duplicate", headers=auth["_authz"]
    )
    assert r.status_code == 201
    body = r.json()
    assert body["is_system"] is False
    assert "(copy)" in body["name"]


# TC-104 org metrics
@pytest.mark.asyncio
async def test_tc104_org_metrics(client, db_session):
    _, auth, _ = await _admin(client, db_session)
    r = await client.post("/api/v1/organizations", json={"name": "OrgM"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    await client.post(
        "/api/v1/projects",
        json={"name": "P1", "description": "d", "type": "innovation", "priority": 3,
              "organization_id": org_id, "pm_id": me.json()["id"], "budget": "10000"},
        headers=auth["_authz"],
    )
    m = await client.get("/api/v1/admin/organizations/metrics", headers=auth["_authz"])
    assert m.status_code == 200
    rows = m.json()
    match = next((x for x in rows if x["name"] == "OrgM"), None)
    assert match is not None
    assert match["project_count_active"] == 1
    assert match["budget_total"] == 10000.0


# TC-107 admin view of all projects
@pytest.mark.asyncio
async def test_tc107_admin_sees_all(client, db_session):
    _, auth, _ = await _admin(client, db_session)
    r = await client.post("/api/v1/organizations", json={"name": "OrgX"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    for i in range(3):
        await client.post(
            "/api/v1/projects",
            json={"name": f"P{i}", "description": "d", "type": "innovation", "priority": 3,
                  "organization_id": org_id, "pm_id": me.json()["id"]},
            headers=auth["_authz"],
        )
    r = await client.get("/api/v1/admin/projects", headers=auth["_authz"])
    assert r.status_code == 200
    assert len(r.json()) == 3


# TC-108 settings update
@pytest.mark.asyncio
async def test_tc108_settings_update(client, db_session):
    _, auth, _ = await _admin(client, db_session)
    r = await client.patch("/api/v1/admin/settings",
                            json={"locale": "en-US", "currency": "USD"},
                            headers=auth["_authz"])
    assert r.status_code == 200
    assert r.json()["settings"]["locale"] == "en-US"


# TC-MT-006 audit logs isolated
@pytest.mark.asyncio
async def test_tcmt006_audit_isolation(client, db_session):
    t_a, auth_a, _ = await _admin(client, db_session, slug="aa")
    t_b, auth_b, _ = await _admin(client, db_session, slug="bb")
    # tenant a crea una org (genera audit)
    await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=auth_a["_authz"])
    logs_b = await client.get("/api/v1/admin/audit-logs", headers=auth_b["_authz"])
    assert logs_b.status_code == 200
    entities = [l.get("entity_id") for l in logs_b.json()]
    # No debe contener eventos del tenant A
    actions = [l["action"] for l in logs_b.json()]
    assert "organization.create" not in actions


# Force close project
@pytest.mark.asyncio
async def test_force_close_project(client, db_session):
    _, auth, _ = await _admin(client, db_session)
    r = await client.post("/api/v1/organizations", json={"name": "OrgF"}, headers=auth["_authz"])
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={"name": "Closeme", "description": "d", "type": "bau", "priority": 1,
              "organization_id": org_id, "pm_id": me.json()["id"]},
        headers=auth["_authz"],
    )
    pid = p.json()["id"]
    fc = await client.post(
        f"/api/v1/admin/projects/{pid}/force-close",
        json={"comment": "Decisión ejecutiva"},
        headers=auth["_authz"],
    )
    assert fc.status_code == 200
    assert fc.json()["phase"] == "closed"


# ============================================================================
# US-023 — Gestión de Tenant (admin panel)
# ============================================================================


@pytest.mark.asyncio
async def test_us023_get_tenant_info_with_stats(client, db_session):
    from decimal import Decimal
    from app.models.project import Project

    t, auth, _ = await _admin(client, db_session, slug="tenant23")
    # seed: una org + 2 proyectos
    r = await client.post(
        "/api/v1/organizations", json={"name": "OrgX"}, headers=auth["_authz"],
    )
    org_id = r.json()["id"]
    for i in range(2):
        db_session.add(
            Project(
                tenant_id=str(t.id),
                organization_id=org_id,
                folio=f"P23-{i+1}",
                name=f"P{i+1}",
                phase="planning",
                budget=Decimal("100"),
            )
        )
    await db_session.commit()

    info = await client.get("/api/v1/admin/tenant", headers=auth["_authz"])
    assert info.status_code == 200, info.text
    data = info.json()
    assert data["slug"] == "tenant23"
    assert data["name"] == "tenant23"
    assert data["plan"] == "mvp"  # default cuando no hay plan en settings
    assert data["stats"]["active_users"] >= 1
    assert data["stats"]["total_organizations"] == 1
    assert data["stats"]["total_projects"] == 2
    assert "storage_bytes" in data["stats"]


@pytest.mark.asyncio
async def test_us023_patch_tenant_name_and_logo(client, db_session):
    _, auth, _ = await _admin(client, db_session, slug="t23b")
    r = await client.patch(
        "/api/v1/admin/tenant",
        json={
            "name": "Acme Updated",
            "logo_url": "https://cdn.example.com/logo.png",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Acme Updated"
    assert r.json()["logo_url"] == "https://cdn.example.com/logo.png"
    # Slug no cambia
    assert r.json()["slug"] == "t23b"


@pytest.mark.asyncio
async def test_us023_patch_ignores_slug(client, db_session):
    _, auth, _ = await _admin(client, db_session, slug="t23c")
    r = await client.patch(
        "/api/v1/admin/tenant",
        json={"slug": "otro-slug", "name": "Nuevo nombre"},
        headers=auth["_authz"],
    )
    # el schema ignora slug (no está en TenantInfoUpdate); nombre sí aplica
    assert r.status_code == 200
    assert r.json()["slug"] == "t23c"
    assert r.json()["name"] == "Nuevo nombre"


@pytest.mark.asyncio
async def test_us023_patch_name_too_short(client, db_session):
    _, auth, _ = await _admin(client, db_session, slug="t23d")
    r = await client.patch(
        "/api/v1/admin/tenant",
        json={"name": "X"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422
