"""US-088 — Hard delete (segundo paso) tests.

Cobertura: las 6 entidades (program, organization, business_unit,
department, user, stakeholder) con happy path + slug mismatch +
active-blocked. Cascada validada con un proyecto-hijo en programa.
"""
import pytest

from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    login,
)

# create_admin_role usado por _admin_setup; create_user reutilizado en tests user.
_ = create_admin_role


async def _admin_setup(client, db_session, slug="us088"):
    t = await create_tenant(db_session, slug=slug, name=slug.title())
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, auth


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us088_program_active_blocks_hard_delete(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us088a")
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"]
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "ProgActive", "organization_id": org["id"]},
            headers=auth["_authz"],
        )
    ).json()

    # Activo → 409 con code=MUST_DEACTIVATE_FIRST
    r = await client.delete(
        f"/api/v1/programs/{prog['id']}/permanent?confirm=program:progactive",
        headers=auth["_authz"],
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "MUST_DEACTIVATE_FIRST"


@pytest.mark.asyncio
async def test_us088_program_slug_mismatch_returns_preview(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us088b")
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgB"}, headers=auth["_authz"]
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "ProgWrongSlug", "organization_id": org["id"]},
            headers=auth["_authz"],
        )
    ).json()
    # Soft delete primero
    await client.delete(f"/api/v1/programs/{prog['id']}", headers=auth["_authz"])

    r = await client.delete(
        f"/api/v1/programs/{prog['id']}/permanent?confirm=program:wrong",
        headers=auth["_authz"],
    )
    assert r.status_code == 400
    body = r.json()["detail"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["fields"]["expected"] == "program:progwrongslug"
    assert "preview" in body["fields"]


@pytest.mark.asyncio
async def test_us088_program_happy_path_with_cascade(client, db_session):
    """Programa con 1 proyecto hijo → hard delete cascadea y borra ambos."""
    _, auth = await _admin_setup(client, db_session, slug="us088c")
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgC"}, headers=auth["_authz"]
        )
    ).json()
    prog = (
        await client.post(
            "/api/v1/programs",
            json={"name": "ProgCascade", "organization_id": org["id"]},
            headers=auth["_authz"],
        )
    ).json()
    # Crear proyecto hijo bajo el programa.
    pm_user = (
        await client.get("/api/v1/users/me", headers=auth["_authz"])
    ).json()
    proj = await client.post(
        "/api/v1/projects",
        json={
            "name": "ProjHijo",
            "description": "child of program",
            "type": "operation",
            "priority": 3,
            "pm_id": pm_user["id"],
            "organization_id": org["id"],
            "program_id": prog["id"],
        },
        headers=auth["_authz"],
    )
    assert proj.status_code == 201, proj.text
    proj_id = proj.json()["id"]

    # Preview muestra 1 proyecto en cascada.
    pr = await client.get(
        f"/api/v1/programs/{prog['id']}/hard-delete-preview", headers=auth["_authz"]
    )
    assert pr.status_code == 200
    body = pr.json()
    assert body["confirm_slug"] == "program:progcascade"
    assert body["cascades"]["projects"] == 1
    assert body["is_active"] is True

    # Soft delete primero.
    sd = await client.delete(f"/api/v1/programs/{prog['id']}", headers=auth["_authz"])
    assert sd.status_code == 204

    # Hard delete con slug correcto.
    hd = await client.delete(
        f"/api/v1/programs/{prog['id']}/permanent?confirm=program:progcascade",
        headers=auth["_authz"],
    )
    assert hd.status_code == 204, hd.text

    # Programa y proyecto ya no existen.
    after = await client.get(f"/api/v1/programs?organization_id={org['id']}", headers=auth["_authz"])
    assert all(p["id"] != prog["id"] for p in after.json())
    after_proj = await client.get(f"/api/v1/projects/{proj_id}", headers=auth["_authz"])
    assert after_proj.status_code == 404


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us088_org_happy_path(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us088d")
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgKill"}, headers=auth["_authz"]
        )
    ).json()
    await client.delete(f"/api/v1/organizations/{org['id']}", headers=auth["_authz"])
    pr = await client.get(
        f"/api/v1/organizations/{org['id']}/hard-delete-preview", headers=auth["_authz"]
    )
    assert pr.status_code == 200
    slug = pr.json()["confirm_slug"]
    assert slug == "organization:orgkill"

    hd = await client.delete(
        f"/api/v1/organizations/{org['id']}/permanent?confirm={slug}",
        headers=auth["_authz"],
    )
    assert hd.status_code == 204
    g = await client.get(f"/api/v1/organizations/{org['id']}", headers=auth["_authz"])
    assert g.status_code == 404


