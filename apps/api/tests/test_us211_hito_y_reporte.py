"""US-211 — «Próx. hito» y «Reporte» como datos consultables.

Las dos últimas columnas del artboard «Portafolio — Vista maestra», y lo que el
Portfolio Board del artboard «Boards» agrupa.

«¿Está reportado?» es la primera pregunta de una reunión de portafolio y la que
nadie puede contestar mirando la lista de reportes: hay que abrir cada proyecto,
ver la fecha del último y compararla con la cadencia. Veintitrés veces.

Lo que estos tests cuidan:

1. **`sin_reporte` no es `vencido`.** Un proyecto que nunca se reportó no
   incumplió una fecha. Meterlos en el mismo cubo esconde el caso que más hay
   que mirar en un onboarding — y es la mezcla que hace natural un `if ultimo is
   None: return "vencido"`.
2. **La ventana de aviso se deriva de la cadencia.** Un «tres días» fijo es casi
   la mitad de un ciclo semanal: la mitad de los proyectos saldrían «por vencer»
   permanentemente.
3. **El próximo hito vencido no se salta.** Devolver la siguiente fecha futura
   esconde el hito que se incumplió, que es justo el que hay que mirar.
"""
from datetime import UTC, date, datetime, timedelta

import pytest

from app.dominio.reporte import (
    CADENCIA_POR_DEFECTO_DIAS,
    evaluar_reporte,
    proximo_hito,
)
from app.models.project import Project
from app.models.report_history import ReportHistory
from app.models.task import Task
from app.services.estado_de_reporte import estado_de_reporte_de
from app.services.tenant_settings import get_cadencia_de_reporte
from tests.factories import (
    create_admin_role,
    create_tenant,
    create_user,
    login,
)

HOY = date(2026, 8, 20)


# ---------------------------------------------------------------------------
# TC-211.1 — El estatus de reporte, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_sin_reporte_no_es_vencido():
    r = evaluar_reporte(None, hoy=HOY)
    assert r.estado == "sin_reporte"
    assert r.etiqueta == "sin reporte"
    # No venció nada: no hay fecha de vencimiento que inventar ni retraso que
    # contar. «Hoy + cadencia» sería una fecha que nadie acordó.
    assert r.vence is None
    assert r.dias_de_retraso == 0


def test_reportado_hoy_esta_al_dia():
    r = evaluar_reporte(HOY, hoy=HOY, cadencia_dias=14)
    assert r.estado == "al_dia"
    assert r.vence == HOY + timedelta(days=14)
    assert r.dias_de_retraso == 0


def test_un_dia_despues_del_vencimiento_esta_vencido():
    ultimo = HOY - timedelta(days=15)
    r = evaluar_reporte(ultimo, hoy=HOY, cadencia_dias=14)
    assert r.estado == "vencido"
    assert r.dias_de_retraso == 1


def test_el_dia_del_vencimiento_todavia_no_esta_vencido():
    """El límite es «después de», no «en»: el día que vence todavía se puede
    reportar, y marcarlo vencido regaña a quien va a cumplir."""
    ultimo = HOY - timedelta(days=14)
    r = evaluar_reporte(ultimo, hoy=HOY, cadencia_dias=14)
    assert r.estado != "vencido"
    assert r.dias_de_retraso == 0


def test_la_ventana_de_aviso_se_deriva_de_la_cadencia():
    """Un quinto del periodo, no un número fijo.

    Con cadencia 14 la ventana es de 2 días; con cadencia 5, de 1. Un «tres
    días» fijo dejaría a la mitad de un ciclo semanal en «por vencer»
    permanentemente.
    """
    # Bi-semanal: a dos días del vencimiento avisa, a tres todavía no.
    assert evaluar_reporte(HOY - timedelta(days=12), hoy=HOY, cadencia_dias=14).estado == "por_vencer"
    assert evaluar_reporte(HOY - timedelta(days=11), hoy=HOY, cadencia_dias=14).estado == "al_dia"
    # Cadencia corta: la ventana no puede ser cero, o nunca avisaría.
    assert evaluar_reporte(HOY - timedelta(days=4), hoy=HOY, cadencia_dias=5).estado == "por_vencer"


