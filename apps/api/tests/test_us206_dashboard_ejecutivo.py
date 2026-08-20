"""US-206 — Los números del tablero ejecutivo.

El mockup «Dashboard ejecutivo» pide seis tarjetas, dos listas cortas de
proyectos y cuatro distribuciones. Lo que estos tests cuidan **no** es que los
campos existan: es que digan la verdad en los casos donde la forma natural de
implementarlos miente sin fallar.

Tres de esos casos:

1. Un portafolio con «todas las organizaciones» filtraba el avance pero **no**
   los riesgos, porque el filtro de módulos se aplicaba solo ante
   `organization_id`. La tarjeta de riesgos severos contaba la cartera entera al
   lado de un avance que sí era del portafolio.
2. «Sin responsable» son los **dos** campos vacíos —`owner_id` legacy y
   `owner_actor_id` del catálogo (ENH-079)—. Mirar uno solo cuenta como
   huérfano lo que tiene dueño.
3. «Por programa» con `INNER JOIN` hace desaparecer los proyectos que cuelgan
   del portafolio sin programa (DEC-030). No falla: devuelve un gráfico que
   suma menos que el total y nadie lo nota.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.modules import Risk
from app.models.project import Project
from tests.factories import (
    create_admin_role,
    create_portfolio,
    create_program,
    create_tenant,
    create_user,
    login,
)

HOY = date.today()


async def _escenario(client, db_session):
    """Una organización, dos portafolios y cinco proyectos.

    - Cartera A ⊃ Programa A1 → P1 (atrasado 30 pts), P2
    - Cartera A ⊃ (sin programa) → P3   ← el que el `INNER JOIN` se come
    - Cartera B ⊃ Programa B1 → P4 (con dos riesgos severos, uno huérfano)
    - sin clasificar → P5

    Los presupuestos son potencias de dos para que cualquier subtotal diga sin
    ambigüedad qué proyectos entraron, igual que en `test_us201`.
    """
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
    org_id = (
        await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=h)
    ).json()["id"]

    pf_a = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org_id, name="Cartera A"
    )
    pf_b = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org_id, name="Cartera B"
    )
    prog_a1 = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org_id,
        name="Programa A1",
        portfolio_id=str(pf_a.id),
    )
    prog_b1 = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org_id,
        name="Programa B1",
        portfolio_id=str(pf_b.id),
    )

    # P1 va por la mitad del calendario (plan 50 %) con 20 % de avance real:
    # −30 pts. Fechas simétricas alrededor de hoy para que el plan sea 50 exacto
    # y el test no dependa de en qué día del mes corra.
    especificaciones = [
        # nombre, budget, consumido, portafolio, programa, salud, sponsor, avance, fechas
        ("P1", "100000", "40000", pf_a, prog_a1, "red", "Dir. TI", 20, True),
        ("P2", "200000", "50000", pf_a, prog_a1, "yellow", "Dir. TI", 60, False),
        ("P3", "400000", "0", pf_a, None, "green", "CFO", 80, False),
        ("P4", "800000", "100000", pf_b, prog_b1, "red", "Dir. Operac.", 40, False),
        ("P5", "1600000", "0", None, None, "green", None, 90, False),
    ]
    proyectos: dict[str, Project] = {}
    for i, (nombre, budget, gastado, pf, pg, salud, sponsor, avance, fechado) in enumerate(
        especificaciones
    ):
        p = Project(
            tenant_id=t.id,
            organization_id=org_id,
            portfolio_id=str(pf.id) if pf else None,
            program_id=str(pg.id) if pg else None,
            folio=f"SEED-2026-{i + 1:03d}",
            name=nombre,
            phase="ejecucion",
            health_status=salud,
            sponsor=sponsor,
            budget=Decimal(budget),
            actual_budget=Decimal(gastado),
            progress=avance,
            type="transformacion",
            start_date=HOY - timedelta(days=50) if fechado else None,
            end_date=HOY + timedelta(days=50) if fechado else None,
        )
        db_session.add(p)
        proyectos[nombre] = p
    await db_session.flush()

    # Tres riesgos severos, todos sin responsable: dos en P4 y uno en P1, para
    # que «top en riesgo» tenga un orden que comprobar. El caso «con
    # responsable» lo pone el test que asigna `owner_actor_id`, porque asignarlo
    # aquí lo daría por bueno en todos los demás.
    for i, proyecto in enumerate(["P4", "P4", "P1"]):
        db_session.add(
            Risk(
                tenant_id=t.id,
                project_id=str(proyectos[proyecto].id),
                folio=f"RSK-2026-{i + 1:03d}",
                title=f"Riesgo {i + 1}",
                status="open",
                probability=5,
                impact=4,
                severity=20,
                owner_id=None,
                owner_actor_id=None,
            )
        )
    await db_session.commit()
    return {
        "tenant": t,
        "auth": auth,
        "h": h,
        "org_id": org_id,
        "pf_a": pf_a,
        "pf_b": pf_b,
        "prog_a1": prog_a1,
        "proyectos": proyectos,
    }


# ---------------------------------------------------------------------------
# TC-206.1 — El filtro de portafolio alcanza a los riesgos, no solo al avance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portafolio_sin_organizacion_filtra_los_riesgos(client, db_session):
    """El bug que esta US cierra: `portfolio_id` sin `organization_id`.

    Es exactamente la combinación que produce el switcher del header en «todas
    las organizaciones» con un portafolio elegido — el estado más común del
    tablero ejecutivo, no un caso de borde.
    """
    e = await _escenario(client, db_session)

    # Cartera B tiene los dos riesgos severos de P4; Cartera A, el de P1.
    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={e['pf_b'].id}", headers=e["h"]
    )
    assert r.status_code == 200, r.text
    assert r.json()["severe_risks"] == 2

    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={e['pf_a'].id}", headers=e["h"]
    )
    assert r.json()["severe_risks"] == 1

    # Y sin filtro alguno, los tres. Si el filtro no se aplicara, las tres
    # respuestas dirían 3 y el test de arriba pasaría por accidente.
    r = await client.get("/api/v1/dashboard/kpis", headers=e["h"])
    assert r.json()["severe_risks"] == 3


# ---------------------------------------------------------------------------
# TC-206.2 — Riesgos severos sin responsable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_riesgos_severos_sin_responsable(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/kpis", headers=e["h"])
    body = r.json()
    # Los tres sembrados están sin dueño en los dos campos.
    assert body["severe_risks"] == 3
    assert body["severe_risks_unassigned"] == 3


@pytest.mark.asyncio
async def test_un_riesgo_con_actor_no_cuenta_como_huerfano(client, db_session):
    """`owner_actor_id` cuenta como responsable, igual que `owner_id`.

    ENH-079 dejó los dos campos conviviendo. Una implementación que mire solo
    el legacy contaría este riesgo como sin dueño.
    """
    from sqlalchemy import select

    from app.models.area import Actor

    e = await _escenario(client, db_session)
    actor = Actor(tenant_id=e["tenant"].id, name="R. Cantú", is_active=True)
    db_session.add(actor)
    await db_session.flush()

    riesgo = (
        await db_session.execute(
            select(Risk).where(Risk.project_id == str(e["proyectos"]["P1"].id))
        )
    ).scalars().first()
    riesgo.owner_actor_id = str(actor.id)
    await db_session.commit()

    r = await client.get("/api/v1/dashboard/kpis", headers=e["h"])
    body = r.json()
    assert body["severe_risks"] == 3
    assert body["severe_risks_unassigned"] == 2


# ---------------------------------------------------------------------------
# TC-206.3 — Presupuesto consumido y avance de plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_presupuesto_consumido_por_moneda(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={e['pf_a'].id}", headers=e["h"]
    )
    body = r.json()
    # P1 + P2 + P3 = 700k presupuestado, 90k consumido.
    assert body["budget_total"] == 700000.0
    assert sum(body["budget_consumed_by_currency"].values()) == 90000.0


@pytest.mark.asyncio
async def test_avance_de_plan_solo_cuenta_lo_que_tiene_calendario(client, db_session):
    """P1 es el único con fechas: va a mitad de camino, o sea plan 50 %.

    Los otros cuatro no tienen fechas y `_plan_progress_for` les da 0. El
    promedio de plan del portafolio A —P1, P2, P3— es (50+0+0)/3 ≈ 16.67, y el
    real (20+60+80)/3 ≈ 53.33. Lo que el test fija es que los dos lados
    promedien **el mismo conjunto**: si el plan excluyera a los sin fechas y el
    real no, la resta de la tarjeta compararía dos carteras distintas.
    """
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={e['pf_a'].id}", headers=e["h"]
    )
    body = r.json()
    assert body["plan_progress_avg"] == pytest.approx(50 / 3, abs=0.1)
    assert body["progress_avg"] == pytest.approx(160 / 3, abs=0.1)


@pytest.mark.asyncio
async def test_sin_proyectos_el_avance_es_nulo_no_cero(client, db_session):
    """DAT-09 — «—» y no «0 %». Un portafolio vacío no avanza cero por ciento:
    no tiene avance del que hablar, y pintar 0 % lo hace parecer parado."""
    e = await _escenario(client, db_session)
    vacio = await create_portfolio(
        db_session,
        tenant_id=e["tenant"].id,
        organization_id=e["org_id"],
        name="Cartera vacía",
    )
    await db_session.commit()
    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={vacio.id}", headers=e["h"]
    )
    body = r.json()
    assert body["progress_avg"] is None
    assert body["plan_progress_avg"] is None


# ---------------------------------------------------------------------------
# TC-206.4 — Las distribuciones por programa y por sponsor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_distribucion_por_programa_no_pierde_los_sin_programa(
    client, db_session
):
    """P3 cuelga de Cartera A sin programa. Con `INNER JOIN` desaparece."""
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/charts?portfolio_id={e['pf_a'].id}", headers=e["h"]
    )
    assert r.status_code == 200, r.text
    por_programa = r.json()["projects_by_program"]
    assert por_programa["Programa A1"] == 2
    # La clave vacía es «sin programa»: la pantalla la rotula, el contrato no.
    assert por_programa[""] == 1
    # Y la distribución suma lo mismo que la tarjeta de proyectos activos: es
    # la comprobación que detecta que el gráfico perdió una rebanada.
    assert sum(por_programa.values()) == 3


@pytest.mark.asyncio
async def test_distribucion_por_sponsor(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/charts", headers=e["h"])
    por_sponsor = r.json()["projects_by_sponsor"]
    assert por_sponsor["Dir. TI"] == 2
    assert por_sponsor["CFO"] == 1
    assert por_sponsor["Dir. Operac."] == 1
    assert por_sponsor[""] == 1  # P5 no tiene sponsor
    assert sum(por_sponsor.values()) == 5


# ---------------------------------------------------------------------------
# TC-206.5 — Las dos listas «Top»
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top_en_riesgo_ordena_por_severos(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/tops", headers=e["h"])
    assert r.status_code == 200, r.text
    por_riesgo = r.json()["by_risk"]
    assert [x["name"] for x in por_riesgo] == ["P4", "P1"]
    assert por_riesgo[0]["severe_risks"] == 2
    assert por_riesgo[1]["severe_risks"] == 1
    # Los proyectos sin riesgos severos no aparecen: la lista es de lo que hay
    # que mirar, no un ranking de toda la cartera.
    assert len(por_riesgo) == 2


@pytest.mark.asyncio
async def test_top_con_atraso_excluye_los_sin_calendario(client, db_session):
    """Solo P1 tiene fechas y va −30 pts. Los otros cuatro no tienen calendario.

    Si `_plan_progress_for` devolviera 0 y el endpoint no los excluyera, P5
    saldría como «+90 pts» y P3 como «+80»: adelantados contra un plan que no
    existe. El filtro de `delta_pts < 0` los deja fuera igual, pero el test fija
    que la lista sea exactamente el atrasado real.
    """
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/tops", headers=e["h"])
    por_atraso = r.json()["by_delay"]
    assert [x["name"] for x in por_atraso] == ["P1"]
    assert por_atraso[0]["progress_plan"] == 50
    assert por_atraso[0]["progress_actual"] == 20
    assert por_atraso[0]["delta_pts"] == -30


@pytest.mark.asyncio
async def test_tops_respeta_el_filtro_de_portafolio(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/tops?portfolio_id={e['pf_b'].id}", headers=e["h"]
    )
    body = r.json()
    assert [x["name"] for x in body["by_risk"]] == ["P4"]
    # P1 está en la Cartera A: su atraso no puede aparecer filtrando por B.
    assert body["by_delay"] == []


@pytest.mark.asyncio
async def test_tops_recorta_al_limite_pedido(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/tops?limite=1", headers=e["h"])
    assert [x["name"] for x in r.json()["by_risk"]] == ["P4"]
