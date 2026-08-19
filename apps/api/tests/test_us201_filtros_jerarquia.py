"""US-201 — La cascada organización → portafolio → programa en el tablero,
las vistas cross y los snapshots.

Lo que estos tests cuidan no es que el parámetro exista, sino que **agregue lo
que debe**: un portafolio suma los proyectos de sus programas *y* los que
cuelgan directo de él. La forma natural de implementarlo —resolver los programas
del portafolio y filtrar por ellos— deja fuera exactamente a los segundos, y el
resultado no falla: devuelve un número más chico. Un KPI equivocado se lee como
un dato.
"""
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


async def _escenario(client, db_session):
    """Una organización, dos portafolios, y proyectos repartidos así:

    - Cartera A ⊃ Programa A1 → P1 (100k), P2 (200k)
    - Cartera A ⊃ (sin programa) → P3 (400k)   ← el caso que se pierde
    - Cartera B ⊃ Programa B1 → P4 (800k)
    - sin clasificar (sin portafolio ni programa) → P5 (1.6M)

    Los importes son potencias de dos para que cualquier subtotal identifique
    sin ambigüedad **qué** proyectos entraron: 300k solo puede ser P1+P2.
    """
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    admin = await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    r = await client.post(
        "/api/v1/organizations", json={"name": "OrgA"}, headers=auth["_authz"]
    )
    org_id = r.json()["id"]

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

    especificaciones = [
        ("P1", Decimal("100000"), str(pf_a.id), str(prog_a1.id), "green"),
        ("P2", Decimal("200000"), str(pf_a.id), str(prog_a1.id), "yellow"),
        ("P3", Decimal("400000"), str(pf_a.id), None, "red"),
        ("P4", Decimal("800000"), str(pf_b.id), str(prog_b1.id), "green"),
        ("P5", Decimal("1600000"), None, None, "green"),
    ]
    proyectos = {}
    for i, (nombre, budget, pfid, pgid, salud) in enumerate(especificaciones):
        p = Project(
            tenant_id=t.id,
            organization_id=org_id,
            portfolio_id=pfid,
            program_id=pgid,
            # Prefijo propio: los folios que reparte `next_folio` empiezan en
            # `PRJ-2026-001`, y sembrar a mano con ese prefijo hace que el
            # primer alta por API choque contra el único de la tabla.
            folio=f"SEED-2026-{i + 1:03d}",
            name=nombre,
            phase="ejecucion",
            health_status=salud,
            budget=budget,
            progress=20,
            type="transformacion",
        )
        db_session.add(p)
        proyectos[nombre] = p
    await db_session.flush()
    await db_session.commit()
    return {
        "tenant": t,
        "admin": admin,
        "auth": auth,
        "org_id": org_id,
        "pf_a": pf_a,
        "pf_b": pf_b,
        "prog_a1": prog_a1,
        "prog_b1": prog_b1,
        "proyectos": proyectos,
    }


# ---------------------------------------------------------------------------
# TC-201.1 — Los KPIs de un portafolio: sus programas **y** sus proyectos directos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kpis_de_portafolio_incluyen_proyectos_sin_programa(client, db_session):
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={e['pf_a'].id}", headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # P1 + P2 (del programa) + P3 (directo del portafolio) = 700k. Con la
    # implementación «por programas del portafolio» saldría 300k.
    assert body["budget_total"] == 700000.0
    assert body["active_projects"] == 3

    # El otro portafolio no se mezcla, y el proyecto sin clasificar no entra en
    # ninguno de los dos.
    r = await client.get(
        f"/api/v1/dashboard/kpis?portfolio_id={e['pf_b'].id}", headers=h
    )
    assert r.json()["budget_total"] == 800000.0

    # Sin filtro: los cinco.
    r = await client.get("/api/v1/dashboard/kpis", headers=h)
    assert r.json()["budget_total"] == 3100000.0
    assert r.json()["active_projects"] == 5


@pytest.mark.asyncio
async def test_kpis_de_portafolio_igual_a_la_suma_de_sus_partes(client, db_session):
    """La propiedad, dicha como propiedad: el total del portafolio es la suma de
    sus programas más sus proyectos directos, calculada por la API misma."""
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    del_programa = (
        await client.get(
            f"/api/v1/dashboard/kpis?program_id={e['prog_a1'].id}", headers=h
        )
    ).json()["budget_total"]
    filas = (
        await client.get(
            f"/api/v1/dashboard/plan-vs-actual?portfolio_id={e['pf_a'].id}", headers=h
        )
    ).json()
    directos = sum(
        f["budget_plan"] for f in filas if f["name"] == "P3"
    )
    del_portafolio = (
        await client.get(
            f"/api/v1/dashboard/kpis?portfolio_id={e['pf_a'].id}", headers=h
        )
    ).json()["budget_total"]

    assert del_portafolio == del_programa + directos


