"""BUG-104 — una participación cruzada no bloquea el borrado del recurso.

`delete_actor` contaba cualquier participación activa en un proyecto vivo y
abierto. Con la regla de DEC-044, una participación en un proyecto de otra
organización es un dato inválido —no algo que proteger—, y ninguna pantalla
de la organización del recurso la muestra: el owner veía un bloqueo sin nada
que quitar. Ahora se desactiva al borrar y queda escrita en la auditoría.
"""
import pytest
from sqlalchemy import select

from app.models.area import Actor
from app.models.project_participation import ProjectParticipation
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
                "description": "BUG-104",
                "type": "transformacion",
                "priority": 3,
                "organization_id": orgs[clave],
                "pm_id": me["id"],
            },
            headers=auth["_authz"],
        )
        assert p.status_code == 201, p.text
        proyectos[clave] = p.json()["id"]
    return auth, orgs, proyectos, str(tenant.id)


async def _actor(client, auth, nombre, organization_id):
    cuerpo = {"name": nombre}
    if organization_id is not None:
        cuerpo["organization_id"] = organization_id
    r = await client.post("/api/v1/actors", json=cuerpo, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_bug104_un_cruce_no_bloquea_y_se_desactiva(client, db_session):
    """TC-001: el recurso se retira, y el cruce que lo atrapaba se apaga."""
    auth, orgs, proyectos, tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])
    # A mano: la API ya no permite crear el cruce (BUG-103). Esto es el dato
    # heredado que el owner tiene hoy en producción.
    db_session.add(
        ProjectParticipation(
            tenant_id=tenant_id,
            project_id=proyectos["b"],
            actor_id=actor_a,
            is_active=True,
            is_primary=True,
        )
    )
    await db_session.commit()

    r = await client.delete(f"/api/v1/actors/{actor_a}", headers=auth["_authz"])
    assert r.status_code == 204, r.text

    db_session.expire_all()
    fila = (
        await db_session.execute(select(Actor).where(Actor.id == actor_a))
    ).scalar_one()
    assert fila.deleted_at is not None
    assert fila.is_active is False
    cruce = (
        await db_session.execute(
            select(ProjectParticipation).where(
                ProjectParticipation.actor_id == actor_a
            )
        )
    ).scalar_one()
    assert cruce.is_active is False, "el cruce no puede quedar apuntando a un borrado"
    # `derived_assignment.py` ordena por `is_primary.desc(), is_active.desc()`
    # y no filtra `is_active`: una cruzada apagada que siguiera siendo primary
    # le ganaría a la participación legítima y seguiría dictando el área
    # funcional del actor. Apagar sin quitar la marca no se nota en pantalla.
    assert cruce.is_primary is False, "apagada y además sin la marca de primary"


@pytest.mark.asyncio
async def test_bug104_su_propia_organizacion_sigue_bloqueando(client, db_session):
    """TC-002: la protección original no se afloja donde sí aplica."""
    auth, orgs, proyectos, _tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])
    r = await client.post(
        f"/api/v1/projects/{proyectos['a']}/participations",
        json={"actor_id": actor_a},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text

    r = await client.delete(f"/api/v1/actors/{actor_a}", headers=auth["_authz"])
    assert r.status_code == 422, r.text
    assert "Proyecto Org A" in r.json()["detail"]["detail"]


@pytest.mark.asyncio
async def test_bug104_el_global_sigue_bloqueado_por_cualquier_proyecto(
    client, db_session
):
    """TC-003: para el recurso global ningún proyecto es ajeno.

    Sin esta distinción, «no cuentes los de otra organización» dejaría al
    recurso global sin ninguna protección: no tiene organización propia, así
    que todos sus proyectos parecerían ajenos.
    """
    auth, _orgs, proyectos, _tenant_id = await _setup(client, db_session)
    global_ = await _actor(client, auth, "Gabriel Global", None)
    r = await client.post(
        f"/api/v1/projects/{proyectos['b']}/participations",
        json={"actor_id": global_},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text

    r = await client.delete(f"/api/v1/actors/{global_}", headers=auth["_authz"])
    assert r.status_code == 422, r.text
    assert "Proyecto Org B" in r.json()["detail"]["detail"]
