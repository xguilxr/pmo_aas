"""US-274 — vaciar los datos de un inquilino desde el superadmin.

El inventario y su trinquete viven en `test_us274_vaciado_inventario.py`. Esto
prueba el comportamiento: que el preview cuente sin tocar, que la confirmación
por slug frene, y que después del vaciado sobreviva exactamente lo que DEC-045
dice y nada más.
"""
import pytest
from sqlalchemy import func, select

from app.models.area import Actor
from app.models.audit import AuditLog
from app.models.organization import Organization, Portfolio
from app.models.project import Project
from app.models.user import User
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _superadmin(client, db_session):
    await create_user(
        db_session,
        tenant=None,
        username="root",
        email="root@pmoaas.example.com",
        password="Str0ng-Root-1!",
        is_superadmin=True,
    )
    return await login(client, "root", "Str0ng-Root-1!")


async def _inquilino_con_datos(client, db_session, slug: str = "acme"):
    """Un inquilino con organización, portafolio, proyecto y un recurso."""
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
    pf = await client.post(
        f"/api/v1/organizations/{org['id']}/portfolios",
        json={"name": "Portafolio 1"},
        headers=auth["_authz"],
    )
    assert pf.status_code == 201, pf.text
    proyecto = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto 1",
            "description": "US-274",
            "type": "transformacion",
            "priority": 3,
            "organization_id": org["id"],
            "pm_id": me["id"],
        },
        headers=auth["_authz"],
    )
    assert proyecto.status_code == 201, proyecto.text
    actor = await client.post(
        "/api/v1/actors",
        json={"name": "Ana", "organization_id": org["id"]},
        headers=auth["_authz"],
    )
    assert actor.status_code == 201, actor.text
    return tenant, auth


async def _cuantos(db_session, modelo, tenant_id) -> int:
    return int(
        (
            await db_session.execute(
                select(func.count())
                .select_from(modelo)
                .where(modelo.tenant_id == str(tenant_id))
            )
        ).scalar_one()
    )


