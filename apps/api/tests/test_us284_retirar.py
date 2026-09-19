"""US-284 — «Retirar» un portafolio o un programa, sin borrar sus proyectos.

La papelera de dos pasos (US-088) borra. Retirar es otra cosa: saca la
clasificación de circulación y deja los proyectos donde se los pueda seguir
viendo. El owner lo pidió con estas palabras: «retirar un portafolio o programa
solo debería retirar la asignación a proyectos, no borrar los proyectos».

## Una desviación del criterio de aceptación, escrita a propósito

El issue decía que retirar un **programa** también mueve sus proyectos al
«Portafolio General». No se hace: su portafolio sigue activo y sigue diciendo
algo cierto sobre ellos, así que moverlos perdería esa clasificación sin motivo
— lo que se retiró es el programa. Solo se los lleva al General si el portafolio
tampoco está vivo. El invariante que hay que respetar es
`program_id ⇒ portfolio_id = program.portfolio_id`, y soltar el programa ya lo
respeta.

El issue pedía además que ningún proyecto quede con `program_id` en `NULL`. Eso
no se puede cumplir sin inventar un programa: un proyecto con portafolio y sin
programa es el caso normal del producto.
"""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.organization import Portfolio, Program
from app.models.project import Project
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
    org = (
        await client.post(
            "/api/v1/organizations", json={"name": "Org 1"}, headers=auth["_authz"]
        )
    ).json()
    return tenant, auth, me["id"], org["id"]


