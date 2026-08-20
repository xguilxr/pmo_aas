"""US-215 — La tarifa se congela en la asignación, y declara su unidad.

`actors.fte_cost_rate` guarda la tarifa **de hoy**. Si en marzo alguien la sube,
el costo del trabajo de enero cambiaría solo y el gasto acumulado del proyecto se
reescribiría hacia atrás. Es el mismo defecto que la línea base resuelve para las
fechas (US-212): la historia no se mueve.

Lo que estos tests cuidan:

1. **Subir la tarifa del catálogo no cambia el costo de lo ya asignado.** Es el
   defecto entero, en una frase.
2. **Sin unidad de tiempo no hay costo.** «Tarifa de un FTE» puede ser por hora,
   por día o por mes; multiplicar suponiendo una da un número creíble y falso.
3. **Sin tarifa el costo es `None`, no cero.** Un cero se sumaría al total del
   proyecto haciéndolo parecer completo (MCS DAT-12).
4. **Nunca un total único entre monedas.** Dos personas facturadas en monedas
   distintas no tienen un costo total.
5. **El total viene con cuántas asignaciones quedaron sin tarifa.** Un total sin
   ese número miente por omisión.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.dominio.costo import (
    DIAS_LABORABLES_POR_MES,
    HORAS_POR_DIA,
    costo_de_asignacion,
    costo_por_moneda,
    dias_laborables,
    sin_tarifa,
    tarifa_diaria,
)
from tests.factories import create_admin_role, create_tenant, create_user, login

# ---------------------------------------------------------------------------
# TC-215.1 — La regla, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_los_dias_laborables_excluyen_el_fin_de_semana():
    # Lunes 2026-09-07 a domingo 2026-09-13: cinco laborables.
    assert dias_laborables(date(2026, 9, 7), date(2026, 9, 13)) == 5
    # Inclusivas: un solo día laborable es un día de costo, no cero.
    assert dias_laborables(date(2026, 9, 7), date(2026, 9, 7)) == 1
    # Un sábado solo no es ninguno.
    assert dias_laborables(date(2026, 9, 12), date(2026, 9, 12)) == 0
    # Rango invertido no es negativo.
    assert dias_laborables(date(2026, 9, 13), date(2026, 9, 7)) == 0


def test_la_tarifa_se_lleva_a_dia_por_una_sola_frontera():
    assert tarifa_diaria(Decimal(100), "dia") == Decimal(100)
    assert tarifa_diaria(Decimal(2100), "mes") == Decimal(2100) / Decimal(
        DIAS_LABORABLES_POR_MES
    )
    assert tarifa_diaria(Decimal(50), "hora") == Decimal(50) * Decimal(HORAS_POR_DIA)


def test_un_periodo_desconocido_no_cae_en_un_default():
    """Un costo calculado con la unidad equivocada es creíble y falso — la peor
    clase de error que este módulo puede producir."""
    assert tarifa_diaria(Decimal(100), "semana") is None
    assert tarifa_diaria(Decimal(100), "") is None


def test_el_costo_de_una_asignacion_completa():
    # 1.000/día, 50 %, lunes a viernes: 5 × 1.000 × 0,5 = 2.500.
    assert costo_de_asignacion(
        tarifa=Decimal(1000),
        periodo="dia",
        allocation_pct=Decimal(50),
        desde=date(2026, 9, 7),
        hasta=date(2026, 9, 11),
    ) == Decimal("2500.00")


@pytest.mark.parametrize(
    "falta",
    ["tarifa", "periodo", "allocation_pct", "desde", "hasta"],
)
def test_sin_cualquiera_de_los_cinco_datos_el_costo_es_none(falta):
    """`None` y no cero: una asignación sin tarifa no cuesta cero, se desconoce
    su costo, y un cero se sumaría al total haciéndolo parecer completo."""
    argumentos = {
        "tarifa": Decimal(1000),
        "periodo": "dia",
        "allocation_pct": Decimal(50),
        "desde": date(2026, 9, 7),
        "hasta": date(2026, 9, 11),
    }
    argumentos[falta] = None
    assert costo_de_asignacion(**argumentos) is None


def test_no_se_supone_dedicacion_completa():
    """Suponer 100 % cuando no se capturó infla el costo de todo el portafolio."""
    assert (
        costo_de_asignacion(
            tarifa=Decimal(1000),
            periodo="dia",
            allocation_pct=None,
            desde=date(2026, 9, 7),
            hasta=date(2026, 9, 11),
        )
        is None
    )


def test_dos_monedas_no_tienen_un_total():
    pares = [("MXN", Decimal(1000)), ("USD", Decimal(500)), ("MXN", Decimal(200))]
    assert costo_por_moneda(pares) == {"MXN": Decimal(1200), "USD": Decimal(500)}


def test_un_costo_desconocido_no_suma_ni_cuenta_como_cero():
    pares = [("MXN", None), ("MXN", Decimal(300))]
    assert costo_por_moneda(pares) == {"MXN": Decimal(300)}
    # Una moneda cuyos costos son todos desconocidos no aparece.
    assert costo_por_moneda([("EUR", None)]) == {}
    assert sin_tarifa(pares) == 1


def test_una_moneda_invalida_se_descarta_y_no_cae_en_la_default():
    """El costo es derivado; derivarlo con una moneda adivinada lo convierte en
    un dato sin procedencia."""
    assert costo_por_moneda([("XXX", Decimal(100)), (None, Decimal(50))]) == {}


# ---------------------------------------------------------------------------
# TC-215.2 — Contra la API
# ---------------------------------------------------------------------------


async def _escenario(client, db_session, *, moneda=None):
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
    cuerpo = {
        "name": "ERP",
        "description": "US-215",
        "type": "transformacion",
        "priority": 3,
        "organization_id": org,
        "pm_id": me,
    }
    if moneda:
        cuerpo["currency"] = moneda
    proyecto = (
        await client.post("/api/v1/projects", json=cuerpo, headers=h)
    ).json()["id"]

    async def actor(nombre, tarifa=None, periodo=None) -> str:
        cuerpo = {"name": nombre}
        if tarifa is not None:
            cuerpo["fte_cost_rate"] = tarifa
        if periodo is not None:
            cuerpo["cost_rate_period"] = periodo
        r = await client.post("/api/v1/actors", json=cuerpo, headers=h)
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    async def asignar(actor_id, **extra):
        return await client.post(
            f"/api/v1/projects/{proyecto}/participations",
            json={"actor_id": actor_id, **extra},
            headers=h,
        )

    return {"h": h, "proyecto": proyecto, "actor": actor, "asignar": asignar}


@pytest.mark.asyncio
async def test_la_tarifa_se_congela_al_asignar(client, db_session):
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana", tarifa=1000, periodo="dia")
    r = await e["asignar"](
        a, allocation_pct=50, start_date="2026-09-07", end_date="2026-09-11"
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["cost_rate_snapshot"] == 1000.0
    assert d["cost_rate_period"] == "dia"
    assert d["cost_rate_captured_at"]
    assert d["cost_total"] == 2500.0


@pytest.mark.asyncio
async def test_subir_la_tarifa_del_catalogo_no_cambia_lo_ya_asignado(
    client, db_session
):
    """El defecto entero, en un test: sin el congelado, el costo de enero
    cambiaría al subir la tarifa en marzo."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana", tarifa=1000, periodo="dia")
    pid = (
        await e["asignar"](
            a, allocation_pct=100, start_date="2026-09-07", end_date="2026-09-11"
        )
    ).json()["id"]

    subida = await client.patch(
        f"/api/v1/actors/{a}", json={"fte_cost_rate": 3000}, headers=e["h"]
    )
    assert subida.status_code == 200, subida.text

    filas = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/participations", headers=e["h"]
        )
    ).json()
    congelada = next(f for f in filas if f["id"] == pid)
    assert congelada["cost_rate_snapshot"] == 1000.0
    assert congelada["cost_total"] == 5000.0


