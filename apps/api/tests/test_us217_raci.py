"""US-217 — RACI y stakeholders clave del proyecto.

El artboard «Proyecto — Recursos» pide «RACI / stakeholders clave». Su valor no
está en las cuatro letras: está en que **una sola persona sea la A** de cada
cosa. Un proyecto con dos «responsables últimos» no tiene ninguno.

Lo que estos tests cuidan:

1. **La A es única y las otras tres no.** La R se puede repartir —varias personas
   hacen partes de lo mismo—; la A no.
2. **Nulo es un estado válido.** La mayoría de las participaciones no tienen
   papel, y forzar uno obligaría a inventarlo para poder guardarlas.
3. **Se puede quitar la A.** Rechazar «dejar el proyecto sin A» impediría
   corregir una puesta a la persona equivocada.
4. **El error nombra a quién la tiene.** «Ana ya es la A» es accionable; «ya hay
   una A» obliga a ir a buscarla, que es el paso que hace que alguien deje el
   RACI a medias.
"""
import pytest

from app.dominio.raci import (
    DESCRIPCIONES,
    PAPELES,
    UNICO,
    conflicto_de_unicidad,
    es_papel,
)
from tests.factories import create_admin_role, create_tenant, create_user, login

# ---------------------------------------------------------------------------
# TC-217.1 — La regla, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_las_cuatro_letras_y_solo_esas():
    assert PAPELES == ("A", "R", "C", "I")
    for p in PAPELES:
        assert es_papel(p)
    for basura in ("a", "X", "", None, "AR"):
        assert not es_papel(basura)


def test_cada_papel_se_explica():
    """«A» y «R» se confunden en cada conversación: las dos palabras españolas
    empiezan por «responsable». Sin la descripción, la interfaz no desambigua."""
    for p in PAPELES:
        assert DESCRIPCIONES[p]
        assert len(DESCRIPCIONES[p]) > 20, p


def test_solo_la_a_es_unica():
    assert UNICO == "A"
    actuales = {"p1": "R", "p2": "R", "p3": "C", "p4": "I"}
    # Repartir R, C o I no es conflicto por definición.
    for papel in ("R", "C", "I"):
        assert conflicto_de_unicidad(actuales, participacion="p9", nuevo=papel) is None


def test_una_segunda_a_es_conflicto_y_dice_cual():
    """Se devuelve el identificador y no un booleano porque el mensaje tiene que
    poder decir quién la tiene."""
    actuales = {"p1": "A", "p2": "R"}
    assert conflicto_de_unicidad(actuales, participacion="p9", nuevo="A") == "p1"


def test_poner_la_a_a_quien_ya_la_tiene_es_idempotente():
    actuales = {"p1": "A"}
    assert conflicto_de_unicidad(actuales, participacion="p1", nuevo="A") is None


def test_quitar_la_a_nunca_es_conflicto():
    """Un proyecto sin A es un estado incompleto, no inválido: así está antes de
    que alguien la asigne. Rechazarlo impediría corregir una A mal puesta."""
    actuales = {"p1": "A"}
    assert conflicto_de_unicidad(actuales, participacion="p1", nuevo=None) is None


# ---------------------------------------------------------------------------
# TC-217.2 — Contra la API
# ---------------------------------------------------------------------------


async def _escenario(client, db_session):
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
    h = auth["_authz"]
    org = (
        await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=h)
    ).json()["id"]
    me = (await client.get("/api/v1/auth/me", headers=h)).json()["id"]
    proyecto = (
        await client.post(
            "/api/v1/projects",
            json={
                "name": "ERP",
                "description": "US-217",
                "type": "transformacion",
                "priority": 3,
                "organization_id": org,
                "pm_id": me,
            },
            headers=h,
        )
    ).json()["id"]

    async def actor(nombre: str) -> str:
        r = await client.post(
            "/api/v1/actors", json={"name": nombre}, headers=h
        )
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    return {"h": h, "proyecto": proyecto, "actor": actor}


async def _participar(client, h, proyecto, actor_id, **extra):
    return await client.post(
        f"/api/v1/projects/{proyecto}/participations",
        json={"actor_id": actor_id, **extra},
        headers=h,
    )


