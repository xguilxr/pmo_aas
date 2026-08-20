"""US-213 — La tendencia por corte de reporte, y el historial de cortes.

Los mockups piden una «Tendencia bi-semanal» y un «Historial de cortes (snapshot
por periodo)». Las instantáneas se capturan **semanalmente** (US-151) y la PMO
reporta cada dos semanas: hay que enseñar un punto por periodo de reporte, no
uno por captura.

Lo que estos tests cuidan:

1. **Se muestrea al leer, no al capturar.** Bajar la frecuencia del job sería
   irreversible: el día que alguien quiera la evolución semanal de un mes
   concreto —la pregunta normal cuando algo se torció— no habría de dónde
   sacarla.
2. **El corte es el último punto del periodo, no el promedio.** Un corte es una
   foto del estado al cerrar: «al 4 de agosto la cartera iba al 63 %». El
   promedio de dos semanas no es ningún estado real, y presentarlo como el corte
   convierte un dato verificable en uno que nadie puede reproducir.
3. **Los periodos se anclan en hoy.** Anclándolos en el primer punto de la
   serie, añadir un punto viejo al histórico correría todos los límites y la
   serie entera cambiaría de forma sin que nada hubiera pasado en la cartera.
4. **El default es sin muestrear.** Varias superficies consumen `/trends`, y
   cambiarles la forma de la serie por debajo sería cambiarles el gráfico sin
   que lo pidieran.
"""
from datetime import date, timedelta
from itertools import pairwise

import pytest

from app.dominio.cortes import cortes_por_periodo, limites_del_periodo
from app.models.metric_snapshot import MetricSnapshot
from tests.factories import create_admin_role, create_tenant, create_user, login

HOY = date(2026, 8, 20)


def _p(dia: date, valor: int) -> dict:
    return {"snapshot_date": dia, "avg_progress": valor}


def _f(p: dict) -> date:
    return p["snapshot_date"]


# ---------------------------------------------------------------------------
# TC-213.1 — El muestreo, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_el_corte_es_el_ultimo_del_periodo():
    """Tres capturas semanales en un periodo bi-semanal: gana la más reciente."""
    puntos = [
        _p(HOY - timedelta(days=13), 50),
        _p(HOY - timedelta(days=6), 55),
        _p(HOY, 61),
    ]
    salida = cortes_por_periodo(puntos, fecha_de=_f, cadencia_dias=14, hoy=HOY)
    # Los tres caen en el mismo periodo (0-13 días atrás): un solo corte, el de
    # hoy. El promedio daría 55,3, que no es el estado de ningún día.
    assert [p["avg_progress"] for p in salida] == [61]


def test_un_punto_por_periodo_y_en_orden_cronologico():
    puntos = [
        _p(HOY - timedelta(days=28), 30),  # periodo 2
        _p(HOY - timedelta(days=21), 35),  # periodo 1
        _p(HOY - timedelta(days=14), 40),  # periodo 1
        _p(HOY - timedelta(days=7), 50),   # periodo 0
        _p(HOY, 61),                       # periodo 0
    ]
    salida = cortes_por_periodo(puntos, fecha_de=_f, cadencia_dias=14, hoy=HOY)
    # Tres periodos → tres cortes, del más viejo al más nuevo.
    assert [p["avg_progress"] for p in salida] == [30, 40, 61]


def test_los_periodos_se_anclan_en_hoy():
    """Añadir un punto viejo no puede cambiar en qué periodo cae el reciente."""
    recientes = [_p(HOY - timedelta(days=7), 50), _p(HOY, 61)]
    con_viejo = [_p(HOY - timedelta(days=90), 10), *recientes]
    sin = cortes_por_periodo(recientes, fecha_de=_f, cadencia_dias=14, hoy=HOY)
    con = cortes_por_periodo(con_viejo, fecha_de=_f, cadencia_dias=14, hoy=HOY)
    # El corte del periodo actual es el mismo en los dos casos.
    assert sin[-1]["avg_progress"] == con[-1]["avg_progress"] == 61


def test_cadencia_cero_devuelve_la_serie_tal_cual():
    """No muestrear es un resultado válido —lo quiere quien pide resolución
    fina— y no un error que merezca una excepción."""
    puntos = [_p(HOY - timedelta(days=d), d) for d in (14, 7, 0)]
    for cadencia in (0, -1):
        assert cortes_por_periodo(
            puntos, fecha_de=_f, cadencia_dias=cadencia, hoy=HOY
        ) == puntos


