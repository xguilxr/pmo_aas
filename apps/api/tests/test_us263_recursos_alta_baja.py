"""US-263 (FASE-6, revamp v2, DEC-038) — alta y baja de recursos por organización.

1. La unicidad de `POST /actors` es por `(tenant, organización, correo)`:
   el mismo correo en la misma organización → 409; en otra organización →
   se crea (punto 5 del feedback).
2. `DELETE /actors/{id}` rechaza si el actor tiene participaciones activas
   en proyectos; sin ellas, lo da de baja (soft-delete).
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.organization import Organization
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session, slug="us263", name="US263")
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin263", email="admin263@pmoaas.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    auth = await login(client, "admin263", "Str0ng-Admin-1!")
    org_a = (
        await client.post("/api/v1/organizations", json={"name": "Org A"}, headers=auth["_authz"])
    ).json()
    org_b = (
        await client.post("/api/v1/organizations", json={"name": "Org B"}, headers=auth["_authz"])
    ).json()
    return t, auth, org_a["id"], org_b["id"]


@pytest.mark.asyncio
async def test_mismo_correo_en_la_misma_organizacion_409(client, db_session):
    _, auth, org_a, _org_b = await _setup(client, db_session)
    body = {"name": "Ana Ruiz", "email": "ana@example.com", "organization_id": org_a}
    r1 = await client.post("/api/v1/actors", json=body, headers=auth["_authz"])
    assert r1.status_code == 201, r1.text

    r2 = await client.post(
        "/api/v1/actors",
        json={"name": "Otra Ana", "email": "ana@example.com", "organization_id": org_a},
        headers=auth["_authz"],
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["detail"]["code"] == "ACTOR_EMAIL_DUPLICATE"


@pytest.mark.asyncio
async def test_mismo_correo_en_otra_organizacion_se_crea(client, db_session):
    _, auth, org_a, org_b = await _setup(client, db_session)
    r1 = await client.post(
        "/api/v1/actors",
        json={"name": "Ana Ruiz", "email": "ana@example.com", "organization_id": org_a},
        headers=auth["_authz"],
    )
    assert r1.status_code == 201, r1.text

    # DEC-038 — el mismo correo en OTRA organización del tenant es un actor
    # distinto e independiente, no el mismo compartido.
    r2 = await client.post(
        "/api/v1/actors",
        json={"name": "Ana Ruiz", "email": "ana@example.com", "organization_id": org_b},
        headers=auth["_authz"],
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["id"] != r1.json()["id"]


@pytest.mark.asyncio
async def test_quitar_actor_sin_participaciones_lo_da_de_baja(client, db_session):
    _, auth, org_a, _org_b = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/actors",
        json={"name": "Roberto Vega", "email": "roberto@example.com", "organization_id": org_a},
        headers=auth["_authz"],
    )
    actor_id = r.json()["id"]

    d = await client.delete(f"/api/v1/actors/{actor_id}", headers=auth["_authz"])
    assert d.status_code == 204, d.text


@pytest.mark.asyncio
async def test_quitar_actor_con_participacion_activa_se_rechaza(client, db_session):
    tenant, auth, org_a, _org_b = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/actors",
        json={"name": "Roberto Vega", "email": "roberto2@example.com", "organization_id": org_a},
        headers=auth["_authz"],
    )
    actor_id = r.json()["id"]

    org = (await db_session.execute(select(Organization).where(Organization.id == org_a))).scalar_one()
    project = Project(
        tenant_id=tenant.id,
        organization_id=org.id,
        folio="PRJ-US263",
        name="Proyecto con recurso",
        phase="ejecucion",
    )
    db_session.add(project)
    await db_session.flush()
    participation = ProjectParticipation(
        tenant_id=tenant.id,
        project_id=project.id,
        actor_id=actor_id,
        is_active=True,
    )
    db_session.add(participation)
    await db_session.commit()

    d = await client.delete(f"/api/v1/actors/{actor_id}", headers=auth["_authz"])
    assert d.status_code in (400, 409, 422), d.text
