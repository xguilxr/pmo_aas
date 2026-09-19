"""BUG-106 / DEC-044 — tres rutas que asignaban un actor validando solo el inquilino.

Ninguna pasa por `create_participation`, así que BUG-103 no las cubrió:

1. Responsables de una acción de mitigación de riesgo.
2. El pool del matcher difuso al confirmar una importación de plan.
3. El dueño de un portafolio.

La tercera es la más fácil de cometer a mano —las dos organizaciones salen en
el mismo desplegable— y la segunda la más difícil de ver, porque ahí nadie
elige: empareja un algoritmo.
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
                "description": "BUG-106",
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


async def _actor(client, auth, nombre, organization_id):
    cuerpo = {"name": nombre}
    if organization_id is not None:
        cuerpo["organization_id"] = organization_id
    r = await client.post("/api/v1/actors", json=cuerpo, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _area(client, auth, organization_id, nombre="Área"):
    r = await client.post(
        "/api/v1/areas",
        json={"name": nombre, "organization_id": organization_id},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _riesgo(client, auth, project_id, area_id):
    r = await client.post(
        f"/api/v1/projects/{project_id}/risks",
        json={
            "title": "Riesgo de prueba",
            "description": "BUG-106",
            "status": "open",
            "category": "tecnico",
            "probability": 3,
            "impact": 3,
            "area_id": area_id,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_bug106_una_accion_no_acepta_responsable_de_otra_organizacion(
    client, db_session
):
    """TC-001: por API directa, no solo desde el desplegable.

    El selector ya filtraba desde BUG-103. Un filtro que solo vive en el
    cliente no es un filtro.
    """
    auth, orgs, proyectos = await _setup(client, db_session)
    area = await _area(client, auth, orgs["a"])
    riesgo = await _riesgo(client, auth, proyectos["a"], area)
    ajeno = await _actor(client, auth, "Beto de B", orgs["b"])

    r = await client.post(
        f"/api/v1/risks/{riesgo}/actions",
        json={"short_desc": "Mitigar", "assignee_actor_ids": [ajeno]},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    # El endpoint descarta en silencio lo que no valida —era así antes de este
    # arreglo y no se cambia aquí—, así que lo que se comprueba es que el
    # ajeno no quedó asignado.
    assert r.json()["assignee_actor_ids"] == []


@pytest.mark.asyncio
async def test_bug106_una_accion_si_acepta_al_suyo_y_al_global(client, db_session):
    """TC-002: la regla no estorba a quien sí pertenece."""
    auth, orgs, proyectos = await _setup(client, db_session)
    area = await _area(client, auth, orgs["a"])
    riesgo = await _riesgo(client, auth, proyectos["a"], area)
    propio = await _actor(client, auth, "Ana de A", orgs["a"])
    global_ = await _actor(client, auth, "Gabriel Global", None)

    r = await client.post(
        f"/api/v1/risks/{riesgo}/actions",
        json={"short_desc": "Mitigar", "assignee_actor_ids": [propio, global_]},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert set(r.json()["assignee_actor_ids"]) == {propio, global_}


@pytest.mark.asyncio
async def test_bug106_editar_una_accion_tampoco_acepta_al_ajeno(client, db_session):
    """TC-003: el PATCH reemplaza la lista y pasa por la misma validación."""
    auth, orgs, proyectos = await _setup(client, db_session)
    area = await _area(client, auth, orgs["a"])
    riesgo = await _riesgo(client, auth, proyectos["a"], area)
    propio = await _actor(client, auth, "Ana de A", orgs["a"])
    ajeno = await _actor(client, auth, "Beto de B", orgs["b"])

    creada = await client.post(
        f"/api/v1/risks/{riesgo}/actions",
        json={"short_desc": "Mitigar", "assignee_actor_ids": [propio]},
        headers=auth["_authz"],
    )
    assert creada.status_code == 201, creada.text

    r = await client.patch(
        f"/api/v1/risk-actions/{creada.json()['id']}",
        json={"assignee_actor_ids": [ajeno]},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["assignee_actor_ids"] == []


@pytest.mark.asyncio
async def test_bug106_el_dueno_del_portafolio_no_cruza(client, db_session):
    """TC-004: el caso más fácil de cometer a mano."""
    auth, orgs, _proyectos = await _setup(client, db_session)
    ajeno = await _actor(client, auth, "Beto de B", orgs["b"])

    r = await client.post(
        f"/api/v1/organizations/{orgs['a']}/portfolios",
        json={"name": "Portafolio de A", "owner_actor_id": ajeno},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_bug106_el_dueno_global_del_portafolio_si_vale(client, db_session):
    """TC-005: un PMO global puede ser dueño de cualquier portafolio."""
    auth, orgs, _proyectos = await _setup(client, db_session)
    global_ = await _actor(client, auth, "Gabriel Global", None)

    r = await client.post(
        f"/api/v1/organizations/{orgs['a']}/portfolios",
        json={"name": "Portafolio de A", "owner_actor_id": global_},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["owner_actor_id"] == global_


@pytest.mark.asyncio
async def test_bug106_editar_el_portafolio_tampoco_cruza(client, db_session):
    """TC-006: la edición pasa por la misma comprobación que el alta."""
    auth, orgs, _proyectos = await _setup(client, db_session)
    ajeno = await _actor(client, auth, "Beto de B", orgs["b"])
    pf = await client.post(
        f"/api/v1/organizations/{orgs['a']}/portfolios",
        json={"name": "Portafolio de A"},
        headers=auth["_authz"],
    )
    assert pf.status_code == 201, pf.text

    r = await client.patch(
        f"/api/v1/portfolios/{pf.json()['id']}",
        json={"owner_actor_id": ajeno},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