def test_una_serie_vacia_no_revienta():
    assert cortes_por_periodo([], fecha_de=_f, cadencia_dias=14, hoy=HOY) == []


def test_los_limites_de_periodo_son_contiguos_y_terminan_hoy():
    """El historial nombra los periodos aunque alguno no tenga instantánea: un
    periodo sin datos es información —el job no corrió— y omitirlo hace que la
    tabla parezca continua cuando tiene un hueco."""
    limites = limites_del_periodo(cadencia_dias=14, hoy=HOY, periodos=3)
    assert len(limites) == 3
    assert limites[-1][1] == HOY
    for (_, fin), (inicio_siguiente, _) in pairwise(limites):
        assert fin + timedelta(days=1) == inicio_siguiente
    # Cada periodo cubre exactamente la cadencia.
    for inicio, fin in limites:
        assert (fin - inicio).days == 13


def test_sin_periodos_no_hay_limites():
    assert limites_del_periodo(cadencia_dias=14, hoy=HOY, periodos=0) == []
    assert limites_del_periodo(cadencia_dias=0, hoy=HOY, periodos=3) == []


# ---------------------------------------------------------------------------
# TC-213.2 — El endpoint
# ---------------------------------------------------------------------------


async def _con_instantaneas(client, db_session, dias: list[int]):
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
    hoy = date.today()
    for i, atras in enumerate(dias):
        db_session.add(
            MetricSnapshot(
                tenant_id=t.id,
                scope_type="tenant",
                scope_id=str(t.id),
                snapshot_date=hoy - timedelta(days=atras),
                avg_progress=10 * (i + 1),
                projects_active=i + 1,
                open_risks=i,
            )
        )
    await db_session.commit()
    return auth["_authz"]


@pytest.mark.asyncio
async def test_sin_cadencia_la_serie_viene_completa(client, db_session):
    """El default no muestrea: varias superficies consumen este endpoint y
    cambiarles la forma de la serie sería cambiarles el gráfico."""
    h = await _con_instantaneas(client, db_session, [21, 14, 7, 0])
    r = await client.get("/api/v1/dashboard/trends?scope=tenant", headers=h)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert len(cuerpo["series"]) == 4
    assert cuerpo["cadencia_dias"] == 0


@pytest.mark.asyncio
async def test_con_cadencia_bi_semanal_queda_un_punto_por_periodo(
    client, db_session
):
    h = await _con_instantaneas(client, db_session, [21, 14, 7, 0])
    r = await client.get(
        "/api/v1/dashboard/trends?scope=tenant&cadencia_dias=14", headers=h
    )
    cuerpo = r.json()
    # 21 y 14 días atrás caen en el periodo 1; 7 y 0, en el periodo 0.
    assert len(cuerpo["series"]) == 2
    assert cuerpo["cadencia_dias"] == 14
    # Y el corte de cada periodo es el más reciente de los suyos: los valores
    # sembrados crecen con la antigüedad invertida, así que son el 2.º y el 4.º.
    assert [p["avg_progress"] for p in cuerpo["series"]] == [20.0, 40.0]


@pytest.mark.asyncio
async def test_cadencia_cero_explicita_no_muestrea(client, db_session):
    h = await _con_instantaneas(client, db_session, [21, 14, 7, 0])
    r = await client.get(
        "/api/v1/dashboard/trends?scope=tenant&cadencia_dias=0", headers=h
    )
    assert len(r.json()["series"]) == 4


@pytest.mark.asyncio
async def test_una_cadencia_absurda_se_rechaza(client, db_session):
    """Un año como cadencia de reporte no es una configuración."""
    h = await _con_instantaneas(client, db_session, [0])
    r = await client.get(
        "/api/v1/dashboard/trends?scope=tenant&cadencia_dias=900", headers=h
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# TC-213.3 — La cadencia viaja con el branding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_branding_trae_la_cadencia(client, db_session):
    """Viaja por ahí por el mismo motivo que la moneda: la necesitan el rótulo
    de la tendencia, el muestreo y el historial, y ninguno debería ir a pedirla
    aparte."""
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
    r = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
    assert r.status_code == 200, r.text
    assert r.json()["reporting_cadence_days"] == 14

    t.settings = {"report_builder": {"cadencia_de_reporte_dias": 7}}
    await db_session.commit()
    r = await client.get("/api/v1/me/tenant-branding", headers=auth["_authz"])
    assert r.json()["reporting_cadence_days"] == 7
