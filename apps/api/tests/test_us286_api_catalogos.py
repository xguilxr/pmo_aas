"""US-286 — la API de catálogos y la validación del proyecto contra ella.

El servicio y la tabla son US-285. Aquí se prueba lo que ve quien llama: los
cuatro verbos del catálogo, y que un proyecto se valide contra el catálogo de
**su** inquilino y no contra el enum del dominio.
"""
import pytest

from tests.factories import create_admin_role, create_tenant, create_user, login


async def _setup(client, db_session, slug: str = "acme"):
    tenant = await create_tenant(db_session, slug=slug, name=slug.upper())
    admin_role = await create_admin_role(db_session, tenant)
    await create_user(
        db_session,
        tenant=tenant,
        username=f"admin_{slug}",
        email=f"admin@{slug}.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, f"admin_{slug}", "Str0ng-Admin-1!")
    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "Org 1"}, headers=auth["_authz"]
        )
    ).json()
    return auth, me["id"], org["id"]


async def _crear_proyecto(client, auth, org_id, pm_id, **extra):
    cuerpo = {
        "name": "Proyecto",
        "description": "US-286",
        "type": "transformacion",
        "priority": 3,
        "organization_id": org_id,
        "pm_id": pm_id,
    }
    cuerpo.update(extra)
    return await client.post(
        "/api/v1/projects", json=cuerpo, headers=auth["_authz"]
    )