@pytest.mark.asyncio
async def test_sin_tarifa_en_el_catalogo_se_puede_asignar_igual(client, db_session):
    """Que el actor no tenga tarifa capturada es lo normal y no puede impedir
    ponerlo en un proyecto."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Sin tarifa")
    r = await e["asignar"](
        a, allocation_pct=50, start_date="2026-09-07", end_date="2026-09-11"
    )
    assert r.status_code == 201, r.text
    assert r.json()["cost_rate_snapshot"] is None
    # `None` y no 0.0: el costo se desconoce.
    assert r.json()["cost_total"] is None


@pytest.mark.asyncio
async def test_con_tarifa_pero_sin_unidad_no_se_congela(client, db_session):
    """Congelar un importe sin unidad de tiempo dejaría un número que parece
    utilizable y no lo es."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Tarifa sin unidad", tarifa=1000)
    r = await e["asignar"](
        a, allocation_pct=50, start_date="2026-09-07", end_date="2026-09-11"
    )
    assert r.status_code == 201, r.text
    assert r.json()["cost_rate_snapshot"] is None
    assert r.json()["cost_total"] is None


@pytest.mark.asyncio
async def test_congelar_despues_de_capturar_la_tarifa(client, db_session):
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana")
    pid = (
        await e["asignar"](
            a, allocation_pct=100, start_date="2026-09-07", end_date="2026-09-11"
        )
    ).json()["id"]
    assert (
        await client.patch(
            f"/api/v1/actors/{a}",
            json={"fte_cost_rate": 2100, "cost_rate_period": "mes"},
            headers=e["h"],
        )
    ).status_code == 200

    r = await client.post(
        f"/api/v1/projects/{e['proyecto']}/participations/{pid}/freeze-cost-rate",
        headers=e["h"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["cost_rate_snapshot"] == 2100.0
    assert r.json()["cost_rate_period"] == "mes"
    # 2.100/mes ÷ 21 días = 100/día × 5 días × 100 % = 500.
    assert r.json()["cost_total"] == 500.0


@pytest.mark.asyncio
async def test_congelar_sin_tarifa_en_el_catalogo_falla_y_lo_dice(client, db_session):
    """Aquí sí es un error: alguien pidió explícitamente congelar, y un 200 sin
    haber congelado nada lo dejaría creyendo que ya está."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Sin tarifa")
    pid = (await e["asignar"](a, allocation_pct=50)).json()["id"]
    r = await client.post(
        f"/api/v1/projects/{e['proyecto']}/participations/{pid}/freeze-cost-rate",
        headers=e["h"],
    )
    # `validation_error` es 400 en este repo; el 422 es de `business_rule`. Se
    # usa el mismo que su hermano `_exigir_una_sola_a`, que es otro conflicto de
    # estado en el mismo módulo: dos códigos distintos para el mismo tipo de
    # rechazo obligarían a quien consume la API a aprender la excepción.
    assert r.status_code == 400, r.text
    assert "tarifa" in r.text.lower()


@pytest.mark.asyncio
async def test_la_moneda_congelada_es_la_del_proyecto(client, db_session):
    e = await _escenario(client, db_session, moneda="USD")
    a = await e["actor"]("Ana", tarifa=1000, periodo="dia")
    r = await e["asignar"](
        a, allocation_pct=100, start_date="2026-09-07", end_date="2026-09-11"
    )
    assert r.json()["cost_currency"] == "USD"


@pytest.mark.asyncio
async def test_el_resumen_da_el_total_y_lo_que_falta(client, db_session):
    e = await _escenario(client, db_session)
    con = await e["actor"]("Con tarifa", tarifa=1000, periodo="dia")
    sin = await e["actor"]("Sin tarifa")
    await e["asignar"](
        con, allocation_pct=100, start_date="2026-09-07", end_date="2026-09-11"
    )
    await e["asignar"](
        sin, allocation_pct=100, start_date="2026-09-07", end_date="2026-09-11"
    )

    r = await client.get(
        f"/api/v1/projects/{e['proyecto']}/participations/cost-summary", headers=e["h"]
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["by_currency"] == {"MXN": 5000.0}
    assert d["single_currency"] == "MXN"
    # Tres y no dos: crear el proyecto autoasigna al PM, y esa participación
    # también cuenta —tiene un costo real y desconocido—. Que aparezca aquí es
    # correcto: si el PM dedica tiempo al proyecto, su costo es parte del costo.
    assert d["assignments"] == 3
    # El total viene con lo que falta: sin este número miente por omisión. Dos:
    # la persona sin tarifa y el PM autoasignado.
    assert d["without_rate"] == 2


@pytest.mark.asyncio
async def test_una_asignacion_tentativa_no_cuenta_como_gasto(client, db_session):
    """Una tentativa no es un compromiso de gasto. Mismo criterio que el motor de
    saturación de US-183."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana", tarifa=1000, periodo="dia")
    await e["asignar"](
        a,
        allocation_pct=100,
        start_date="2026-09-07",
        end_date="2026-09-11",
        status="tentativa",
    )
    d = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/participations/cost-summary",
            headers=e["h"],
        )
    ).json()
    assert d["by_currency"] == {}
    # Solo queda el PM autoasignado al crear el proyecto; la tentativa no cuenta.
    assert d["assignments"] == 1
    assert d["without_rate"] == 1


@pytest.mark.asyncio
async def test_sin_fechas_no_hay_costo(client, db_session):
    """Una asignación sin plazo cuenta como vigente para la capacidad (US-208) y
    no para el costo: habría que elegir arbitrariamente cuándo termina."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana", tarifa=1000, periodo="dia")
    r = await e["asignar"](a, allocation_pct=100)
    assert r.json()["cost_rate_snapshot"] == 1000.0
    assert r.json()["cost_total"] is None
    d = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/participations/cost-summary",
            headers=e["h"],
        )
    ).json()
    # Dos: esta asignación sin fechas y el PM autoasignado al crear el proyecto.
    assert d["without_rate"] == 2
    assert d["by_currency"] == {}


@pytest.mark.asyncio
async def test_la_tarifa_no_se_puede_dictar_desde_el_cliente(client, db_session):
    """Aceptarla permitiría registrar un costo que no corresponde a ninguna
    tarifa aprobada, y el snapshot dejaría de ser una copia verificable."""
    e = await _escenario(client, db_session)
    a = await e["actor"]("Ana")
    r = await e["asignar"](a, allocation_pct=100, cost_rate_snapshot=99999)
    assert r.status_code == 201, r.text
    assert r.json()["cost_rate_snapshot"] is None