def test_el_retraso_nunca_es_negativo():
    """Reportar antes no adelanta nada, y un negativo se leería así."""
    for dias in range(0, 20):
        r = evaluar_reporte(HOY - timedelta(days=dias), hoy=HOY, cadencia_dias=14)
        assert r.dias_de_retraso >= 0


def test_una_cadencia_de_cero_cae_al_default():
    """Cero días haría que todo esté vencido siempre: no es una configuración,
    es un error de captura."""
    r = evaluar_reporte(HOY, hoy=HOY, cadencia_dias=0)
    assert r.vence == HOY + timedelta(days=CADENCIA_POR_DEFECTO_DIAS)
    assert r.estado == "al_dia"


# ---------------------------------------------------------------------------
# TC-211.2 — El próximo hito
# ---------------------------------------------------------------------------


def test_sin_hitos_no_hay_proximo():
    assert proximo_hito([], hoy=HOY) is None


def test_el_proximo_es_el_mas_cercano():
    h = proximo_hito(
        [("Go-live", HOY + timedelta(days=30)), ("UAT", HOY + timedelta(days=8))],
        hoy=HOY,
    )
    assert h is not None
    assert h.nombre == "UAT"
    assert not h.vencido


def test_un_hito_pasado_se_devuelve_marcado_y_no_se_salta():
    """Saltar a la siguiente fecha futura esconde el hito que se incumplió."""
    h = proximo_hito(
        [("Corte", HOY - timedelta(days=5)), ("Go-live", HOY + timedelta(days=30))],
        hoy=HOY,
    )
    assert h is not None
    assert h.nombre == "Corte"
    assert h.vencido


def test_el_empate_de_fechas_desempata_por_nombre():
    """Dos cargas seguidas tienen que devolver el mismo hito: una columna que
    cambia sola entre dos refrescos parece un dato que se mueve."""
    fecha = HOY + timedelta(days=10)
    for orden in ([("Zeta", fecha), ("Alfa", fecha)], [("Alfa", fecha), ("Zeta", fecha)]):
        h = proximo_hito(orden, hoy=HOY)
        assert h is not None and h.nombre == "Alfa"


# ---------------------------------------------------------------------------
# TC-211.3 — La cadencia del inquilino
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_cadencia_por_defecto_es_bi_semanal(client, db_session):
    t = await create_tenant(db_session)
    assert get_cadencia_de_reporte(t) == CADENCIA_POR_DEFECTO_DIAS == 14


@pytest.mark.asyncio
async def test_la_cadencia_configurada_se_respeta(client, db_session):
    t = await create_tenant(db_session)
    t.settings = {"report_builder": {"cadencia_de_reporte_dias": 7}}
    await db_session.commit()
    assert get_cadencia_de_reporte(t) == 7


@pytest.mark.asyncio
async def test_una_cadencia_basura_cae_al_default(client, db_session):
    t = await create_tenant(db_session)
    for basura in ("siete", None, 0, -3, True):
        t.settings = {"report_builder": {"cadencia_de_reporte_dias": basura}}
        assert get_cadencia_de_reporte(t) == CADENCIA_POR_DEFECTO_DIAS, basura


# ---------------------------------------------------------------------------
# TC-211.4 — En lote, contra la base
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
    return {"tenant": t, "h": h, "org": org}


def _proyecto(e, nombre, folio):
    return Project(
        tenant_id=e["tenant"].id,
        organization_id=e["org"],
        folio=folio,
        name=nombre,
        phase="ejecucion",
    )


@pytest.mark.asyncio
async def test_el_ultimo_reporte_es_el_mas_reciente(client, db_session):
    """Con tres reportes se cuenta desde el último, no desde el primero."""
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Con historia", "SEED-2026-001")
    db_session.add(p)
    await db_session.flush()
    for dias in (40, 20, 3):
        db_session.add(
            ReportHistory(
                tenant_id=e["tenant"].id,
                project_id=str(p.id),
                report_type="status",
                generated_at=datetime.now(UTC) - timedelta(days=dias),
            )
        )
    await db_session.commit()

    estados = await estado_de_reporte_de(
        db_session, [p], cadencia_dias=14, hoy=date.today()
    )
    reporte, _ = estados[str(p.id)]
    # Con el último hace tres días está al día; contando desde el de hace
    # cuarenta estaría vencido por veintiséis.
    assert reporte.estado == "al_dia"