@pytest.mark.asyncio
async def test_us286_el_catalogo_nace_con_los_valores_de_fabrica(client, db_session):
    auth, _pm, _org = await _setup(client, db_session)

    r = await client.get(
        "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    claves = [v["clave"] for v in r.json()]
    assert claves == ["transformacion", "operacion", "innovacion", "bau"]

    r = await client.get(
        "/api/v1/admin/catalogos/fase_proyecto", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert next(v["clave"] for v in r.json()) == "preparacion"


@pytest.mark.asyncio
async def test_us286_un_catalogo_inventado_no_existe(client, db_session):
    auth, _pm, _org = await _setup(client, db_session)
    r = await client.get(
        "/api/v1/admin/catalogos/color_favorito", headers=auth["_authz"]
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "CATALOGO_DESCONOCIDO"


@pytest.mark.asyncio
async def test_us286_un_tipo_nuevo_queda_disponible_para_un_proyecto(
    client, db_session
):
    """TC-001: el recorrido completo, que es lo que el owner pidió."""
    auth, pm_id, org_id = await _setup(client, db_session)

    r = await client.post(
        "/api/v1/admin/catalogos/tipo_proyecto",
        json={"etiqueta": "Mantenimiento evolutivo"},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["clave"] == "mantenimiento_evolutivo"

    creado = await _crear_proyecto(
        client, auth, org_id, pm_id, type="mantenimiento_evolutivo"
    )
    assert creado.status_code == 201, creado.text
    assert creado.json()["type"] == "mantenimiento_evolutivo"


@pytest.mark.asyncio
async def test_us286_un_tipo_que_no_esta_en_el_catalogo_se_rechaza(
    client, db_session
):
    """La regla de US-202 no desapareció: cambió de sitio."""
    auth, pm_id, org_id = await _setup(client, db_session)

    r = await _crear_proyecto(client, auth, org_id, pm_id, type="Mejora continua")
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "VALOR_FUERA_DE_CATALOGO"


@pytest.mark.asyncio
async def test_us286_el_catalogo_de_un_inquilino_no_vale_en_el_otro(
    client, db_session
):
    """Lo que hace que el catálogo sea del inquilino y no de la plataforma."""
    auth_a, pm_a, org_a = await _setup(client, db_session, slug="acme")
    r = await client.post(
        "/api/v1/admin/catalogos/tipo_proyecto",
        json={"etiqueta": "Mantenimiento"},
        headers=auth_a["_authz"],
    )
    assert r.status_code == 201, r.text

    auth_b, pm_b, org_b = await _setup(client, db_session, slug="globex")
    en_a = await _crear_proyecto(client, auth_a, org_a, pm_a, type="mantenimiento")
    assert en_a.status_code == 201, en_a.text
    en_b = await _crear_proyecto(client, auth_b, org_b, pm_b, type="mantenimiento")
    assert en_b.status_code == 422, en_b.text


@pytest.mark.asyncio
async def test_us286_reordenar_cambia_el_orden_del_listado(client, db_session):
    """TC-002."""
    auth, _pm, _org = await _setup(client, db_session)
    al_reves = ["bau", "innovacion", "operacion", "transformacion"]

    r = await client.put(
        "/api/v1/admin/catalogos/tipo_proyecto/orden",
        json={"claves": al_reves},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert [v["clave"] for v in r.json()] == al_reves

    listado = await client.get(
        "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
    )
    assert [v["clave"] for v in listado.json()] == al_reves


@pytest.mark.asyncio
async def test_us286_reordenar_con_la_lista_incompleta_se_rechaza(client, db_session):
    auth, _pm, _org = await _setup(client, db_session)
    r = await client.put(
        "/api/v1/admin/catalogos/tipo_proyecto/orden",
        json={"claves": ["bau"]},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
    assert "Faltan" in r.json()["detail"]["detail"]


@pytest.mark.asyncio
async def test_us286_un_proyecto_con_el_tipo_desactivado_se_sigue_leyendo(
    client, db_session
):
    """TC-003: desactivar no borra, y lo que ya se guardó sigue valiendo."""
    auth, pm_id, org_id = await _setup(client, db_session)
    proyecto = await _crear_proyecto(client, auth, org_id, pm_id, type="bau")
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]

    valores = (
        await client.get(
            "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
        )
    ).json()
    bau = next(v for v in valores if v["clave"] == "bau")
    r = await client.patch(
        f"/api/v1/admin/catalogos/tipo_proyecto/{bau['id']}",
        json={"activo": False},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is False

    leido = await client.get(
        f"/api/v1/projects/{proyecto_id}", headers=auth["_authz"]
    )
    assert leido.status_code == 200, leido.text
    assert leido.json()["type"] == "bau"

    # Y ya no se puede asignar a uno nuevo: desactivado es «no lo ofrezcas más».
    nuevo = await _crear_proyecto(client, auth, org_id, pm_id, type="bau")
    assert nuevo.status_code == 422, nuevo.text


@pytest.mark.asyncio
async def test_us286_editar_cambia_la_etiqueta_y_no_la_clave(client, db_session):
    auth, _pm, _org = await _setup(client, db_session)
    valores = (
        await client.get(
            "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
        )
    ).json()
    bau = next(v for v in valores if v["clave"] == "bau")

    r = await client.patch(
        f"/api/v1/admin/catalogos/tipo_proyecto/{bau['id']}",
        json={"etiqueta": "Mantener las luces encendidas"},
        headers=auth["_authz"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["etiqueta"] == "Mantener las luces encendidas"
    assert r.json()["clave"] == "bau"


@pytest.mark.asyncio
async def test_us286_todavia_no_se_agregan_fases_y_lo_dice(client, db_session):
    """Una fase nueva no tendría transiciones ni contaría en los KPIs.

    Aceptarla a medias la dejaría atrapada al usarla, y el síntoma no apuntaría
    a la causa. Llega en US-289 con su grafo.
    """
    auth, _pm, _org = await _setup(client, db_session)
    r = await client.post(
        "/api/v1/admin/catalogos/fase_proyecto",
        json={"etiqueta": "Abandonado"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "FASE_NUEVA_NO_DISPONIBLE"
    assert "US-289" in r.json()["detail"]["detail"]


@pytest.mark.asyncio
async def test_us286_una_fase_desactivada_no_se_puede_asignar(client, db_session):
    """El grafo de transiciones dice si el salto es legítimo; el catálogo, si la
    fase sigue existiendo para este inquilino. Son dos preguntas."""
    auth, pm_id, org_id = await _setup(client, db_session)
    proyecto = await _crear_proyecto(client, auth, org_id, pm_id)
    assert proyecto.status_code == 201, proyecto.text
    proyecto_id = proyecto.json()["id"]

    fases = (
        await client.get(
            "/api/v1/admin/catalogos/fase_proyecto", headers=auth["_authz"]
        )
    ).json()
    cancelado = next(v for v in fases if v["clave"] == "cancelado")
    await client.patch(
        f"/api/v1/admin/catalogos/fase_proyecto/{cancelado['id']}",
        json={"activo": False},
        headers=auth["_authz"],
    )

    r = await client.post(
        f"/api/v1/projects/{proyecto_id}/phase/change",
        json={"new_phase": "cancelado"},
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "VALOR_FUERA_DE_CATALOGO"


@pytest.mark.asyncio
async def test_us286_un_usuario_sin_capability_no_toca_el_catalogo(
    client, db_session
):
    """`tenant.manage`: configurar el vocabulario del inquilino es de admin."""
    tenant = await create_tenant(db_session)
    await create_user(
        db_session,
        tenant=tenant,
        username="plain",
        email="plain@acme.example.com",
        password="Str0ng-Plain-1!",
    )
    auth = await login(client, "plain", "Str0ng-Plain-1!")

    r = await client.post(
        "/api/v1/admin/catalogos/tipo_proyecto",
        json={"etiqueta": "Mantenimiento"},
        headers=auth["_authz"],
    )
    assert r.status_code in (401, 403), r.text
