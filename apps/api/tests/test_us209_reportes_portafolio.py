"""US-209 — El reporte de portafolio: el nivel que faltaba entero.

ADR-037 metió el portafolio **entre** la organización y el programa. El reporte
de status existía para inquilino, organización, programa y proyecto, y para el
nivel nuevo no había ninguno: la única forma de mirar una cartera era el reporte
de su organización, que suma las demás.

Lo que estos tests cuidan:

1. **Qué agrega un portafolio.** Sus proyectos son los de sus programas **y** los
   que cuelgan directo de él (DEC-030). La implementación natural —resolver los
   programas del portafolio y filtrar por ellos— deja fuera exactamente a los
   segundos, y no falla: devuelve un total más chico. Es TC-201.1 otra vez, un
   nivel más arriba.
2. **Contra qué se compara.** Un portafolio se compara por programa y una
   organización por portafolio: cada nivel contra el de abajo. Comparar
   programas en el reporte de organización se salta un nivel y mezcla programas
   de carteras distintas en la misma tabla.
3. **El rótulo de la tabla.** Con un `if/else` de dos ramas en la plantilla, el
   nivel nuevo salía etiquetado «por programa». Una tabla mal rotulada se lee
   como el nivel equivocado, que es peor que no tenerla.
"""
from decimal import Decimal

import pytest

from app.models.project import Project
from app.services.reports.scoped_status import build_scope_status_context
from tests.factories import (
    create_admin_role,
    create_portfolio,
    create_program,
    create_tenant,
    create_user,
    login,
)


