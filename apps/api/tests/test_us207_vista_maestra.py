"""US-207 — La fila de la vista maestra.

`plan-vs-actual` pasó de seis columnas a las trece del control tower. Lo que
estos tests cuidan es lo que se rompe sin ruido al añadir columnas a una fila:

1. **Los nombres de la jerarquía.** Si se resolvieran fila a fila, la tabla
   funcionaría igual con veintitrés proyectos y tardaría segundos con
   doscientos. El test fija que un proyecto sin portafolio ni programa devuelva
   `null` y no reviente, que es el caso que una consulta por fila con `JOIN`
   implícito se salta.
2. **Los conteos de riesgos e issues.** Un proyecto sin ninguno tiene que
   devolver `0`, no faltar la clave: una tabla que pinta `undefined` como vacío
   hace indistinguible «cero riesgos» de «no se pudo contar».
3. **El scoping.** La fila lleva ahora datos de tres entidades más, y cada una
   es una oportunidad de filtrar por menos de lo pedido.
"""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.modules import Issue, Risk
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
    """Dos organizaciones para ejercitar la columna que las distingue.

    - OrgA ⊃ Cartera A ⊃ Programa A1 → P1 (2 riesgos, 1 issue)
    - OrgA ⊃ Cartera A ⊃ (sin programa) → P2
    - OrgA ⊃ (sin portafolio) → P3   ← el que rompe un `JOIN` implícito
    - OrgB → P4
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
    org_a = (
        await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=h)
    ).json()["id"]
    org_b = (
        await client.post("/api/v1/organizations", json={"name": "OrgB"}, headers=h)
    ).json()["id"]

    pf_a = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org_a, name="Cartera A"
    )
    prog_a1 = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org_a,
        name="Programa A1",
        portfolio_id=str(pf_a.id),
    )

    especificaciones = [
        ("P1", org_a, str(pf_a.id), str(prog_a1.id), 3, "transformacion", "red"),
        ("P2", org_a, str(pf_a.id), None, 1, "operacion", "yellow"),
        ("P3", org_a, None, None, 5, "innovacion", "green"),
        ("P4", org_b, None, None, 2, "bau", "green"),
    ]
    proyectos: dict[str, Project] = {}
    for i, (nombre, org, pfid, pgid, prio, tipo, salud) in enumerate(especificaciones):
        p = Project(
            tenant_id=t.id,
            organization_id=org,
            portfolio_id=pfid,
            program_id=pgid,
            folio=f"SEED-2026-{i + 1:03d}",
            name=nombre,
            phase="ejecucion",
            health_status=salud,
            priority=prio,
            type=tipo,
            budget=Decimal("100000"),
            actual_budget=Decimal("40000"),
            progress=30,
            start_date=HOY - timedelta(days=10),
            end_date=HOY + timedelta(days=90),
        )
        db_session.add(p)
        proyectos[nombre] = p
    await db_session.flush()

    # Dos riesgos abiertos y uno resuelto en P1 (el resuelto no cuenta), y un
    # issue abierto. P2, P3 y P4 se quedan en cero a propósito.
    for i, estado in enumerate(["open", "on_hold", "resolved"]):
        db_session.add(
            Risk(
                tenant_id=t.id,
                project_id=str(proyectos["P1"].id),
                folio=f"RSK-2026-{i + 1:03d}",
                title=f"Riesgo {i + 1}",
                status=estado,
                probability=3,
                impact=3,
                severity=9,
            )
        )
    db_session.add(
        Issue(
            tenant_id=t.id,
            project_id=str(proyectos["P1"].id),
            folio="ISS-2026-001",
            title="Issue abierto",
            status="open",
            # `type` y `reported_at` son NOT NULL en el modelo: un AID es una
            # acción, un issue o una decisión, y siempre se reportó un día.
            type="issue",
            reported_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    return {
        "tenant": t,
        "h": h,
        "org_a": org_a,
        "org_b": org_b,
        "pf_a": pf_a,
        "prog_a1": prog_a1,
        "proyectos": proyectos,
    }


def _por_nombre(filas):
    return {f["name"]: f for f in filas}


# ---------------------------------------------------------------------------
# TC-207.1 — Las columnas de la jerarquía, incluidos los huecos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_fila_lleva_los_nombres_de_la_jerarquia(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=e["h"])
    assert r.status_code == 200, r.text
    filas = _por_nombre(r.json())

    assert filas["P1"]["organization_name"] == "OrgA"
    assert filas["P1"]["portfolio_name"] == "Cartera A"
    assert filas["P1"]["program_name"] == "Programa A1"

    # P2 cuelga del portafolio sin programa (DEC-030): portafolio sí, programa
    # `null`. La tabla lo rotula «—»; el contrato no inventa una etiqueta.
    assert filas["P2"]["portfolio_name"] == "Cartera A"
    assert filas["P2"]["program_name"] is None

    # P3 no tiene ninguno de los dos. Es el caso que un `JOIN` implícito se
    # come: no falla, hace desaparecer la fila.
    assert filas["P3"]["portfolio_name"] is None
    assert filas["P3"]["program_name"] is None
    assert filas["P3"]["organization_name"] == "OrgA"

    # Y las cuatro filas están: ninguna se perdió por no tener jerarquía.
    assert set(filas) == {"P1", "P2", "P3", "P4"}


@pytest.mark.asyncio
async def test_organizaciones_distintas_se_distinguen(client, db_session):
    """La columna existe para esto: sin ella, filas de dos organizaciones son
    indistinguibles cuando el header está en «todas» (US-205)."""
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=e["h"])
    filas = _por_nombre(r.json())
    assert filas["P4"]["organization_name"] == "OrgB"
    assert filas["P1"]["organization_name"] == "OrgA"


# ---------------------------------------------------------------------------
# TC-207.2 — Riesgos e issues abiertos por proyecto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conteos_de_riesgos_e_issues(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=e["h"])
    filas = _por_nombre(r.json())

    # `open` y `on_hold` cuentan; `resolved` no (US-179).
    assert filas["P1"]["open_risks"] == 2
    assert filas["P1"]["open_issues"] == 1

    # Cero es **cero**, no una clave ausente: una tabla que pinta `undefined`
    # como vacío hace indistinguible «sin riesgos» de «no se pudo contar».
    for nombre in ("P2", "P3", "P4"):
        assert filas[nombre]["open_risks"] == 0
        assert filas[nombre]["open_issues"] == 0


# ---------------------------------------------------------------------------
# TC-207.3 — Las demás columnas del mockup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tipo_fase_prioridad_y_fuente_de_salud(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=e["h"])
    filas = _por_nombre(r.json())

    assert filas["P1"]["type"] == "transformacion"
    assert filas["P1"]["phase"] == "ejecucion"
    assert filas["P1"]["priority"] == 3
    assert filas["P3"]["priority"] == 5
    # La columna de salud es clicable y abre el desglose: hay que saber si el
    # color lo puso la regla o una persona (US-180/US-191).
    assert filas["P1"]["health_source"] in {"auto", "manual"}
    # «Últ. act.» es cuándo cambió el registro. Existe siempre: la columna del
    # mockup no puede quedarse en blanco en una fila recién creada.
    assert filas["P1"]["updated_at"]


# ---------------------------------------------------------------------------
# TC-207.4 — El scoping de las columnas nuevas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_filtro_de_organizacion_recorta_las_filas(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual?organization_id={e['org_b']}",
        headers=e["h"],
    )
    assert [f["name"] for f in r.json()] == ["P4"]


@pytest.mark.asyncio
async def test_el_filtro_de_portafolio_incluye_los_sin_programa(client, db_session):
    """Cartera A son P1 (por su programa) y P2 (directo). P3 no, aunque sea de
    la misma organización: es la regla de TC-201.1, y la fila nueva no la
    cambia."""
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual?portfolio_id={e['pf_a'].id}",
        headers=e["h"],
    )
    assert sorted(f["name"] for f in r.json()) == ["P1", "P2"]


@pytest.mark.asyncio
async def test_los_conteos_no_se_cuelan_de_otro_proyecto(client, db_session):
    """Filtrando a un portafolio, los riesgos de P1 no pueden aparecer en P2.

    Es el fallo de una agrupación que se calcula sobre todo el inquilino y se
    indexa por proyecto: el número existe, pero es de otro.
    """
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/dashboard/plan-vs-actual?portfolio_id={e['pf_a'].id}",
        headers=e["h"],
    )
    filas = _por_nombre(r.json())
    assert filas["P1"]["open_risks"] == 2
    assert filas["P2"]["open_risks"] == 0
