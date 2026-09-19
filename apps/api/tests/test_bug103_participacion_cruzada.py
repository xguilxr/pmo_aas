"""BUG-103 / DEC-044 — un recurso no cruza de organización.

La regla: `actors.organization_id` puesto ata al actor a esa organización;
nulo lo deja global al inquilino y sirve a cualquiera. Hasta este arreglo
`create_participation` solo comprobaba el inquilino, así que el cruce se
creaba sin resistencia y después bloqueaba el borrado del recurso en su
propia organización.
"""
import pytest
from sqlalchemy import select

from app.models.project_participation import ProjectParticipation
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session):
    """Dos organizaciones con un proyecto cada una, en el mismo inquilino."""
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
    pm_id = me["id"]
    orgs = {}
    proyectos = {}
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
                "description": "BUG-103",
                "type": "transformacion",
                "priority": 3,
                "organization_id": orgs[clave],
                "pm_id": pm_id,
            },
            headers=auth["_authz"],
        )
        assert p.status_code == 201, p.text
        proyectos[clave] = p.json()["id"]
    return auth, orgs, proyectos, str(tenant.id)


async def _actor(client, auth, nombre: str, organization_id: str | None) -> str:
    cuerpo: dict = {"name": nombre}
    if organization_id is not None:
        cuerpo["organization_id"] = organization_id
    r = await client.post("/api/v1/actors", json=cuerpo, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _asignar(client, auth, project_id: str, actor_id: str):
    return await client.post(
        f"/api/v1/projects/{project_id}/participations",
        json={"actor_id": actor_id},
        headers=auth["_authz"],
    )


@pytest.mark.asyncio
async def test_bug103_actor_de_otra_organizacion_no_se_asigna(client, db_session):
    """TC-001: el actor de la organización A no entra al proyecto de la B."""
    auth, orgs, proyectos, _tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])

    r = await _asignar(client, auth, proyectos["b"], actor_a)

    assert r.status_code == 422, r.text
    detalle = r.json()["detail"]
    assert detalle["code"] == "ACTOR_DE_OTRA_ORGANIZACION"
    # El mensaje nombra a la persona: sin el nombre, quien lo lee no sabe
    # cuál de las cinco filas del desplegable es la que sobra.
    assert "Ana de A" in detalle["detail"]


