"""US-182 — Actors como pool de recursos con capacidad.

Cubre:
- TC-182-1: crear actor con clasificación + capacidades persiste todo.
- TC-182-2: actor mínimo queda "sin clasificar" con defaults 100/100,
  compartido, no-clave, skills [].
- TC-182-3: PATCH actualiza capacidades/clasificación.
- TC-182-4: resource_type inválido → 422 (Literal).
- TC-182-5: list /actors filtra por resource_type y portfolio_function.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _auth(client, db_session) -> dict:
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin", email="admin@acme.example.com",
        password="Str0ng-Admin-1!", roles=[admin_role],
    )
    return await login(client, "admin", "Str0ng-Admin-1!")


@pytest.mark.asyncio
async def test_us182_create_with_resource_fields(client, db_session):
    auth = await _auth(client, db_session)
    r = await client.post(
        "/api/v1/actors",
        json={
            "name": "Carlos Mejia",
            "email": "carlos@cliente.example.com",
            "resource_type": "cliente_it",
            "portfolio_function": "arquitectura",
            "seniority": "senior",
            "scarcity_level": "alta",
            "location": "Monterrey",
            "skills_tags": ["SAP", "Integration"],
            "nominal_capacity_pct": 100,
            "project_capacity_pct": 60,
            "is_key_resource": True,
            "is_shared_resource": True,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["resource_type"] == "cliente_it"
    assert body["portfolio_function"] == "arquitectura"
    assert body["seniority"] == "senior"
    assert body["scarcity_level"] == "alta"
    assert body["skills_tags"] == ["SAP", "Integration"]
    assert float(body["project_capacity_pct"]) == 60
    assert body["is_key_resource"] is True


@pytest.mark.asyncio
async def test_us182_defaults_unclassified(client, db_session):
    auth = await _auth(client, db_session)
    r = await client.post(
        "/api/v1/actors", json={"name": "Ana Sin Clasificar"}, headers=auth["_authz"]
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["resource_type"] is None
    assert float(body["nominal_capacity_pct"]) == 100
    assert float(body["project_capacity_pct"]) == 100
    assert body["is_key_resource"] is False
    assert body["is_shared_resource"] is True
    assert body["skills_tags"] == []


@pytest.mark.asyncio
async def test_us182_patch_capacity(client, db_session):
    auth = await _auth(client, db_session)
    r = await client.post(
        "/api/v1/actors", json={"name": "Eli Gomora"}, headers=auth["_authz"]
    )
    actor_id = r.json()["id"]
    r = await client.patch(
        f"/api/v1/actors/{actor_id}",
        json={
            "project_capacity_pct": 50,
            "resource_type": "cliente_negocio",
            "is_key_resource": True,
            "scarcity_level": "alta",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["project_capacity_pct"]) == 50
    assert body["resource_type"] == "cliente_negocio"
    assert body["is_key_resource"] is True


@pytest.mark.asyncio
async def test_us182_invalid_resource_type_422(client, db_session):
    auth = await _auth(client, db_session)
    r = await client.post(
        "/api/v1/actors",
        json={"name": "X Y", "resource_type": "contractor"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_us182_list_filters(client, db_session):
    auth = await _auth(client, db_session)
    for name, rt, pf in (
        ("Arq Uno", "cliente_it", "arquitectura"),
        ("Arq Dos", "e4_tecnologia", "arquitectura"),
        ("PM Uno", "e4_pmo", "pm"),
    ):
        await client.post(
            "/api/v1/actors",
            json={"name": name, "resource_type": rt, "portfolio_function": pf},
            headers=auth["_authz"],
        )
    r = await client.get(
        "/api/v1/actors?portfolio_function=arquitectura", headers=auth["_authz"]
    )
    assert {a["name"] for a in r.json()} == {"Arq Uno", "Arq Dos"}
    r = await client.get(
        "/api/v1/actors?resource_type=e4_pmo", headers=auth["_authz"]
    )
    assert {a["name"] for a in r.json()} == {"PM Uno"}
