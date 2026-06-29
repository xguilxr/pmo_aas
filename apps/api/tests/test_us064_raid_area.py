"""US-064 — RAID area_id obligatorio en creación + ordering por área."""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1", "description": "d", "type": "innovation",
            "priority": 3, "organization_id": org_id, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    proj_id = r.json()["id"]
    return t, auth, proj_id, org_id


async def _area(client, auth, proj_id, name, org_id: str | None = None):
    """ENH-078: crea área en catálogo tenant + asigna al proyecto."""
    area_body: dict = {"name": name}
    if org_id:
        area_body["organization_id"] = org_id
    r = await client.post(
        "/api/v1/areas",
        json=area_body,
        headers=auth["_authz"],
    )
    aid = r.json()["id"]
    await client.put(
        f"/api/v1/admin/areas/{aid}/assignments",
        json={"scopes": [{"project_id": proj_id}]},
        headers=auth["_authz"],
    )
    return aid


# TC-064.1 — POST /risks sin area_id → 422
@pytest.mark.asyncio
async def test_tc064_1_risk_requires_area_id(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={"title": "R sin área", "probability": 3, "impact": 3},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-064.1b — POST /issues sin area_id → 422
@pytest.mark.asyncio
async def test_tc064_1b_issue_requires_area_id(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/issues",
        json={"title": "I sin área", "type": "action"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


# TC-064.2 — POST /risks con area_id válido → 201 + area embebida en Read
@pytest.mark.asyncio
async def test_tc064_2_risk_with_area_embeds(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)
    area_id = await _area(client, auth, proj_id, "Finanzas", org_id)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "R con área", "probability": 4, "impact": 4,
            "area_id": area_id,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["area_id"] == area_id
    assert body["area"] == {"id": area_id, "name": "Finanzas"}


# TC-035 — BUG-035: POST/GET /risks devuelve `owner` con full_name + email.
@pytest.mark.asyncio
async def test_bug035_risk_embeds_owner(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)
    area_id = await _area(client, auth, proj_id, "Finanzas", org_id)
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    me_id = me.json()["id"]

    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo con owner", "probability": 3, "impact": 3,
            "area_id": area_id, "owner_id": me_id,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["owner_id"] == me_id
    assert body["owner"] is not None
    assert body["owner"]["id"] == me_id
    assert body["owner"]["email"] == "admin@acme.example.com"

    # GET detail también lo embebe.
    r2 = await client.get(f"/api/v1/risks/{body['id']}", headers=auth["_authz"])
    assert r2.status_code == 200
    assert r2.json()["owner"]["email"] == "admin@acme.example.com"

    # Riesgo sin owner: owner=None.
    r3 = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Riesgo sin owner", "probability": 2, "impact": 2,
            "area_id": area_id,
        },
        headers=auth["_authz"],
    )
    assert r3.status_code == 201
    assert r3.json()["owner"] is None


# TC-064.3 — GET lista ordena por área ASC → legacy NULL al final
@pytest.mark.asyncio
async def test_tc064_3_list_orders_by_area(client, db_session):

    from app.models.modules import Risk

    t, auth, proj_id, org_id = await _setup(client, db_session)
    a_z = await _area(client, auth, proj_id, "Zeta", org_id)
    a_a = await _area(client, auth, proj_id, "Alpha", org_id)
    for a, title in [(a_z, "Z-1"), (a_a, "A-1")]:
        await client.post(
            f"/api/v1/projects/{proj_id}/risks",
            json={
                "title": title, "probability": 3, "impact": 3, "area_id": a,
            },
            headers=auth["_authz"],
        )
    # Risk legacy (sin área) insertado a mano para simular pre-migración.
    from app.services.folio import next_folio
    folio = await next_folio(db_session, tenant_id=t.id, prefix="RIS")
    db_session.add(
        Risk(
            tenant_id=str(t.id), project_id=proj_id, folio=folio,
            title="Legacy sin área", status="open",
            probability=2, impact=2, severity=4,
        )
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/projects/{proj_id}/risks", headers=auth["_authz"]
    )
    assert r.status_code == 200
    rows = r.json()
    titles = [x["title"] for x in rows]
    # Alpha primero, Zeta segundo, legacy al final (por COALESCE 'ZZZ').
    assert titles.index("A-1") < titles.index("Z-1") < titles.index("Legacy sin área")


# TC-064.4 — PATCH asigna area a legacy
@pytest.mark.asyncio
async def test_tc064_4_patch_assigns_area(client, db_session):
    from app.models.modules import Risk
    from app.services.folio import next_folio

    t, auth, proj_id, org_id = await _setup(client, db_session)
    area_id = await _area(client, auth, proj_id, "RRHH", org_id)
    folio = await next_folio(db_session, tenant_id=t.id, prefix="RIS")
    r = Risk(
        tenant_id=str(t.id), project_id=proj_id, folio=folio,
        title="Legacy", status="open",
        probability=2, impact=2, severity=4,
    )
    db_session.add(r)
    await db_session.commit()

    p = await client.patch(
        f"/api/v1/risks/{r.id}",
        json={"area_id": area_id},
        headers=auth["_authz"],
    )
    assert p.status_code == 200, p.text
    assert p.json()["area_id"] == area_id


# TC-064.5 — filtro ?area_id= retorna solo de esa área
@pytest.mark.asyncio
async def test_tc064_5_filter_area_id(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)
    a1 = await _area(client, auth, proj_id, "A1", org_id)
    a2 = await _area(client, auth, proj_id, "A2", org_id)
    for a, t in [(a1, "En A1"), (a2, "En A2"), (a1, "Otro A1")]:
        await client.post(
            f"/api/v1/projects/{proj_id}/risks",
            json={
                "title": t, "probability": 3, "impact": 3, "area_id": a,
            },
            headers=auth["_authz"],
        )
    r = await client.get(
        f"/api/v1/projects/{proj_id}/risks?area_id={a1}",
        headers=auth["_authz"],
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert all(x["area_id"] == a1 for x in rows)


# TC-064.6 — area_id de otro proyecto → 422
@pytest.mark.asyncio
async def test_tc064_6_area_must_belong_to_project(client, db_session):
    _, auth, proj_id, org_id = await _setup(client, db_session)
    # Crear un segundo proyecto + área ajena.
    r = await client.post(
        "/api/v1/organizations", json={"name": "Org2"}, headers=auth["_authz"]
    )
    org2 = r.json()["id"]
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p2 = await client.post(
        "/api/v1/projects",
        json={
            "name": "P2", "description": "x", "type": "innovation",
            "priority": 3, "organization_id": org2, "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    foreign_area = await _area(client, auth, p2.json()["id"], "Foreign", org2)
    r = await client.post(
        f"/api/v1/projects/{proj_id}/risks",
        json={
            "title": "Bad area", "probability": 3, "impact": 3,
            "area_id": foreign_area,
        },
        headers=auth["_authz"],
    )
    # _validate_area lanza business_rule → 422
    assert r.status_code == 422
