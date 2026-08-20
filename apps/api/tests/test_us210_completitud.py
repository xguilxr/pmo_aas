"""US-210 — Cuánto de un proyecto está capturado, y qué falta.

La columna «Compl.» del artboard «Portafolio — Vista maestra» y el «checklist de
onboarding» de «Onboarding masivo». Son la misma cosa: el porcentaje resume y el
checklist detalla.

Lo que estos tests cuidan es lo que un cálculo de completitud rompe sin ruido:

1. **Un dato ausente y un dato en cero no son lo mismo.** Un presupuesto
   declarado de cero es un proyecto sin costo —dato capturado— y contarlo como
   faltante diría que falta algo que sí está. Es el mismo DAT-12 de siempre, del
   lado del que evalúa.
2. **Una clave que nadie averiguó cuenta como faltante.** Colapsar «no lo tiene»
   y «no lo miré» hacia el lado optimista es cómo un porcentaje acaba diciendo
   100 % de un proyecto vacío.
3. **El denominador se deriva.** Un requisito nuevo tiene que mover el
   porcentaje de todos los proyectos; un total escrito a mano lo dejaría igual.
4. **Los tres requisitos de gobierno son consultas.** Sin ellas el porcentaje
   tiene un techo del 72 % y nadie llega al 100 nunca.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.dominio.completitud import REQUISITOS, TOTAL, evaluar
from app.models.project import Project
from app.services.completitud import completitud_de
from tests.factories import (
    create_admin_role,
    create_portfolio,
    create_tenant,
    create_user,
    login,
)

HOY = date.today()


# ---------------------------------------------------------------------------
# TC-210.1 — La regla, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_todo_presente_es_cien_por_ciento():
    hechos = {r.clave: True for r in REQUISITOS}
    c = evaluar(hechos)
    assert c.pct == 100
    assert c.presentes == TOTAL
    assert c.faltantes == ()
    assert c.completo


def test_nada_presente_es_cero():
    c = evaluar({})
    assert c.pct == 0
    assert c.presentes == 0
    assert len(c.faltantes) == TOTAL
    assert not c.completo


def test_una_clave_ausente_cuenta_como_faltante():
    """«No lo tiene» y «no lo miré» no se colapsan hacia el optimismo.

    Quien no averiguó el dato no puede afirmar que está, y hacerlo es cómo un
    porcentaje acaba diciendo 100 % de un proyecto vacío.
    """
    hechos = {r.clave: True for r in REQUISITOS}
    del hechos["budget"]
    c = evaluar(hechos)
    assert c.pct < 100
    assert [f.clave for f in c.faltantes] == ["budget"]


def test_el_porcentaje_redondea_hacia_abajo():
    """Con diez de once, «90 %» es más honesto que «91 %»: al proyecto le falta
    algo, y el redondeo no puede insinuar que casi no."""
    hechos = {r.clave: True for r in REQUISITOS}
    hechos[REQUISITOS[0].clave] = False
    c = evaluar(hechos)
    esperado = (TOTAL - 1) * 100 // TOTAL
    assert c.pct == esperado
    assert c.pct < 100


def test_el_total_se_deriva_de_la_lista():
    """Un requisito nuevo tiene que mover el porcentaje de todos los proyectos.
    Un total escrito a mano lo dejaría igual (MCA CTX-03)."""
    assert TOTAL == len(REQUISITOS)


def test_cada_faltante_dice_que_se_pierde():
    """Una casilla sin consecuencia se ignora. La consecuencia es lo que hace
    que alguien capture el dato, así que ninguna puede venir vacía."""
    c = evaluar({})
    for f in c.faltantes:
        assert f.etiqueta and f.porque
        assert len(f.porque) > 20, f"«{f.clave}» se explica con una frase hueca"


def test_no_se_piden_los_campos_obligatorios_del_modelo():
    """`name`, `folio` y `phase` son NOT NULL: una casilla que nunca puede
    fallar infla el porcentaje sin decir nada."""
    claves = {r.clave for r in REQUISITOS}
    assert not claves & {"name", "folio", "phase", "organization_id"}


# ---------------------------------------------------------------------------
# TC-210.2 — Los hechos, contra la base
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
    pf = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org, name="Cartera A"
    )
    me = (await client.get("/api/v1/auth/me", headers=h)).json()["id"]
    return {"tenant": t, "h": h, "org": org, "pf": pf, "me": me}


def _proyecto(e, nombre, folio, **campos):
    base = {
        "tenant_id": e["tenant"].id,
        "organization_id": e["org"],
        "folio": folio,
        "name": nombre,
        "phase": "ejecucion",
    }
    base.update(campos)
    return Project(**base)


@pytest.mark.asyncio
async def test_un_proyecto_pelado_solo_tiene_lo_obligatorio(client, db_session):
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Pelado", "SEED-2026-001")
    db_session.add(p)
    await db_session.commit()

    c = (await completitud_de(db_session, [p]))[str(p.id)]
    assert c.pct == 0
    assert len(c.faltantes) == TOTAL


@pytest.mark.asyncio
async def test_presupuesto_cero_es_un_dato_capturado(client, db_session):
    """DAT-12 del lado del que evalúa: un proyecto sin costo declarado es un
    dato, y contarlo como faltante dice que falta algo que sí está."""
    e = await _escenario(client, db_session)
    cero = _proyecto(e, "Sin costo", "SEED-2026-001", budget=Decimal("0"))
    nulo = _proyecto(e, "Sin capturar", "SEED-2026-002")
    db_session.add_all([cero, nulo])
    await db_session.commit()

    todas = await completitud_de(db_session, [cero, nulo])
    faltantes_cero = {f.clave for f in todas[str(cero.id)].faltantes}
    faltantes_nulo = {f.clave for f in todas[str(nulo.id)].faltantes}
    assert "budget" not in faltantes_cero
    assert "budget" in faltantes_nulo
    # Y por tanto el de cero está **más** completo que el nulo.
    assert todas[str(cero.id)].pct > todas[str(nulo.id)].pct


@pytest.mark.asyncio
async def test_un_sponsor_de_espacios_no_cuenta(client, db_session):
    """Texto libre: «capturado con nada» no es capturado."""
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Espacios", "SEED-2026-001", sponsor="   ")
    db_session.add(p)
    await db_session.commit()

    c = (await completitud_de(db_session, [p]))[str(p.id)]
    assert "sponsor" in {f.clave for f in c.faltantes}


@pytest.mark.asyncio
async def test_los_campos_del_registro_cuentan(client, db_session):
    e = await _escenario(client, db_session)
    p = _proyecto(
        e,
        "Casi",
        "SEED-2026-001",
        type="transformacion",
        priority=2,
        portfolio_id=str(e["pf"].id),
        pm_id=e["me"],
        sponsor="Dir. TI",
        start_date=HOY,
        end_date=HOY + timedelta(days=90),
        budget=Decimal("100000"),
    )
    db_session.add(p)
    await db_session.commit()

    c = (await completitud_de(db_session, [p]))[str(p.id)]
    # Los ocho del registro están; faltan los tres de gobierno.
    assert {f.clave for f in c.faltantes} == {"charter", "plan", "recursos"}
    assert c.presentes == TOTAL - 3


@pytest.mark.asyncio
async def test_el_acta_y_el_plan_se_consultan(client, db_session):
    """Sin las consultas de gobierno el porcentaje tiene techo y nadie llega
    nunca al 100."""
    from app.models.project_charter import ProjectCharter
    from app.models.task import Task

    e = await _escenario(client, db_session)
    p = _proyecto(
        e,
        "Con gobierno",
        "SEED-2026-001",
        type="transformacion",
        priority=2,
        portfolio_id=str(e["pf"].id),
        pm_id=e["me"],
        sponsor="Dir. TI",
        start_date=HOY,
        end_date=HOY + timedelta(days=90),
        budget=Decimal("100000"),
    )
    db_session.add(p)
    await db_session.flush()
    db_session.add(
        ProjectCharter(
            tenant_id=e["tenant"].id, project_id=str(p.id), project_name=p.name
        )
    )
    db_session.add(
        Task(
            tenant_id=e["tenant"].id,
            project_id=str(p.id),
            wbs_code="1",
            name="Arranque",
        )
    )
    await db_session.commit()

    c = (await completitud_de(db_session, [p]))[str(p.id)]
    faltantes = {f.clave for f in c.faltantes}
    assert "charter" not in faltantes
    assert "plan" not in faltantes
    # Solo queda «recursos»: la única superficie que no se sembró.
    assert faltantes == {"recursos"}


@pytest.mark.asyncio
async def test_el_acta_de_otro_proyecto_no_cuenta(client, db_session):
    """Una agrupación mal indexada da un número que existe pero es de otro."""
    from app.models.project_charter import ProjectCharter

    e = await _escenario(client, db_session)
    con = _proyecto(e, "Con acta", "SEED-2026-001")
    sin = _proyecto(e, "Sin acta", "SEED-2026-002")
    db_session.add_all([con, sin])
    await db_session.flush()
    db_session.add(
        ProjectCharter(
            tenant_id=e["tenant"].id, project_id=str(con.id), project_name=con.name
        )
    )
    await db_session.commit()

    todas = await completitud_de(db_session, [con, sin])
    assert "charter" not in {f.clave for f in todas[str(con.id)].faltantes}
    assert "charter" in {f.clave for f in todas[str(sin.id)].faltantes}


@pytest.mark.asyncio
async def test_sin_proyectos_no_consulta_nada(client, db_session):
    """Tres consultas con `IN ()` es trabajo para no encontrar nada."""
    assert await completitud_de(db_session, []) == {}


# ---------------------------------------------------------------------------
# TC-210.3 — Las dos superficies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_vista_maestra_trae_la_completitud(client, db_session):
    e = await _escenario(client, db_session)
    p = _proyecto(
        e,
        "Con datos",
        "SEED-2026-001",
        type="transformacion",
        priority=1,
        portfolio_id=str(e["pf"].id),
        budget=Decimal("50000"),
    )
    db_session.add(p)
    await db_session.commit()

    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=e["h"])
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json() if f["name"] == "Con datos")
    assert fila["completeness"]["total"] == TOTAL
    assert fila["completeness"]["presentes"] == 4
    # El detalle viaja con la fila: el checklist se abre sin ir al servidor.
    assert fila["completeness"]["faltantes"]
    assert all(f["porque"] for f in fila["completeness"]["faltantes"])


@pytest.mark.asyncio
async def test_el_endpoint_del_proyecto_devuelve_el_checklist(client, db_session):
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Pelado", "SEED-2026-001")
    db_session.add(p)
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{p.id}/completeness", headers=e["h"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["pct"] == 0
    assert len(cuerpo["faltantes"]) == TOTAL
    # Los grupos existen para poder agrupar el checklist: «te falta el
    # calendario» es más accionable que seis casillas sueltas.
    assert {f["grupo"] for f in cuerpo["faltantes"]} >= {
        "identidad",
        "responsables",
        "calendario",
        "dinero",
        "gobierno",
    }


@pytest.mark.asyncio
async def test_un_proyecto_de_otro_inquilino_no_se_consulta(client, db_session):
    e = await _escenario(client, db_session)
    otro = await create_tenant(db_session, slug="otro", name="Otro")
    ajeno = Project(
        tenant_id=otro.id,
        organization_id=e["org"],
        folio="OTRO-001",
        name="Ajeno",
        phase="ejecucion",
    )
    db_session.add(ajeno)
    await db_session.commit()

    r = await client.get(f"/api/v1/projects/{ajeno.id}/completeness", headers=e["h"])
    assert r.status_code in (403, 404)