@pytest.mark.asyncio
async def test_un_proyecto_sin_reportes_sale_sin_reporte(client, db_session):
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Nuevo", "SEED-2026-001")
    db_session.add(p)
    await db_session.commit()

    estados = await estado_de_reporte_de(db_session, [p], cadencia_dias=14)
    reporte, hito = estados[str(p.id)]
    assert reporte.estado == "sin_reporte"
    assert hito is None


@pytest.mark.asyncio
async def test_solo_los_hitos_abiertos_y_con_fecha_cuentan(client, db_session):
    """Un hito completado no es «el próximo», y uno sin fecha no puede
    ordenarse contra nada."""
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Con plan", "SEED-2026-001")
    db_session.add(p)
    await db_session.flush()
    hoy = date.today()
    especificaciones = [
        # nombre, es_hito, estado, fecha
        ("Kickoff", True, "completed", hoy + timedelta(days=2)),
        ("Sin fecha", True, "not_started", None),
        ("Tarea normal", False, "not_started", hoy + timedelta(days=3)),
        ("UAT integral", True, "not_started", hoy + timedelta(days=8)),
        ("Go-live", True, "in_progress", hoy + timedelta(days=40)),
    ]
    for i, (nombre, es_hito, estado, fecha) in enumerate(especificaciones):
        db_session.add(
            Task(
                tenant_id=e["tenant"].id,
                project_id=str(p.id),
                wbs_code=str(i + 1),
                name=nombre,
                is_milestone=es_hito,
                status=estado,
                end_date=fecha,
            )
        )
    await db_session.commit()

    estados = await estado_de_reporte_de(db_session, [p], cadencia_dias=14, hoy=hoy)
    _, hito = estados[str(p.id)]
    assert hito is not None
    # «Kickoff» está completado, «Sin fecha» no ordena y «Tarea normal» no es
    # hito: el próximo es UAT.
    assert hito.nombre == "UAT integral"


@pytest.mark.asyncio
async def test_los_hitos_de_un_proyecto_no_se_cuelan_en_otro(client, db_session):
    e = await _escenario(client, db_session)
    con = _proyecto(e, "Con hito", "SEED-2026-001")
    sin = _proyecto(e, "Sin hito", "SEED-2026-002")
    db_session.add_all([con, sin])
    await db_session.flush()
    db_session.add(
        Task(
            tenant_id=e["tenant"].id,
            project_id=str(con.id),
            wbs_code="1",
            name="Hito",
            is_milestone=True,
            status="not_started",
            end_date=date.today() + timedelta(days=5),
        )
    )
    await db_session.commit()

    estados = await estado_de_reporte_de(
        db_session, [con, sin], cadencia_dias=14, hoy=date.today()
    )
    assert estados[str(con.id)][1] is not None
    assert estados[str(sin.id)][1] is None


@pytest.mark.asyncio
async def test_sin_proyectos_no_consulta_nada(client, db_session):
    assert await estado_de_reporte_de(db_session, [], cadencia_dias=14) == {}


# ---------------------------------------------------------------------------
# TC-211.5 — Las dos columnas en la vista maestra
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_vista_maestra_trae_las_dos_columnas(client, db_session):
    e = await _escenario(client, db_session)
    p = _proyecto(e, "Con todo", "SEED-2026-001")
    db_session.add(p)
    await db_session.flush()
    hoy = date.today()
    db_session.add(
        Task(
            tenant_id=e["tenant"].id,
            project_id=str(p.id),
            wbs_code="1",
            name="UAT integral",
            is_milestone=True,
            status="not_started",
            end_date=hoy + timedelta(days=8),
        )
    )
    db_session.add(
        ReportHistory(
            tenant_id=e["tenant"].id,
            project_id=str(p.id),
            report_type="status",
            generated_at=datetime.now(UTC) - timedelta(days=20),
        )
    )
    await db_session.commit()

    r = await client.get("/api/v1/dashboard/plan-vs-actual", headers=e["h"])
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json() if f["name"] == "Con todo")
    # Veinte días sin reportar con cadencia de catorce: vencido por seis.
    assert fila["report_status"] == "vencido"
    assert fila["report_status_label"] == "vencido"
    assert fila["report_days_late"] == 6
    assert fila["report_due_date"]
    assert fila["next_milestone"]["name"] == "UAT integral"
    assert fila["next_milestone"]["overdue"] is False