# ---------------------------------------------------------------------------
# Business Units
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us088_bu_happy_path(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us088e")
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgBU"}, headers=auth["_authz"]
        )
    ).json()
    bu = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/business-units",
            json={"name": "BUDelete"},
            headers=auth["_authz"],
        )
    ).json()
    # Soft delete (BU pasa a is_active=False + deleted_at).
    await client.delete(
        f"/api/v1/business-units/{bu['id']}", headers=auth["_authz"]
    )
    pr = await client.get(
        f"/api/v1/business-units/{bu['id']}/hard-delete-preview",
        headers=auth["_authz"],
    )
    assert pr.status_code == 200
    slug = pr.json()["confirm_slug"]
    hd = await client.delete(
        f"/api/v1/business-units/{bu['id']}/permanent?confirm={slug}",
        headers=auth["_authz"],
    )
    assert hd.status_code == 204, hd.text


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us088_dept_happy_path(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us088f")
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgDept"}, headers=auth["_authz"]
        )
    ).json()
    bu = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/business-units",
            json={"name": "BUForDept"},
            headers=auth["_authz"],
        )
    ).json()
    dept = (
        await client.post(
            f"/api/v1/business-units/{bu['id']}/departments",
            json={"name": "DeptKill"},
            headers=auth["_authz"],
        )
    ).json()
    await client.delete(f"/api/v1/departments/{dept['id']}", headers=auth["_authz"])
    pr = await client.get(
        f"/api/v1/departments/{dept['id']}/hard-delete-preview",
        headers=auth["_authz"],
    )
    slug = pr.json()["confirm_slug"]
    hd = await client.delete(
        f"/api/v1/departments/{dept['id']}/permanent?confirm={slug}",
        headers=auth["_authz"],
    )
    assert hd.status_code == 204, hd.text


# ---------------------------------------------------------------------------
# Stakeholders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us088_stakeholder_happy_path(client, db_session):
    _, auth = await _admin_setup(client, db_session, slug="us088g")
    s = (
        await client.post(
            "/api/v1/stakeholders",
            json={"full_name": "Juan Stake"},
            headers=auth["_authz"],
        )
    ).json()
    # Soft delete → deleted_at set.
    await client.delete(f"/api/v1/stakeholders/{s['id']}", headers=auth["_authz"])
    pr = await client.get(
        f"/api/v1/stakeholders/{s['id']}/hard-delete-preview",
        headers=auth["_authz"],
    )
    slug = pr.json()["confirm_slug"]
    assert slug == "stakeholder:juan-stake"
    hd = await client.delete(
        f"/api/v1/stakeholders/{s['id']}/permanent?confirm={slug}",
        headers=auth["_authz"],
    )
    assert hd.status_code == 204


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_us088_user_blocked_when_active(client, db_session):
    t, auth = await _admin_setup(client, db_session, slug="us088h")
    other = await create_user(
        db_session,
        tenant=t,
        username="victima",
        email="victima@us088h.example.com",
        password="Str0ng-Pass-1!",
    )
    r = await client.delete(
        f"/api/v1/admin/users/{other.id}/permanent?confirm=user:victima",
        headers=auth["_authz"],
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "MUST_DEACTIVATE_FIRST"


@pytest.mark.asyncio
async def test_us088_user_happy_path(client, db_session):
    t, auth = await _admin_setup(client, db_session, slug="us088i")
    other = await create_user(
        db_session,
        tenant=t,
        username="paraborrar",
        email="paraborrar@us088i.example.com",
        password="Str0ng-Pass-1!",
    )
    # Soft delete primero.
    await client.delete(f"/api/v1/admin/users/{other.id}", headers=auth["_authz"])

    pr = await client.get(
        f"/api/v1/admin/users/{other.id}/hard-delete-preview",
        headers=auth["_authz"],
    )
    assert pr.status_code == 200
    slug = pr.json()["confirm_slug"]
    assert slug == "user:paraborrar"

    hd = await client.delete(
        f"/api/v1/admin/users/{other.id}/permanent?confirm={slug}",
        headers=auth["_authz"],
    )
    assert hd.status_code == 204, hd.text

    g = await client.get(f"/api/v1/admin/users/{other.id}", headers=auth["_authz"])
    assert g.status_code == 404