@pytest.mark.asyncio
async def test_bug103_actor_de_la_misma_organizacion_si_se_asigna(client, db_session):
    """TC-002: la regla no estorba al caso normal."""
    auth, orgs, proyectos, _tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])

    r = await _asignar(client, auth, proyectos["a"], actor_a)

    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_bug103_actor_global_sirve_a_cualquier_organizacion(client, db_session):
    """TC-003: `organization_id` nulo es un recurso del inquilino, no un huérfano."""
    auth, _orgs, proyectos, _tenant_id = await _setup(client, db_session)
    global_ = await _actor(client, auth, "Gabriel Global", None)

    for clave in ("a", "b"):
        r = await _asignar(client, auth, proyectos[clave], global_)
        assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_bug103_asignable_en_incluye_al_global_y_excluye_al_ajeno(
    client, db_session
):
    """TC-004: `asignable_en` responde «puede trabajar aquí», no «es de aquí».

    `organization_id` sigue respondiendo la otra pregunta, y por eso los dos
    parámetros conviven: el catálogo de Recursos quiere los suyos, el selector
    de un proyecto quiere los suyos **más** los globales.
    """
    auth, orgs, _proyectos, _tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])
    actor_b = await _actor(client, auth, "Beto de B", orgs["b"])
    global_ = await _actor(client, auth, "Gabriel Global", None)

    r = await client.get(
        f"/api/v1/actors?asignable_en={orgs['a']}", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    ids = {fila["id"] for fila in r.json()}
    assert actor_a in ids
    assert global_ in ids
    assert actor_b not in ids

    r = await client.get(
        f"/api/v1/actors?organization_id={orgs['a']}", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    ids = {fila["id"] for fila in r.json()}
    assert actor_a in ids
    assert global_ not in ids
    assert actor_b not in ids


@pytest.mark.asyncio
async def test_bug103_eligible_actors_no_ofrece_un_cruce_heredado(client, db_session):
    """TC-005: una participación cruzada vieja deja de ofrecerse como responsable.

    Se inserta a mano porque la API ya no deja crearla. Es el dato que existe
    hoy en producción, y ofrecerlo sería proponer un valor que la propia API
    rechaza al guardarlo.
    """
    auth, orgs, proyectos, tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])
    global_ = await _actor(client, auth, "Gabriel Global", None)
    assert (await _asignar(client, auth, proyectos["b"], global_)).status_code == 201

    db_session.add(
        ProjectParticipation(
            tenant_id=tenant_id,
            project_id=proyectos["b"],
            actor_id=actor_a,
            is_active=True,
        )
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/projects/{proyectos['b']}/eligible-actors", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    ids = {fila["id"] for fila in r.json()}
    assert global_ in ids
    assert actor_a not in ids


@pytest.mark.asyncio
async def test_bug103_un_cruce_apagado_no_se_revive_con_un_patch(client, db_session):
    """TC-006: la puerta de atrás del PATCH.

    `ParticipationUpdate` no expone `actor_id`, así que no se puede mover la
    participación. Lo que sí se podía era volver a encender con
    `is_active=true` la que la limpieza acababa de apagar.
    """
    auth, orgs, proyectos, tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])
    cruce = ProjectParticipation(
        tenant_id=tenant_id,
        project_id=proyectos["b"],
        actor_id=actor_a,
        is_active=False,
    )
    db_session.add(cruce)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/projects/{proyectos['b']}/participations/{cruce.id}",
        json={"is_active": True},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "ACTOR_DE_OTRA_ORGANIZACION"


@pytest.mark.asyncio
async def test_bug103_una_participacion_legitima_si_se_reactiva(client, db_session):
    """TC-007: el cierre no estorba a quien sí pertenece."""
    auth, orgs, proyectos, tenant_id = await _setup(client, db_session)
    actor_a = await _actor(client, auth, "Ana de A", orgs["a"])
    suya = ProjectParticipation(
        tenant_id=tenant_id,
        project_id=proyectos["a"],
        actor_id=actor_a,
        is_active=False,
    )
    db_session.add(suya)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/projects/{proyectos['a']}/participations/{suya.id}",
        json={"is_active": True},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is True


@pytest.mark.asyncio
async def test_bug103_quitar_a_un_miembro_con_actor_en_dos_organizaciones(
    client, db_session
):
    """TC-008: el sincronizador no revienta con dos actores del mismo usuario.

    `_ensure_actor_for_user` crea un actor por organización desde este mismo
    arreglo. `sync_member_removal` resolvía **uno** con `scalar_one_or_none()`
    y por tanto se rompía en cuanto existiera el segundo.
    """
    from app.models.area import Actor as _Actor
    from app.services.project_membership_sync import (
        sync_member_removal,
        sync_member_to_participation,
    )

    auth, _orgs, proyectos, tenant_id = await _setup(client, db_session)
    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()

    for clave in ("a", "b"):
        await sync_member_to_participation(
            db_session, tenant_id, proyectos[clave], me["id"], "pm"
        )
    await db_session.commit()

    suyos = (
        await db_session.execute(
            select(_Actor).where(_Actor.user_id == me["id"])
        )
    ).scalars().all()
    assert len(suyos) >= 2, "un actor por organización (DEC-038)"

    # No lanza MultipleResultsFound, y retira solo las de este proyecto.
    await sync_member_removal(db_session, proyectos["a"], me["id"])
    await db_session.commit()

    vivas = (
        await db_session.execute(
            select(ProjectParticipation).where(
                ProjectParticipation.actor_id.in_([str(x.id) for x in suyos]),
                ProjectParticipation.is_active.is_(True),
            )
        )
    ).scalars().all()
    assert {str(p.project_id) for p in vivas} == {proyectos["b"]}
