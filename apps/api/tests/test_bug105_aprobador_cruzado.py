"""BUG-105 / DEC-044 — un aprobador de otra organización no entra al cambio.

`add_approver` validaba solo el inquilino. Importa más que las otras rutas del
mismo defecto porque su efecto sale del producto: al enviar a aprobación,
US-113 manda el contenido del cambio al correo del aprobador.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    tenant = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, tenant)
    await create_user(
        db_session,
        tenant=tenant,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()
    orgs, proyectos = {}, {}
    for clave, nombre in (("a", "Org A"), ("b", "Org B")):
        r = await client.post(
            "/api/v1/organizations", json={"name": nombre}, headers=auth["_authz"]
        )
        assert r.status_code == 201, r.text
        orgs[clave] = r.json()["id"]
        p = await client.post(
            "/api/v1/projects",
            json={
                "name": f"Proyecto {nombre}",
                "description": "BUG-105",
                "type": "transformacion",
                "priority": 3,
                "organization_id": orgs[clave],
                "pm_id": me["id"],
            },
            headers=auth["_authz"],
        )
        assert p.status_code == 201, p.text
        proyectos[clave] = p.json()["id"]
    return auth, orgs, proyectos


async def _cambio(client, auth, project_id: str) -> str:
    r = await client.post(
        f"/api/v1/projects/{project_id}/change-requests",
        json={
            "title": "Cambio de alcance",
            "description": "BUG-105",
            "type": "scope",
            "status": "draft",
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _actor(client, auth, nombre, organization_id, email):
    cuerpo = {"name": nombre, "email": email}
    if organization_id is not None:
        cuerpo["organization_id"] = organization_id
    r = await client.post("/api/v1/actors", json=cuerpo, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_bug105_aprobador_de_otra_organizacion_se_rechaza(client, db_session):
    """TC-001: el correo del cambio no sale de la organización del proyecto."""
    auth, orgs, proyectos = await _setup(client, db_session)
    cambio = await _cambio(client, auth, proyectos["a"])
    ajeno = await _actor(client, auth, "Beto de B", orgs["b"], "beto@b.example.com")

    r = await client.post(
        f"/api/v1/change-requests/{cambio}/approvers",
        json={"actor_id": ajeno},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "ACTOR_DE_OTRA_ORGANIZACION"
    assert "Beto de B" in r.json()["detail"]["detail"]


@pytest.mark.asyncio
async def test_bug105_el_de_la_misma_organizacion_si_aprueba(client, db_session):
    """TC-002: el caso normal no se estorba."""
    auth, orgs, proyectos = await _setup(client, db_session)
    cambio = await _cambio(client, auth, proyectos["a"])
    propio = await _actor(client, auth, "Ana de A", orgs["a"], "ana@a.example.com")

    r = await client.post(
        f"/api/v1/change-requests/{cambio}/approvers",
        json={"actor_id": propio},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_bug105_el_recurso_global_si_aprueba(client, db_session):
    """TC-003: sin organización es del inquilino y aprueba en cualquiera."""
    auth, _orgs, proyectos = await _setup(client, db_session)
    cambio = await _cambio(client, auth, proyectos["b"])
    global_ = await _actor(client, auth, "Gabriel", None, "gabriel@acme.example.com")

    r = await client.post(
        f"/api/v1/change-requests/{cambio}/approvers",
        json={"actor_id": global_},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
