"""US-126 — Plantillas privadas + publicar al proyecto (EP020).

TC-218 (privacidad respetada), TC-219 (publicar/despublicar),
TC-220 (RLS por proyecto).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.organization import Organization
from app.models.project import Project
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session, slug):
    t = await create_tenant(db_session, slug=slug, name=slug)
    role = await create_admin_role(db_session, t)
    u1 = await create_user(
        db_session,
        tenant=t,
        username=f"u1_{slug}",
        email=f"u1@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    u2 = await create_user(
        db_session,
        tenant=t,
        username=f"u2_{slug}",
        email=f"u2@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[role],
    )
    org = Organization(tenant_id=t.id, name="Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    p1 = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-1",
        name="Proj 1",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    p2 = Project(
        tenant_id=str(t.id),
        organization_id=str(org.id),
        folio="P-2",
        name="Proj 2",
        phase="execution",
        health_status="green",
        budget=Decimal("0"),
        actual_budget=Decimal("0"),
        progress=0,
    )
    db_session.add_all([p1, p2])
    await db_session.flush()
    await db_session.commit()
    auth1 = await login(client, f"u1_{slug}", "Str0ng-Admin-1!")
    auth2 = await login(client, f"u2_{slug}", "Str0ng-Admin-1!")
    return t, p1, p2, u1, u2, auth1, auth2


@pytest.mark.asyncio
async def test_tc218_private_visible_only_to_owner(client, db_session):
    t, p1, p2, u1, u2, auth1, auth2 = await _setup(client, db_session, "us126-priv")
    r = await client.post(
        "/api/v1/report-builder-templates",
        headers=auth1["_authz"],
        json={
            "code": "T-PRIV",
            "name": "Privada de u1",
            "level": 4,
            "composition_mode": "A",
            "section_codes": ["S-01"],
            "default_parameters": {},
            "visibility": "private",
        },
    )
    assert r.status_code == 201, r.text

    # u1 la ve, u2 no.
    r1 = await client.get("/api/v1/report-builder-templates", headers=auth1["_authz"])
    assert any(t["code"] == "T-PRIV" for t in r1.json())
    r2 = await client.get("/api/v1/report-builder-templates", headers=auth2["_authz"])
    assert all(t["code"] != "T-PRIV" for t in r2.json())


@pytest.mark.asyncio
async def test_tc219_publish_and_unpublish(client, db_session):
    t, p1, p2, u1, u2, auth1, auth2 = await _setup(client, db_session, "us126-pub")
    # Crear privada y publicar al proyecto p1.
    r = await client.post(
        "/api/v1/report-builder-templates",
        headers=auth1["_authz"],
        json={
            "code": "T-PUB",
            "name": "Para publicar",
            "level": 4,
            "composition_mode": "A",
            "section_codes": ["S-01"],
            "default_parameters": {},
            "visibility": "private",
        },
    )
    tpl = r.json()
    assert tpl["visibility"] == "private"
    tid = tpl["id"]

    # u2 NO la ve filtrando por proyecto.
    r2 = await client.get(
        f"/api/v1/report-builder-templates?project_id={p1.id}",
        headers=auth2["_authz"],
    )
    assert all(t["code"] != "T-PUB" for t in r2.json())

    # u1 publica al proyecto p1.
    rp = await client.patch(
        f"/api/v1/report-builder-templates/{tid}",
        headers=auth1["_authz"],
        json={"visibility": "project", "project_id": str(p1.id)},
    )
    assert rp.status_code == 200, rp.text
    assert rp.json()["visibility"] == "project"

    # Ahora u2 SÍ la ve cuando filtra por p1.
    r2 = await client.get(
        f"/api/v1/report-builder-templates?project_id={p1.id}",
        headers=auth2["_authz"],
    )
    assert any(t["code"] == "T-PUB" for t in r2.json())

    # Pero no si filtra por p2 (TC-220 RLS por proyecto).
    r2b = await client.get(
        f"/api/v1/report-builder-templates?project_id={p2.id}",
        headers=auth2["_authz"],
    )
    assert all(t["code"] != "T-PUB" for t in r2b.json())

    # u1 despublica.
    rpu = await client.patch(
        f"/api/v1/report-builder-templates/{tid}",
        headers=auth1["_authz"],
        json={"visibility": "private"},
    )
    assert rpu.status_code == 200

    r2 = await client.get(
        f"/api/v1/report-builder-templates?project_id={p1.id}",
        headers=auth2["_authz"],
    )
    assert all(t["code"] != "T-PUB" for t in r2.json())


@pytest.mark.asyncio
async def test_only_owner_can_modify(client, db_session):
    t, p1, p2, u1, u2, auth1, auth2 = await _setup(client, db_session, "us126-mod")
    r = await client.post(
        "/api/v1/report-builder-templates",
        headers=auth1["_authz"],
        json={
            "code": "T-OWN",
            "name": "Sólo u1",
            "level": 4,
            "composition_mode": "A",
            "section_codes": ["S-01"],
            "default_parameters": {},
            "visibility": "private",
        },
    )
    tid = r.json()["id"]

    # u2 no puede modificar.
    rp = await client.patch(
        f"/api/v1/report-builder-templates/{tid}",
        headers=auth2["_authz"],
        json={"name": "Hack"},
    )
    assert rp.status_code == 403

    # u2 no puede borrar.
    rd = await client.delete(
        f"/api/v1/report-builder-templates/{tid}", headers=auth2["_authz"]
    )
    assert rd.status_code == 403

    # u1 sí puede borrar.
    rd1 = await client.delete(
        f"/api/v1/report-builder-templates/{tid}", headers=auth1["_authz"]
    )
    assert rd1.status_code == 204