# ---------------------------------------------------------------------------
# TC-201.2 — El filtro de programa queda restringido al portafolio elegido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_programa_de_otro_portafolio_devuelve_vacio(client, db_session):
    """Cruzar Cartera A con un programa de Cartera B no es un error: es un filtro
    que no se cruza. Devuelve vacío, no 422 — quien combina dos filtros ajenos
    está explorando."""
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual"
        f"?portfolio_id={e['pf_a'].id}&program_id={e['prog_b1'].id}",
        headers=h,
    )
    assert r.status_code == 200
    assert r.json() == []

    # La combinación coherente sí trae lo suyo.
    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual"
        f"?portfolio_id={e['pf_a'].id}&program_id={e['prog_a1'].id}",
        headers=h,
    )
    assert sorted(f["name"] for f in r.json()) == ["P1", "P2"]


@pytest.mark.asyncio
async def test_lista_de_programas_recortada_por_portafolio(client, db_session):
    """Lo que alimenta el desplegable: `/programs?portfolio_id=` solo ofrece los
    del portafolio elegido. Es lo que impide construir la combinación vacía de
    arriba desde la interfaz."""
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.get(
        f"/api/v1/programs?organization_id={e['org_id']}"
        f"&portfolio_id={e['pf_a'].id}",
        headers=h,
    )
    assert r.status_code == 200
    assert [p["name"] for p in r.json()] == ["Programa A1"]


# ---------------------------------------------------------------------------
# TC-201.3 — El snapshot con scope `portfolio` se captura y se lee en trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_de_portafolio_se_captura_y_se_lee(client, db_session):
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.post("/api/v1/dashboard/snapshots/capture", headers=h)
    assert r.status_code == 200, r.text

    r = await client.get(
        f"/api/v1/dashboard/trends?scope=portfolio&id={e['pf_a'].id}", headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scope"] == "portfolio"
    assert len(body["series"]) == 1
    punto = body["series"][0]
    # Los mismos tres proyectos que en los KPIs, y el mismo importe: si el
    # snapshot y el KPI discrepan, la tendencia dibuja una historia que no
    # cuadra con el número de hoy.
    assert punto["projects_total"] == 3
    assert punto["budget_plan"] == 700000.0


@pytest.mark.asyncio
async def test_scope_portfolio_exige_id(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get(
        "/api/v1/dashboard/trends?scope=portfolio", headers=e["auth"]["_authz"]
    )
    # 400 y no 422: el contrato de `validation_error` de la casa es una regla de
    # negocio con mensaje accionable, no un fallo de esquema de FastAPI.
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# El resto de las superficies del tablero
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_charts_y_heatmap_y_health_matrix_aceptan_la_cascada(client, db_session):
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.get(
        f"/api/v1/dashboard/charts?portfolio_id={e['pf_a'].id}", headers=h
    )
    assert r.status_code == 200, r.text
    charts = r.json()
    assert sum(charts["projects_by_phase"].values()) == 3
    assert charts["portfolio_health"] == {"green": 1, "yellow": 1, "red": 1}
    assert charts["budget_by_type"] == {"transformacion": 700000.0}

    r = await client.get(
        f"/api/v1/dashboard/heatmap?portfolio_id={e['pf_a'].id}", headers=h
    )
    assert r.status_code == 200, r.text
    filas = r.json()["rows"]
    # Sigue habiendo una fila por organización; la de OrgA cuenta solo los tres.
    org_a = next(f for f in filas if f["org_id"] == str(e["org_id"]))
    assert org_a["total"] == 3

    r = await client.get(
        f"/api/v1/dashboard/health-matrix?program_id={e['prog_a1'].id}", headers=h
    )
    assert r.status_code == 200, r.text
    assert sorted(f["name"] for f in r.json()["rows"]) == ["P1", "P2"]


@pytest.mark.asyncio
async def test_treemap_anida_el_portafolio_como_nivel_propio(client, db_session):
    """El proyecto directo del portafolio no puede caer en la misma bolsa que el
    que no está clasificado en nada: son dos situaciones distintas."""
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.get("/api/v1/dashboard/treemap?scope=tenant", headers=h)
    assert r.status_code == 200, r.text
    arbol = r.json()["tree"]
    assert len(arbol) == 1  # una organización
    carteras = {c["name"]: c for c in arbol[0]["children"]}
    assert set(carteras) == {"Cartera A", "Cartera B", "Sin clasificar"}

    programas_a = {p["name"]: p for p in carteras["Cartera A"]["children"]}
    assert set(programas_a) == {"Programa A1", "Sin programa"}
    assert sorted(p["name"] for p in programas_a["Programa A1"]["children"]) == [
        "P1",
        "P2",
    ]
    # P3 cuelga del portafolio sin programa; P5 no cuelga de nada. Antes de
    # US-201 los dos aparecían bajo el mismo «Sin programa» de la organización.
    assert [p["name"] for p in programas_a["Sin programa"]["children"]] == ["P3"]
    sin_clasificar = carteras["Sin clasificar"]["children"]
    assert [p["name"] for p in sin_clasificar[0]["children"]] == ["P5"]


@pytest.mark.asyncio
async def test_plan_vs_actual_csv_filtra_igual_que_la_pantalla(client, db_session):
    """Un export que filtra distinto de la tabla es un informe que no cuadra."""
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual/export.csv?portfolio_id={e['pf_a'].id}",
        headers=h,
    )
    assert r.status_code == 200, r.text
    cuerpo = r.text
    for nombre in ("P1", "P2", "P3"):
        assert nombre in cuerpo
    for nombre in ("P4", "P5"):
        assert f",{nombre}," not in cuerpo


# ---------------------------------------------------------------------------
# Vistas cross
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vistas_cross_aceptan_filtro_de_portafolio(client, db_session):
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]
    proyectos = e["proyectos"]

    # Un riesgo en un proyecto de cada portafolio, y uno en el sin clasificar.
    for clave, folio in (("P3", "R-A"), ("P4", "R-B"), ("P5", "R-X")):
        db_session.add(
            Risk(
                tenant_id=e["tenant"].id,
                project_id=proyectos[clave].id,
                folio=folio,
                title=folio,
                status="open",
                probability=3,
                impact=3,
                severity=9,
            )
        )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/tenant/risks?portfolio_id={e['pf_a'].id}", headers=h
    )
    assert r.status_code == 200, r.text
    assert [x["folio"] for x in r.json()] == ["R-A"]

    r = await client.get("/api/v1/tenant/risks", headers=h)
    assert sorted(x["folio"] for x in r.json()) == ["R-A", "R-B", "R-X"]


