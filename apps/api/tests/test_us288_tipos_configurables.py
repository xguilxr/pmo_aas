"""US-288 — los tipos de proyecto son del inquilino, sin valores de sistema.

La tabla es US-285 y la API de administración US-286. Lo que se prueba aquí es
la decisión D9 —ningún tipo es intocable— y la lectura sin capability de admin,
que es lo que permite que el formulario de alta de un proyecto los ofrezca.
"""
import pytest

from app.dominio.proyecto import TIPOS
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _admin(client, db_session, slug: str = "acme"):
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
    return tenant, await login(client, f"admin_{slug}", "Str0ng-Admin-1!")


async def _plain(client, db_session, tenant, username: str = "pm"):
    await create_user(
        db_session,
        tenant=tenant,
        username=username,
        email=f"{username}@acme.example.com",
        password="Str0ng-Plain-1!",
    )
    return await login(client, username, "Str0ng-Plain-1!")


@pytest.mark.asyncio
async def test_us288_ningun_tipo_sembrado_es_intocable(client, db_session):
    """D9 — los cuatro de fábrica se editan y se retiran como cualquier otro.

    No hay bandera «de sistema» y no debe haberla: la decisión del owner fue que
    el inquilino manda sobre su propio vocabulario. Lo que la plataforma protege
    es lo que está **en uso**, no lo que vino de fábrica.
    """
    _tenant, auth = await _admin(client, db_session)
    valores = (
        await client.get(
            "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
        )
    ).json()
    assert [v["clave"] for v in valores] == list(TIPOS)
    assert all("es_sistema" not in v for v in valores), (
        "Ningún valor lleva marca de sistema: D9 dice que todos son del inquilino."
    )

    for v in valores:
        r = await client.patch(
            f"/api/v1/admin/catalogos/tipo_proyecto/{v['id']}",
            json={"etiqueta": f"{v['etiqueta']} (nuestro)", "activo": False},
            headers=auth["_authz"],
        )
        assert r.status_code == 200, r.text
        assert r.json()["activo"] is False


@pytest.mark.asyncio
async def test_us288_no_hay_forma_de_borrar_un_tipo(client, db_session):
    """Se desactiva, nunca se borra: borrarlo dejaría proyectos sin referencia.

    No es una validación que se pueda saltar — es que la ruta no existe.
    """
    _tenant, auth = await _admin(client, db_session)
    valores = (
        await client.get(
            "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
        )
    ).json()

    r = await client.delete(
        f"/api/v1/admin/catalogos/tipo_proyecto/{valores[0]['id']}",
        headers=auth["_authz"],
    )
    assert r.status_code in (404, 405), r.text


@pytest.mark.asyncio
async def test_us288_un_pm_lee_el_catalogo_sin_ser_admin(client, db_session):
    """El formulario de alta de proyecto lo abre un PM, no un administrador.

    Leer con qué palabras clasifica tu inquilino no es administrar nada. La ruta
    de administración sí exige `tenant.manage`, y eso no cambia.
    """
    tenant, _auth = await _admin(client, db_session)
    pm = await _plain(client, db_session, tenant)

    r = await client.get("/api/v1/catalogos/tipo_proyecto", headers=pm["_authz"])
    assert r.status_code == 200, r.text
    assert [v["clave"] for v in r.json()] == list(TIPOS)

    negado = await client.get(
        "/api/v1/admin/catalogos/tipo_proyecto", headers=pm["_authz"]
    )
    assert negado.status_code in (401, 403), negado.text


@pytest.mark.asyncio
async def test_us288_la_lectura_incluye_los_retirados_para_poder_nombrarlos(
    client, db_session
):
    """Quien llama ofrece con `activo` y nombra con la lista completa.

    Sin los retirados, un proyecto con un tipo que se dejó de usar se pintaría
    con su clave cruda. Esconder el nombre no cambia el dato: lo hace ilegible.
    """
    tenant, auth = await _admin(client, db_session)
    valores = (
        await client.get(
            "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
        )
    ).json()
    retirado = valores[0]
    await client.patch(
        f"/api/v1/admin/catalogos/tipo_proyecto/{retirado['id']}",
        json={"activo": False},
        headers=auth["_authz"],
    )

    pm = await _plain(client, db_session, tenant)
    leidos = (
        await client.get("/api/v1/catalogos/tipo_proyecto", headers=pm["_authz"])
    ).json()
    por_clave = {v["clave"]: v for v in leidos}
    assert retirado["clave"] in por_clave
    assert por_clave[retirado["clave"]]["activo"] is False
    assert por_clave[retirado["clave"]]["etiqueta"] == retirado["etiqueta"]


@pytest.mark.asyncio
async def test_us288_un_inquilino_puede_quedarse_sin_tipos_activos(
    client, db_session
):
    """Es un estado alcanzable, no un imposible.

    Sin valores de sistema (D9), retirar los cuatro es legítimo. La API no lo
    impide; lo que tiene que pasar es que el alta de proyecto lo **diga** —la
    pantalla pinta el aviso con el enlace al catálogo— en vez de ofrecer un
    desplegable vacío. Aquí se fija que el estado existe y que el alta lo
    rechaza con el motivo, que es la mitad que vive en el servidor.
    """
    _tenant, auth = await _admin(client, db_session)
    me = (await client.get("/api/v1/auth/me", headers=auth["_authz"])).json()
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "Org 1"}, headers=auth["_authz"]
        )
    ).json()

    valores = (
        await client.get(
            "/api/v1/admin/catalogos/tipo_proyecto", headers=auth["_authz"]
        )
    ).json()
    for v in valores:
        await client.patch(
            f"/api/v1/admin/catalogos/tipo_proyecto/{v['id']}",
            json={"activo": False},
            headers=auth["_authz"],
        )

    vigentes = (
        await client.get("/api/v1/catalogos/tipo_proyecto", headers=auth["_authz"])
    ).json()
    assert [v for v in vigentes if v["activo"]] == []

    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto",
            "description": "US-288",
            "type": "transformacion",
            "priority": 3,
            "organization_id": org["id"],
            "pm_id": me["id"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "VALOR_FUERA_DE_CATALOGO"
    assert "Catálogos" in r.json()["detail"]["detail"]


@pytest.mark.asyncio
async def test_us288_un_tipo_nuevo_esta_disponible_de_inmediato(client, db_session):
    """TC-002: sin despliegue, sin reinicio, sin migración."""
    _tenant, auth = await _admin(client, db_session)
    r = await client.post(
        "/api/v1/admin/catalogos/tipo_proyecto",
        json={"etiqueta": "Regulatorio"},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text

    vigentes = (
        await client.get("/api/v1/catalogos/tipo_proyecto", headers=auth["_authz"])
    ).json()
    assert "regulatorio" in [v["clave"] for v in vigentes]
