"""ENH-020 + US-062 — recursos múltiples por área + area_leader_id."""
from decimal import Decimal

import pytest

from app.models.organization import Organization
from app.models.project import Project
from app.models.project_area import ProjectArea, ProjectAreaResource
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug="area-rsc"):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    u = await create_user(
        db_session,
        tenant=t,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    return t, u, auth


async def _project_with_area(db_session, tenant, *, folio="P-A01"):
    org = Organization(tenant_id=tenant.id, name=f"Org-{folio}", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p = Project(
        tenant_id=str(tenant.id),
        organization_id=str(org.id),
        folio=folio,
        name=f"Proyecto {folio}",
        description="",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add(p)
    await db_session.flush()
    area = ProjectArea(
        tenant_id=tenant.id,
        project_id=p.id,
        name="Tecnología",
        type="area",
        is_active=True,
    )
    db_session.add(area)
    await db_session.flush()
    await db_session.commit()
    return p, area


@pytest.mark.asyncio
async def test_enh020_create_external_resource(client, db_session):
    t, _u, auth = await _admin(client, db_session, slug="rsc-ext")
    _p, area = await _project_with_area(db_session, t, folio="P-A10")

    r = await client.post(
        f"/api/v1/project-areas/{area.id}/resources",
        json={
            "name": "María Externa",
            "email": "maria@contratista.com",
            "role": "Analista",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] is None
    assert body["name"] == "María Externa"
    assert body["email"] == "maria@contratista.com"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_enh020_create_internal_resource(client, db_session):
    t, u, auth = await _admin(client, db_session, slug="rsc-int")
    _p, area = await _project_with_area(db_session, t, folio="P-A11")

    r = await client.post(
        f"/api/v1/project-areas/{area.id}/resources",
        json={"user_id": str(u.id), "role": "Líder técnico"},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == str(u.id)
    assert body["role"] == "Líder técnico"


@pytest.mark.asyncio
async def test_enh020_reject_resource_without_identity(client, db_session):
    t, _u, auth = await _admin(client, db_session, slug="rsc-none")
    _p, area = await _project_with_area(db_session, t, folio="P-A12")

    r = await client.post(
        f"/api/v1/project-areas/{area.id}/resources",
        json={"role": "Sin identidad"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_enh020_reject_duplicate_internal_user(client, db_session):
    t, u, auth = await _admin(client, db_session, slug="rsc-dup")
    _p, area = await _project_with_area(db_session, t, folio="P-A13")

    r1 = await client.post(
        f"/api/v1/project-areas/{area.id}/resources",
        json={"user_id": str(u.id)},
        headers=auth["_authz"],
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/project-areas/{area.id}/resources",
        json={"user_id": str(u.id)},
        headers=auth["_authz"],
    )
    assert r2.status_code == 422
    assert "asignado" in r2.json()["detail"]["detail"].lower()


@pytest.mark.asyncio
async def test_enh020_list_and_delete(client, db_session):
    t, _u, auth = await _admin(client, db_session, slug="rsc-list")
    _p, area = await _project_with_area(db_session, t, folio="P-A14")

    db_session.add_all(
        [
            ProjectAreaResource(
                tenant_id=t.id, area_id=area.id, name="A", email="a@x.com"
            ),
            ProjectAreaResource(
                tenant_id=t.id, area_id=area.id, name="B", email="b@x.com"
            ),
        ]
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/project-areas/{area.id}/resources",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2

    rid = body[0]["id"]
    d = await client.delete(
        f"/api/v1/project-area-resources/{rid}", headers=auth["_authz"]
    )
    assert d.status_code == 204

    r2 = await client.get(
        f"/api/v1/project-areas/{area.id}/resources",
        headers=auth["_authz"],
    )
    assert len(r2.json()) == 1


@pytest.mark.asyncio
async def test_us062_area_leader_set_and_update(client, db_session):
    t, u, auth = await _admin(client, db_session, slug="area-leader")
    p, _ = await _project_with_area(db_session, t, folio="P-A15")

    created = await client.post(
        f"/api/v1/projects/{p.id}/areas",
        json={
            "name": "Nueva Área",
            "type": "area",
            "area_leader_id": str(u.id),
        },
        headers=auth["_authz"],
    )
    assert created.status_code == 201, created.text
    assert created.json()["area_leader_id"] == str(u.id)

    area_id = created.json()["id"]
    updated = await client.patch(
        f"/api/v1/project-areas/{area_id}",
        json={"area_leader_id": None},
        headers=auth["_authz"],
    )
    assert updated.status_code == 200
    assert updated.json()["area_leader_id"] is None


@pytest.mark.asyncio
async def test_us062_area_leader_cross_tenant_rejected(client, db_session):
    t_a, _ua, auth_a = await _admin(client, db_session, slug="leader-ta")
    _, u_b, _auth_b = await _admin(client, db_session, slug="leader-tb")
    p, _ = await _project_with_area(db_session, t_a, folio="P-A16")

    # u_b pertenece al tenant B; no debe poder asignarse como leader en tenant A.
    r = await client.post(
        f"/api/v1/projects/{p.id}/areas",
        json={
            "name": "Área con líder de otro tenant",
            "type": "area",
            "area_leader_id": str(u_b.id),
        },
        headers=auth_a["_authz"],
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_enh020_cross_tenant_resource_404(client, db_session):
    t_a, _, _auth_a = await _admin(client, db_session, slug="rsc-cross-a")
    _, _u_b, auth_b = await _admin(client, db_session, slug="rsc-cross-b")
    _p, area = await _project_with_area(db_session, t_a, folio="P-A17")

    r = await client.post(
        f"/api/v1/project-areas/{area.id}/resources",
        json={"name": "Ajeno", "email": "x@y.com"},
        headers=auth_b["_authz"],
    )
    assert r.status_code == 404