@pytest.mark.asyncio
async def test_aislamiento_entre_inquilinos_en_el_filtro(client, db_session):
    """Un `portfolio_id` de otro inquilino no filtra: devuelve vacío. El scoping
    por `tenant_id` va primero, así que no hay forma de leer al vecino pasando
    su UUID."""
    e = await _escenario(client, db_session)
    otro = await create_tenant(db_session, slug="otro", name="Otro")
    from app.models.organization import Organization

    org_otro = Organization(tenant_id=otro.id, name="OrgOtro", is_active=True)
    db_session.add(org_otro)
    await db_session.flush()
    pf_otro = await create_portfolio(
        db_session,
        tenant_id=otro.id,
        organization_id=str(org_otro.id),
        name="Cartera del vecino",
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual?portfolio_id={pf_otro.id}",
        headers=e["auth"]["_authz"],
    )
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# La invariante de la que depende toda la agregación
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proyecto_creado_solo_con_programa_entra_en_el_filtro(client, db_session):
    """Todo el filtrado por portafolio se apoya en `Project.portfolio_id`, no en
    los programas del portafolio. Es lo correcto —así entran los proyectos
    directos— pero deja la agregación a merced de la invariante de US-198: con
    programa, el portafolio es el del programa.

    Un escritor que ponga `program_id` y se olvide del portafolio no falla: crea
    un proyecto que aparece en el árbol y **desaparece** del filtro. Este test
    entra por el endpoint, que es donde vive la resolución, para que un escritor
    nuevo que la salte lo rompa.
    """
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "P6 solo con programa",
            "organization_id": str(e["org_id"]),
            "program_id": str(e["prog_a1"].id),
            # El alta exige estos cuatro (US-030): nada que ver con la jerarquía,
            # pero sin ellos no se llega a la parte que este test mira.
            "description": "Creado sin portfolio_id a propósito.",
            "type": "transformacion",
            "priority": 3,
            "pm_id": str(e["admin"].id),
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    creado = r.json()
    assert creado["portfolio_id"] == str(e["pf_a"].id)

    filas = (
        await client.get(
            f"/api/v1/dashboard/plan-vs-actual?portfolio_id={e['pf_a'].id}", headers=h
        )
    ).json()
    assert "P6 solo con programa" in [f["name"] for f in filas]


@pytest.mark.asyncio
async def test_mover_el_programa_arrastra_sus_proyectos_al_nuevo_portafolio(
    client, db_session
):
    """La otra mitad de la invariante: si el programa cambia de portafolio, sus
    proyectos van con él. Si no, el KPI del portafolio viejo sigue contándolos y
    el del nuevo no los ve — los dos mal, y sumando más que el total."""
    e = await _escenario(client, db_session)
    h = e["auth"]["_authz"]

    r = await client.patch(
        f"/api/v1/programs/{e['prog_a1'].id}",
        json={"portfolio_id": str(e["pf_b"].id)},
        headers=h,
    )
    assert r.status_code == 200, r.text

    # Cartera A se queda solo con su proyecto directo (P3, 400k).
    a = (
        await client.get(
            f"/api/v1/dashboard/kpis?portfolio_id={e['pf_a'].id}", headers=h
        )
    ).json()
    assert a["budget_total"] == 400000.0
    # Cartera B suma los dos del programa mudado (300k) más el suyo (800k).
    b = (
        await client.get(
            f"/api/v1/dashboard/kpis?portfolio_id={e['pf_b'].id}", headers=h
        )
    ).json()
    assert b["budget_total"] == 1100000.0