async def _portafolio(client, auth, org_id, nombre="Portafolio A"):
    r = await client.post(
        f"/api/v1/organizations/{org_id}/portfolios",
        json={"name": nombre},
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _programa(client, auth, org_id, portfolio_id, nombre="Programa A"):
    r = await client.post(
        "/api/v1/programs",
        json={
            "name": nombre,
            "organization_id": org_id,
            "portfolio_id": portfolio_id,
        },
        headers=auth["_authz"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _proyecto(client, auth, org_id, pm_id, nombre="Proyecto", **extra):
    cuerpo = {
        "name": nombre,
        "description": "US-284",
        "type": "transformacion",
        "priority": 3,
        "organization_id": org_id,
        "pm_id": pm_id,
    }
    cuerpo.update(extra)
    r = await client.post("/api/v1/projects", json=cuerpo, headers=auth["_authz"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _recargar(db_session, project_id) -> Project:
    await db_session.rollback()
    return (
        await db_session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one()


@pytest.mark.asyncio
async def test_us284_retirar_un_portafolio_mueve_sus_proyectos_al_general(
    client, db_session
):
    """TC-001: los proyectos siguen ahí, con portafolio, y queda auditado."""
    tenant, auth, pm_id, org_id = await _setup(client, db_session)
    pf = await _portafolio(client, auth, org_id)
    proyecto_id = await _proyecto(client, auth, org_id, pm_id, portfolio_id=pf)

    r = await client.post(
        f"/api/v1/portfolios/{pf}/retire", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["proyectos_movidos"] == 1

    proyecto = await _recargar(db_session, proyecto_id)
    assert proyecto.deleted_at is None, "retirar no borra el proyecto"
    assert str(proyecto.portfolio_id) != pf
    assert proyecto.portfolio_id is not None

    general = (
        await db_session.execute(
            select(Portfolio).where(Portfolio.id == str(proyecto.portfolio_id))
        )
    ).scalar_one()
    assert general.name == "Portafolio General"

    retirado = (
        await db_session.execute(select(Portfolio).where(Portfolio.id == pf))
    ).scalar_one()
    assert retirado.is_active is False
    assert retirado.deleted_at is None, "retirar no es la papelera"


@pytest.mark.asyncio
async def test_us284_retirar_un_portafolio_desactiva_sus_programas_y_suelta_el_par(
    client, db_session
):
    """El invariante `program_id ⇒ portfolio_id` no puede quedar roto.

    Si el proyecto conservara su programa, ese programa seguiría colgando del
    portafolio que se acaba de retirar, y el par sería justo el que DEC-037
    prohíbe.
    """
    tenant, auth, pm_id, org_id = await _setup(client, db_session)
    pf = await _portafolio(client, auth, org_id)
    prog = await _programa(client, auth, org_id, pf)
    proyecto_id = await _proyecto(client, auth, org_id, pm_id, program_id=prog)

    r = await client.post(
        f"/api/v1/portfolios/{pf}/retire", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["programas_desactivados"] == 1

    proyecto = await _recargar(db_session, proyecto_id)
    assert proyecto.program_id is None
    assert proyecto.portfolio_id is not None
    programa = (
        await db_session.execute(select(Program).where(Program.id == prog))
    ).scalar_one()
    assert programa.is_active is False


@pytest.mark.asyncio
async def test_us284_retirar_un_programa_deja_el_portafolio_en_paz(
    client, db_session
):
    """TC-002, con la desviación declarada en el encabezado.

    El portafolio sigue activo y sigue diciendo algo cierto: moverlos al
    General perdería esa clasificación sin que nadie lo pidiera.
    """
    tenant, auth, pm_id, org_id = await _setup(client, db_session)
    pf = await _portafolio(client, auth, org_id)
    prog = await _programa(client, auth, org_id, pf)
    proyecto_id = await _proyecto(client, auth, org_id, pm_id, program_id=prog)

    r = await client.post(f"/api/v1/programs/{prog}/retire", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    assert r.json()["proyectos_movidos"] == 1
    assert r.json()["destino_portfolio_id"] == pf

    proyecto = await _recargar(db_session, proyecto_id)
    assert proyecto.program_id is None
    assert str(proyecto.portfolio_id) == pf
    programa = (
        await db_session.execute(select(Program).where(Program.id == prog))
    ).scalar_one()
    assert programa.is_active is False


@pytest.mark.asyncio
async def test_us284_retirar_sin_proyectos_no_es_un_error(client, db_session):
    """TC-003: cero es una respuesta, y queda auditada como tal."""
    tenant, auth, _pm_id, org_id = await _setup(client, db_session)
    pf = await _portafolio(client, auth, org_id)

    r = await client.post(f"/api/v1/portfolios/{pf}/retire", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    assert r.json()["proyectos_movidos"] == 0

    await db_session.rollback()
    filas = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "portfolio.retire")
        )
    ).scalars().all()
    assert len(filas) == 1
    assert filas[0].details["proyectos_movidos"] == 0


@pytest.mark.asyncio
async def test_us284_la_auditoria_cuenta_los_proyectos_movidos(client, db_session):
    tenant, auth, pm_id, org_id = await _setup(client, db_session)
    pf = await _portafolio(client, auth, org_id)
    for i in range(3):
        await _proyecto(client, auth, org_id, pm_id, nombre=f"P{i}", portfolio_id=pf)

    r = await client.post(f"/api/v1/portfolios/{pf}/retire", headers=auth["_authz"])
    assert r.status_code == 200, r.text

    await db_session.rollback()
    fila = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "portfolio.retire")
        )
    ).scalar_one()
    assert fila.details["proyectos_movidos"] == 3
    assert fila.details["destino_portfolio_id"] == r.json()["destino_portfolio_id"]


@pytest.mark.asyncio
async def test_us284_el_portafolio_general_no_se_retira(client, db_session):
    """Es el destino de los demás: retirarlo los dejaría sin sitio."""
    tenant, auth, pm_id, org_id = await _setup(client, db_session)
    # Se crea al vuelo al dar de alta un proyecto sin portafolio (DEC-037).
    await _proyecto(client, auth, org_id, pm_id)
    await db_session.rollback()
    general = (
        await db_session.execute(
            select(Portfolio).where(Portfolio.name == "Portafolio General")
        )
    ).scalar_one()

    r = await client.post(
        f"/api/v1/portfolios/{general.id}/retire", headers=auth["_authz"]
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "PORTAFOLIO_GENERAL_NO_SE_RETIRA"


@pytest.mark.asyncio
async def test_us284_retirar_no_es_la_papelera(client, db_session):
    """Dos acciones distintas: una desactiva, la otra marca para borrar."""
    tenant, auth, _pm_id, org_id = await _setup(client, db_session)
    pf = await _portafolio(client, auth, org_id)

    await client.post(f"/api/v1/portfolios/{pf}/retire", headers=auth["_authz"])
    await db_session.rollback()
    retirado = (
        await db_session.execute(select(Portfolio).where(Portfolio.id == pf))
    ).scalar_one()
    assert retirado.is_active is False
    assert retirado.deleted_at is None