@pytest.mark.asyncio
async def test_una_participacion_sin_raci_es_valida(client, db_session):
    """Es el caso normal: la mayoría no tiene papel asignado."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Sin papel")
    r = await _participar(client, e["h"], e["proyecto"], a)
    assert r.status_code == 201, r.text
    assert r.json()["raci"] is None
    assert r.json()["is_key_stakeholder"] is False


@pytest.mark.asyncio
async def test_se_puede_asignar_cada_papel(client, db_session):
    e = await _escenario(client, db_session)
    for papel in ("A", "R", "C", "I"):
        a = await e["actor"](f"Persona {papel}")
        r = await _participar(client, e["h"], e["proyecto"], a, raci=papel)
        assert r.status_code == 201, (papel, r.text)
        assert r.json()["raci"] == papel


@pytest.mark.asyncio
async def test_la_segunda_a_se_rechaza_nombrando_a_la_primera(client, db_session):
    e = await _escenario(client, db_session)
    primera = await e["actor"]("Ana Ruiz")
    r = await _participar(client, e["h"], e["proyecto"], primera, raci="A")
    assert r.status_code == 201, r.text

    segunda = await e["actor"]("Beto Lara")
    r = await _participar(client, e["h"], e["proyecto"], segunda, raci="A")
    assert r.status_code == 400, r.text
    # El mensaje nombra a quién la tiene: es lo que hace la corrección posible.
    assert "Ana Ruiz" in r.text


@pytest.mark.asyncio
async def test_varias_r_se_permiten(client, db_session):
    """Varias personas pueden hacer partes de lo mismo, y eso es normal."""
    e = await _escenario(client, db_session)
    for i in range(3):
        a = await e["actor"](f"Ejecuta {i}")
        r = await _participar(client, e["h"], e["proyecto"], a, raci="R")
        assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_se_puede_mover_la_a_de_una_persona_a_otra(client, db_session):
    """Primero se quita y luego se pone: es el flujo de corregir una A mal
    asignada, y si quitarla estuviera prohibido no habría forma de arreglarlo."""
    e = await _escenario(client, db_session)
    primera = await e["actor"]("Ana Ruiz")
    p1 = (await _participar(client, e["h"], e["proyecto"], primera, raci="A")).json()
    segunda = await e["actor"]("Beto Lara")
    p2 = (await _participar(client, e["h"], e["proyecto"], segunda)).json()

    # Quitar con cadena vacía: `None` no serviría porque `exclude_unset` ya
    # distingue «no lo mandes».
    quitar = await client.patch(
        f"/api/v1/projects/{e['proyecto']}/participations/{p1['id']}",
        json={"raci": ""},
        headers=e["h"],
    )
    assert quitar.status_code == 200, quitar.text
    assert quitar.json()["raci"] is None

    poner = await client.patch(
        f"/api/v1/projects/{e['proyecto']}/participations/{p2['id']}",
        json={"raci": "A"},
        headers=e["h"],
    )
    assert poner.status_code == 200, poner.text
    assert poner.json()["raci"] == "A"


@pytest.mark.asyncio
async def test_el_patch_a_una_segunda_a_se_rechaza(client, db_session):
    e = await _escenario(client, db_session)
    primera = await e["actor"]("Ana Ruiz")
    await _participar(client, e["h"], e["proyecto"], primera, raci="A")
    segunda = await e["actor"]("Beto Lara")
    p2 = (await _participar(client, e["h"], e["proyecto"], segunda, raci="R")).json()

    r = await client.patch(
        f"/api/v1/projects/{e['proyecto']}/participations/{p2['id']}",
        json={"raci": "A"},
        headers=e["h"],
    )
    assert r.status_code == 400, r.text
    assert "Ana Ruiz" in r.text


@pytest.mark.asyncio
async def test_reasignar_la_a_a_la_misma_participacion_no_falla(client, db_session):
    """Idempotente: quien la vuelve a poner quiere que esté, y ya está."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana Ruiz")
    p = (await _participar(client, e["h"], e["proyecto"], a, raci="A")).json()
    r = await client.patch(
        f"/api/v1/projects/{e['proyecto']}/participations/{p['id']}",
        json={"raci": "A"},
        headers=e["h"],
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_un_papel_inventado_se_rechaza_en_la_frontera(client, db_session):
    e = await _escenario(client, db_session)
    a = await e["actor"]("Persona")
    r = await _participar(client, e["h"], e["proyecto"], a, raci="X")
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_el_stakeholder_clave_es_independiente_del_raci(client, db_session):
    """Alguien informado puede ser clave —el director que quiere el correo— y
    alguien que ejecuta puede no serlo."""
    e = await _escenario(client, db_session)
    informado = await e["actor"]("Director")
    r = await _participar(
        client, e["h"], e["proyecto"], informado, raci="I", is_key_stakeholder=True
    )
    assert r.status_code == 201, r.text
    assert r.json()["raci"] == "I"
    assert r.json()["is_key_stakeholder"] is True

    ejecuta = await e["actor"]("Dev")
    r = await _participar(
        client, e["h"], e["proyecto"], ejecuta, raci="R", is_key_stakeholder=False
    )
    assert r.json()["is_key_stakeholder"] is False


@pytest.mark.asyncio
async def test_la_a_es_por_proyecto_y_no_por_inquilino(client, db_session):
    """Cada proyecto tiene su A. Validarlo por inquilino dejaría un solo
    responsable último para toda la cartera, que no es lo que RACI dice."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana Ruiz")
    await _participar(client, e["h"], e["proyecto"], a, raci="A")

    otro = (
        await client.post(
            "/api/v1/projects",
            json={
                "name": "Data Center",
                "description": "US-217",
                "type": "operacion",
                "priority": 2,
                "organization_id": (
                    await client.get("/api/v1/organizations", headers=e["h"])
                ).json()[0]["id"],
                "pm_id": (
                    await client.get("/api/v1/auth/me", headers=e["h"])
                ).json()["id"],
            },
            headers=e["h"],
        )
    ).json()["id"]
    r = await _participar(client, e["h"], otro, a, raci="A")
    assert r.status_code == 201, r.text