async def _escenario(client, db_session):
    """Una organización con dos carteras y un proyecto suelto.

    - Cartera A ⊃ Programa A1 → P1 (100k), P2 (200k)
    - Cartera A ⊃ (sin programa) → P3 (400k)   ← el que se pierde
    - Cartera B ⊃ Programa B1 → P4 (800k)
    - sin portafolio → P5 (1.6M)

    Potencias de dos: cualquier subtotal identifica sin ambigüedad qué proyectos
    entraron. 700k solo puede ser P1+P2+P3.
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
    org = (
        await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=h)
    ).json()["id"]

    pf_a = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org, name="Cartera A"
    )
    pf_b = await create_portfolio(
        db_session, tenant_id=t.id, organization_id=org, name="Cartera B"
    )
    prog_a1 = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org,
        name="Programa A1",
        portfolio_id=str(pf_a.id),
    )
    prog_b1 = await create_program(
        db_session,
        tenant_id=t.id,
        organization_id=org,
        name="Programa B1",
        portfolio_id=str(pf_b.id),
    )

    especificaciones = [
        ("P1", "100000", str(pf_a.id), str(prog_a1.id), "green"),
        ("P2", "200000", str(pf_a.id), str(prog_a1.id), "yellow"),
        ("P3", "400000", str(pf_a.id), None, "red"),
        ("P4", "800000", str(pf_b.id), str(prog_b1.id), "green"),
        ("P5", "1600000", None, None, "green"),
    ]
    for i, (nombre, budget, pfid, pgid, salud) in enumerate(especificaciones):
        db_session.add(
            Project(
                tenant_id=t.id,
                organization_id=org,
                portfolio_id=pfid,
                program_id=pgid,
                folio=f"SEED-2026-{i + 1:03d}",
                name=nombre,
                phase="ejecucion",
                health_status=salud,
                budget=Decimal(budget),
                progress=20,
                type="transformacion",
            )
        )
    await db_session.commit()
    return {
        "tenant": t,
        "h": h,
        "org": org,
        "pf_a": pf_a,
        "pf_b": pf_b,
        "prog_a1": prog_a1,
    }


# ---------------------------------------------------------------------------
# TC-209.1 — Qué agrega un portafolio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_portafolio_agrega_sus_programas_y_sus_proyectos_directos(
    client, db_session
):
    e = await _escenario(client, db_session)
    ctx = await build_scope_status_context(
        db_session, e["tenant"].id, "portfolio", e["pf_a"].id
    )
    # P1 + P2 (del programa) + P3 (directo del portafolio) = 700k. Resolviendo
    # por programas del portafolio saldría 300k, y nada fallaría.
    assert ctx["kpis"]["budget_plan"] == 700000.0
    assert ctx["kpis"]["projects_active"] == 3
    assert ctx["scope_label"] == "Cartera A"


@pytest.mark.asyncio
async def test_la_otra_cartera_no_se_mezcla(client, db_session):
    e = await _escenario(client, db_session)
    ctx = await build_scope_status_context(
        db_session, e["tenant"].id, "portfolio", e["pf_b"].id
    )
    assert ctx["kpis"]["budget_plan"] == 800000.0
    assert ctx["kpis"]["projects_active"] == 1


@pytest.mark.asyncio
async def test_el_proyecto_sin_portafolio_no_entra_en_ninguno(client, db_session):
    """P5 (1.6M) no está en ninguna cartera. Si apareciera en alguna, el total
    de esa cartera sería mayor que el real y nadie lo notaría."""
    e = await _escenario(client, db_session)
    a = await build_scope_status_context(
        db_session, e["tenant"].id, "portfolio", e["pf_a"].id
    )
    b = await build_scope_status_context(
        db_session, e["tenant"].id, "portfolio", e["pf_b"].id
    )
    assert a["kpis"]["budget_plan"] + b["kpis"]["budget_plan"] == 1500000.0


@pytest.mark.asyncio
async def test_un_portafolio_de_otro_inquilino_no_existe(client, db_session):
    """El scope se valida contra el inquilino: un identificador de otro no
    devuelve un reporte vacío, devuelve «no existe»."""
    from fastapi import HTTPException

    e = await _escenario(client, db_session)
    otro = await create_tenant(db_session, slug="otro", name="Otro")
    ajena = await create_portfolio(
        db_session, tenant_id=otro.id, organization_id=e["org"], name="Ajena"
    )
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await build_scope_status_context(
            db_session, e["tenant"].id, "portfolio", ajena.id
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# TC-209.2 — Contra qué se compara cada nivel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_portafolio_se_compara_por_programa(client, db_session):
    e = await _escenario(client, db_session)
    ctx = await build_scope_status_context(
        db_session, e["tenant"].id, "portfolio", e["pf_a"].id
    )
    assert ctx["rows_kind"] == "programs"
    assert ctx["heatmap_label"] == "programa"
    nombres = {r["name"] for r in ctx["rows"]}
    # Programa A1 está; el B1 es de la otra cartera y no puede aparecer.
    assert "Programa A1" in nombres
    assert "Programa B1" not in nombres


@pytest.mark.asyncio
async def test_la_organizacion_se_compara_por_portafolio(client, db_session):
    """Cada nivel contra el de abajo. Comparar programas aquí se salta el
    portafolio y mezcla programas de carteras distintas en una tabla."""
    e = await _escenario(client, db_session)
    ctx = await build_scope_status_context(
        db_session, e["tenant"].id, "organization", e["org"]
    )
    assert ctx["rows_kind"] == "portfolios"
    assert ctx["heatmap_label"] == "portafolio"
    nombres = {r["name"] for r in ctx["rows"]}
    assert {"Cartera A", "Cartera B"} <= nombres


@pytest.mark.asyncio
async def test_el_heatmap_del_portafolio_se_pinta(client, db_session):
    """`heatmap_rows` se llenaba solo para organización y programa: el nivel
    nuevo salía sin tabla de salud, que es la mitad del reporte."""
    e = await _escenario(client, db_session)
    ctx = await build_scope_status_context(
        db_session, e["tenant"].id, "portfolio", e["pf_a"].id
    )
    assert ctx["heatmap_rows"], "el portafolio tiene que traer su heatmap"


# ---------------------------------------------------------------------------
# TC-209.3 — El endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_endpoint_devuelve_un_pdf(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.post(
        f"/api/v1/portfolios/{e['pf_a'].id}/reports/status", headers=e["h"]
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "status-portafolio.pdf" in r.headers["content-disposition"]


# Que la ruta exija sesión no se comprueba aquí: `AsyncClient` comparte el
# frasco de cookies, así que un POST «sin sesión» después de `_escenario`
# seguiría autenticado y el test pasaría sin probar nada. La garantía de que
# ninguna ruta queda abierta la da `test_seg06_modelo_amenazas`, sobre todas a
# la vez.