@pytest.mark.asyncio
async def test_us274_el_preview_cuenta_y_no_borra(client, db_session):
    """TC-001: cuenta lo que hay y deja los datos donde estaban."""
    tenant, _auth = await _inquilino_con_datos(client, db_session)
    root = await _superadmin(client, db_session)

    r = await client.get(
        f"/api/v1/superadmin/tenants/{tenant.id}/wipe/preview",
        headers=root["_authz"],
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    conteo = {fila["tabla"]: fila["filas"] for fila in cuerpo["tablas"]}
    assert conteo["organizations"] == 1
    # Dos: el que creamos y el «Portafolio General» que `services/jerarquia.py`
    # crea al vuelo para un proyecto sin portafolio (DEC-037).
    assert conteo["portfolios"] == 2
    assert conteo["projects"] == 1
    assert conteo["actors"] >= 1
    assert cuerpo["total"] == sum(conteo.values())

    # El inventario entero viaja, ceros incluidos: un preview que solo liste lo
    # que tiene filas se lee como «esto es todo lo que hay».
    assert any(fila["filas"] == 0 for fila in cuerpo["tablas"])
    assert "audit_log" in cuerpo["sobreviven"]

    assert await _cuantos(db_session, Organization, tenant.id) == 1
    assert await _cuantos(db_session, Project, tenant.id) == 1


@pytest.mark.asyncio
async def test_us274_el_slug_equivocado_no_borra_nada(client, db_session):
    """TC-002: la confirmación frena antes de tocar la primera tabla."""
    tenant, _auth = await _inquilino_con_datos(client, db_session)
    root = await _superadmin(client, db_session)

    r = await client.post(
        f"/api/v1/superadmin/tenants/{tenant.id}/wipe?confirm_slug=otro",
        headers=root["_authz"],
    )
    assert r.status_code == 422, r.text

    assert await _cuantos(db_session, Organization, tenant.id) == 1
    assert await _cuantos(db_session, Project, tenant.id) == 1
    assert await _cuantos(db_session, Portfolio, tenant.id) == 2


@pytest.mark.asyncio
async def test_us274_vaciar_deja_al_inquilino_como_recien_aprovisionado(
    client, db_session
):
    """El corazón de DEC-045: se va el contenido, se queda la gente."""
    tenant, _auth = await _inquilino_con_datos(client, db_session)
    root = await _superadmin(client, db_session)

    r = await client.post(
        f"/api/v1/superadmin/tenants/{tenant.id}/wipe?confirm_slug={tenant.slug}",
        headers=root["_authz"],
    )
    assert r.status_code == 200, r.text
    borradas = {fila["tabla"]: fila["filas"] for fila in r.json()["tablas"]}
    assert borradas["organizations"] == 1
    assert borradas["projects"] == 1
    assert borradas["portfolios"] == 2
    assert r.json()["total"] >= 4

    await db_session.rollback()
    assert await _cuantos(db_session, Organization, tenant.id) == 0
    assert await _cuantos(db_session, Project, tenant.id) == 0
    assert await _cuantos(db_session, Portfolio, tenant.id) == 0
    assert await _cuantos(db_session, Actor, tenant.id) == 0

    # US-285: los catálogos se rehacen, porque «recién aprovisionado» los
    # incluye. Un inquilino sin tipos ni fases no puede dar de alta un proyecto.
    from app.models.tenant_catalog import TenantCatalogValue

    assert await _cuantos(db_session, TenantCatalogValue, tenant.id) > 0

    # Sobreviven (DEC-045): el inquilino y su gente.
    assert await _cuantos(db_session, User, tenant.id) >= 1
    vivo = (
        await db_session.execute(
            select(func.count()).select_from(Organization)
        )
    ).scalar_one()
    assert vivo == 0


@pytest.mark.asyncio
async def test_us274_el_segundo_vaciado_solo_encuentra_los_catalogos(
    client, db_session
):
    """Vaciar dos veces no es un error.

    Y no devuelve cero: desde US-285 el vaciado vuelve a sembrar los catálogos
    de proyecto —«como recién aprovisionado» (DEC-045) los incluye— así que el
    segundo pasa se lleva exactamente lo que el primero acababa de crear. Que
    el número no sea cero es el dato correcto: son filas que de verdad se
    borraron.
    """
    tenant, _auth = await _inquilino_con_datos(client, db_session)
    root = await _superadmin(client, db_session)
    url = f"/api/v1/superadmin/tenants/{tenant.id}/wipe?confirm_slug={tenant.slug}"

    assert (await client.post(url, headers=root["_authz"])).status_code == 200
    segundo = await client.post(url, headers=root["_authz"])
    assert segundo.status_code == 200, segundo.text
    con_filas = {
        f["tabla"]: f["filas"] for f in segundo.json()["tablas"] if f["filas"]
    }
    assert set(con_filas) == {"tenant_catalog_values"}


@pytest.mark.asyncio
async def test_us274_no_toca_al_inquilino_de_al_lado(client, db_session):
    """El aislamiento es lo único que no puede fallar aquí."""
    tenant_a, _ = await _inquilino_con_datos(client, db_session, slug="acme")
    tenant_b, _ = await _inquilino_con_datos(client, db_session, slug="globex")
    root = await _superadmin(client, db_session)

    r = await client.post(
        f"/api/v1/superadmin/tenants/{tenant_a.id}/wipe?confirm_slug=acme",
        headers=root["_authz"],
    )
    assert r.status_code == 200, r.text

    await db_session.rollback()
    assert await _cuantos(db_session, Organization, tenant_a.id) == 0
    assert await _cuantos(db_session, Organization, tenant_b.id) == 1
    assert await _cuantos(db_session, Project, tenant_b.id) == 1
    assert await _cuantos(db_session, Actor, tenant_b.id) >= 1


@pytest.mark.asyncio
async def test_us274_la_auditoria_sobrevive_al_vaciado(client, db_session):
    """Se escribe después de borrar, y `audit_log` no está en el inventario.

    Si estuviera, el vaciado borraría su propio rastro —y antes de eso fallaría,
    porque AM-08 rechaza el DELETE en la base.
    """
    tenant, _auth = await _inquilino_con_datos(client, db_session)
    root = await _superadmin(client, db_session)

    r = await client.post(
        f"/api/v1/superadmin/tenants/{tenant.id}/wipe?confirm_slug={tenant.slug}",
        headers=root["_authz"],
    )
    assert r.status_code == 200, r.text

    filas = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == str(tenant.id),
                AuditLog.action == "tenant.wipe",
            )
        )
    ).scalars().all()
    assert len(filas) == 1
    detalles = filas[0].details
    assert detalles["slug"] == tenant.slug
    assert detalles["total"] == r.json()["total"]
    # Solo lo que tenía filas: cuarenta ceros esconden los diez que importan.
    assert all(v > 0 for v in detalles["borradas"].values())
    assert "organizations" in detalles["borradas"]


@pytest.mark.asyncio
async def test_us274_solo_el_superadmin_vacia(client, db_session):
    """Un admin del propio inquilino no puede vaciarlo."""
    tenant, auth = await _inquilino_con_datos(client, db_session)

    r = await client.post(
        f"/api/v1/superadmin/tenants/{tenant.id}/wipe?confirm_slug={tenant.slug}",
        headers=auth["_authz"],
    )
    assert r.status_code in (401, 403), r.text
    assert await _cuantos(db_session, Organization, tenant.id) == 1
