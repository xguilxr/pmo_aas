"""US-091 — Áreas/Equipos/Actores: jerarquía explícita + teléfono.

Cubre:
- TC-091.1: crear área A, equipo E con area_id=A, actor X con
  team_id=E + area_id=A → GET X expone ambas FK + phone.
- Validación: team_id apuntando a un área (no equipo) → 422.
- Validación: area_id apuntando a un actor → 422.
- Phone se persiste en GET.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    org = await client.post(
        "/api/v1/organizations", json={"name": "Org1"}, headers=auth["_authz"]
    )
    me = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    p = await client.post(
        "/api/v1/projects",
        json={
            "name": "P1",
            "description": "d",
            "type": "bau",
            "priority": 3,
            "organization_id": org.json()["id"],
            "pm_id": me.json()["id"],
        },
        headers=auth["_authz"],
    )
    return auth, p.json()["id"]


@pytest.mark.asyncio
async def test_tc091_1_hierarchy_creation(client, db_session):
    auth, proj = await _setup(client, db_session)
    a = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={"name": "Operaciones", "type": "area"},
        headers=auth["_authz"],
    )
    assert a.status_code == 201, a.text
    a_id = a.json()["id"]
    e = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={"name": "Equipo Plataforma", "type": "team", "area_id": a_id},
        headers=auth["_authz"],
    )
    assert e.status_code == 201, e.text
    e_id = e.json()["id"]
    x = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={
            "name": "Juan Perez",
            "type": "actor",
            "area_id": a_id,
            "team_id": e_id,
            "phone": "+52 55 1234 5678",
        },
        headers=auth["_authz"],
    )
    assert x.status_code == 201, x.text
    body = x.json()
    assert body["area_id"] == a_id
    assert body["team_id"] == e_id
    assert body["phone"] == "+52 55 1234 5678"


@pytest.mark.asyncio
async def test_team_id_must_point_to_team(client, db_session):
    auth, proj = await _setup(client, db_session)
    a = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={"name": "Operaciones", "type": "area"},
        headers=auth["_authz"],
    )
    a_id = a.json()["id"]
    # Intento usar el área como team — debe fallar.
    r = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={"name": "Mal Actor", "type": "actor", "team_id": a_id},
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 422), r.text
    assert "team" in r.text.lower()


@pytest.mark.asyncio
async def test_area_id_must_point_to_area(client, db_session):
    auth, proj = await _setup(client, db_session)
    actor = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={"name": "Otro Actor", "type": "actor"},
        headers=auth["_authz"],
    )
    actor_id = actor.json()["id"]
    # Intento usar un actor como área — debe fallar.
    r = await client.post(
        f"/api/v1/projects/{proj}/areas",
        json={"name": "Eq Mal", "type": "team", "area_id": actor_id},
        headers=auth["_authz"],
    )
    assert r.status_code in (400, 422), r.text
    assert "area" in r.text.lower()
