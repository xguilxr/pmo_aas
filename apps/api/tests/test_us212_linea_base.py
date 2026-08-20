"""US-212 / D-6 — Línea base del plan: contra qué se mide una desviación.

Es la brecha B-1 del diagnóstico. Sin línea base, «desviación», «retraso» y
«sobrecosto» son palabras sin referente: un Gantt que se mueve solo no está
atrasado respecto de nada.

Lo que estos tests cuidan:

1. **Sin línea base, la respuesta es «no hay», no una desviación de cero.** Es la
   diferencia entre «no se desvió» y «no sabemos si se desvió porque nadie
   prometió nada» (MCS DAT-12).
2. **Las capturas se apilan.** Sobrescribir la última borraría la única prueba de
   que la promesa cambió, que es el dato que un comité de cambios pide.
3. **Se emparejan por identificador y no por código EDT.** El plan tiene un botón
   que renumera el EDT; emparejar por código haría que una renumeración —que no
   mueve ninguna fecha— apareciera como el plan entero reemplazado.
4. **Alcance agregado y alcance quitado no son atrasos.** Un proyecto puede tener
   cero tareas corridas y treinta nuevas, y mezclarlo pierde la conversación.
5. **Borrar una tarea no encoge la promesa.** La fila de la foto sobrevive; por
   eso `plan_baseline_tasks.task_id` no lleva clave ajena.
6. **La deriva real no se puede reescribir.** El plan sí: replanificar hace
   desaparecer `slip_days` y no `actual_slip_days`.
"""
from datetime import date

import pytest

from app.dominio.linea_base import Fila, comparar, resumir
from tests.factories import create_admin_role, create_tenant, create_user, login

# ---------------------------------------------------------------------------
# TC-212.1 — La regla, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def _f(tid: str, fin: str | None, **extra) -> Fila:
    return Fila(
        task_id=tid,
        wbs_code=extra.pop("wbs", "1"),
        nombre=extra.pop("nombre", f"T{tid}"),
        inicio=extra.pop("inicio", None),
        fin=date.fromisoformat(fin) if fin else None,
        **extra,
    )


def test_una_tarea_que_no_se_movio_no_tiene_deriva():
    base = [_f("t1", "2026-09-30")]
    plan = [_f("t1", "2026-09-30")]
    (c,) = comparar(base, plan)
    assert c.deriva_dias == 0
    assert c.estado == "sin_cambio"


def test_una_tarea_corrida_y_una_adelantada():
    base = [_f("t1", "2026-09-30"), _f("t2", "2026-09-30")]
    plan = [_f("t1", "2026-10-15"), _f("t2", "2026-09-20")]
    corrida, adelantada = comparar(base, plan)
    assert (corrida.deriva_dias, corrida.estado) == (15, "corrida")
    assert (adelantada.deriva_dias, adelantada.estado) == (-10, "adelantada")


def test_sin_fecha_la_deriva_es_none_y_no_cero():
    """Decir que la deriva es 0 la contaría como «en fecha», que es la lectura
    opuesta a la verdad: no se sabe (MCS DAT-12)."""
    (c,) = comparar([_f("t1", None)], [_f("t1", "2026-10-15")])
    assert c.deriva_dias is None
    assert c.estado == "sin_cambio"

    (c,) = comparar([_f("t1", "2026-09-30")], [_f("t1", None)])
    assert c.deriva_dias is None


def test_alcance_agregado_es_nueva_y_no_un_atraso():
    base = [_f("t1", "2026-09-30")]
    plan = [_f("t1", "2026-09-30"), _f("t2", "2026-12-31")]
    _, nueva = comparar(base, plan)
    assert nueva.estado == "nueva"
    assert nueva.base_fin is None
    assert nueva.deriva_dias is None


def test_alcance_quitado_es_retirada_y_no_un_adelanto():
    base = [_f("t1", "2026-09-30"), _f("t2", "2026-12-31")]
    plan = [_f("t1", "2026-09-30")]
    filas = comparar(base, plan)
    retirada = [c for c in filas if c.estado == "retirada"]
    assert len(retirada) == 1
    # El nombre es el de la captura: la tarea ya no existe y esta fila es lo
    # único que queda de ella.
    assert retirada[0].nombre == "Tt2"
    assert retirada[0].plan_fin is None


def test_se_empareja_por_id_y_no_por_codigo_edt():
    """El plan tiene un botón que renumera el EDT. Emparejar por código haría que
    una renumeración —que no mueve ninguna fecha— apareciera como el plan entero
    reemplazado."""
    base = [_f("t1", "2026-09-30", wbs="1.1")]
    plan = [_f("t1", "2026-09-30", wbs="2.4")]
    (c,) = comparar(base, plan)
    assert c.estado == "sin_cambio"
    # El código que se muestra es el de hoy: es el que el usuario está viendo.
    assert c.wbs_code == "2.4"


def test_la_deriva_real_es_distinta_de_la_del_plan():
    """El plan se puede reescribir para que la desviación desaparezca; la fecha
    de cierre no. Un tablero que solo mira la primera premia replanificar."""
    base = [_f("t1", "2026-09-30")]
    plan = [_f("t1", "2026-11-30", cerrada_el=date(2026, 11, 20))]
    (c,) = comparar(base, plan)
    assert c.deriva_dias == 61
    assert c.deriva_real_dias == 51


def test_el_resumen_cuenta_cada_cosa_por_separado():
    base = [_f("t1", "2026-09-30"), _f("t2", "2026-09-30"), _f("t3", "2026-09-30")]
    plan = [
        _f("t1", "2026-10-30"),  # corrida
        _f("t2", "2026-09-30"),  # sin cambio
        _f("t4", "2026-12-31"),  # nueva
    ]  # t3 retirada
    r = resumir(base, plan, comparar(base, plan))
    assert (r.corridas, r.sin_cambio, r.nuevas, r.retiradas) == (1, 1, 1, 1)
    assert r.total_base == 3
    assert r.total_plan == 3


def test_el_resumen_da_la_peor_deriva_y_no_el_promedio():
    """Veinte tareas en fecha y una corrida cuatro meses dan un promedio
    tranquilizador. La peor es la que hay que mirar."""
    base = [_f(f"t{i}", "2026-09-30") for i in range(5)]
    plan = [_f(f"t{i}", "2026-09-30") for i in range(4)] + [_f("t4", "2027-01-30")]
    r = resumir(base, plan, comparar(base, plan))
    assert r.peor_deriva_dias == 122
    assert r.peor_deriva_task_id == "t4"


def test_sin_ninguna_tarea_corrida_no_hay_peor():
    """Devolver la menos adelantada bajo ese nombre haría leer un adelanto como
    un atraso."""
    base = [_f("t1", "2026-09-30")]
    plan = [_f("t1", "2026-09-20")]
    r = resumir(base, plan, comparar(base, plan))
    assert r.peor_deriva_dias is None
    assert r.peor_deriva_task_id is None


def test_la_deriva_del_proyecto_es_el_fin_mas_tardio_contra_el_prometido():
    base = [_f("t1", "2026-09-30"), _f("t2", "2026-06-30")]
    plan = [_f("t1", "2026-09-30"), _f("t2", "2026-11-15")]
    r = resumir(base, plan, comparar(base, plan))
    assert r.fin_base == date(2026, 9, 30)
    assert r.fin_plan == date(2026, 11, 15)
    assert r.deriva_proyecto_dias == 46


def test_un_plan_sin_fechas_no_tiene_deriva_de_proyecto():
    r = resumir([_f("t1", None)], [_f("t1", None)], [])
    assert r.deriva_proyecto_dias is None
    assert r.fin_base is None


# ---------------------------------------------------------------------------
# TC-212.2 — Contra la API
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
                "description": "US-212",
                "type": "transformacion",
                "priority": 3,
                "organization_id": org,
                "pm_id": me,
            },
            headers=h,
        )
    ).json()["id"]

    async def tarea(nombre: str, wbs: str, inicio: str, fin: str) -> str:
        r = await client.post(
            f"/api/v1/projects/{proyecto}/tasks",
            json={
                "name": nombre,
                "wbs_code": wbs,
                "start_date": inicio,
                "end_date": fin,
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return {"h": h, "proyecto": proyecto, "tarea": tarea, "org": org, "me": me}


@pytest.mark.asyncio
async def test_sin_linea_base_la_respuesta_lo_dice(client, db_session):
    """No una comparación de ceros: «no sabemos si se desvió» ≠ «no se desvió»."""
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison", headers=e["h"]
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["has_baseline"] is False
    assert d["summary"] is None
    assert d["rows"] == []


@pytest.mark.asyncio
async def test_capturar_copia_el_plan_de_hoy(client, db_session):
    e = await _escenario(client, db_session)
    await e["tarea"]("Diseño", "1", "2026-09-01", "2026-09-30")
    await e["tarea"]("Build", "2", "2026-10-01", "2026-11-30")

    r = await client.post(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines",
        json={"name": "Firmada con el cliente", "note": "Kickoff"},
        headers=e["h"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["task_count"] == 2
    assert r.json()["name"] == "Firmada con el cliente"
    assert r.json()["captured_by_name"]

    comp = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert comp["has_baseline"] is True
    assert comp["summary"]["tasks_in_baseline"] == 2
    assert comp["summary"]["project_slip_days"] == 0
    assert {f["state"] for f in comp["rows"]} == {"sin_cambio"}


@pytest.mark.asyncio
async def test_mover_una_fecha_aparece_como_corrida(client, db_session):
    e = await _escenario(client, db_session)
    tid = await e["tarea"]("Build", "1", "2026-10-01", "2026-11-30")
    await client.post(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines",
        json={"name": "v1"},
        headers=e["h"],
    )
    r = await client.patch(
        f"/api/v1/tasks/{tid}", json={"end_date": "2026-12-31"}, headers=e["h"]
    )
    assert r.status_code == 200, r.text

    comp = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert comp["summary"]["slipped"] == 1
    assert comp["summary"]["project_slip_days"] == 31
    fila = comp["rows"][0]
    assert fila["slip_days"] == 31
    assert fila["baseline_end"] == "2026-11-30"
    assert fila["plan_end"] == "2026-12-31"


@pytest.mark.asyncio
async def test_una_tarea_agregada_despues_es_alcance_nuevo(client, db_session):
    e = await _escenario(client, db_session)
    await e["tarea"]("Diseño", "1", "2026-09-01", "2026-09-30")
    await client.post(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines",
        json={"name": "v1"},
        headers=e["h"],
    )
    await e["tarea"]("Extra", "2", "2026-10-01", "2026-12-31")

    comp = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert comp["summary"]["added"] == 1
    assert comp["summary"]["slipped"] == 0


@pytest.mark.asyncio
async def test_borrar_una_tarea_no_encoge_la_promesa(client, db_session):
    """La fila de la foto sobrevive al borrado. Si no, la comparación mentiría en
    la dirección cómoda: parecería que nunca se prometió esa tarea."""
    e = await _escenario(client, db_session)
    a = await e["tarea"]("Queda", "1", "2026-09-01", "2026-09-30")
    b = await e["tarea"]("Se va", "2", "2026-10-01", "2026-12-31")
    await client.post(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines",
        json={"name": "v1"},
        headers=e["h"],
    )
    assert (await client.delete(f"/api/v1/tasks/{b}", headers=e["h"])).status_code == 204

    comp = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert comp["summary"]["tasks_in_baseline"] == 2
    assert comp["summary"]["removed"] == 1
    retiradas = [f for f in comp["rows"] if f["state"] == "retirada"]
    assert len(retiradas) == 1
    assert retiradas[0]["name"] == "Se va"
    assert a in {f["task_id"] for f in comp["rows"]}


@pytest.mark.asyncio
async def test_las_capturas_se_apilan_y_se_puede_comparar_contra_una_vieja(
    client, db_session
):
    e = await _escenario(client, db_session)
    tid = await e["tarea"]("Build", "1", "2026-10-01", "2026-11-30")
    v1 = (
        await client.post(
            f"/api/v1/projects/{e['proyecto']}/plan/baselines",
            json={"name": "v1"},
            headers=e["h"],
        )
    ).json()["id"]
    await client.patch(
        f"/api/v1/tasks/{tid}", json={"end_date": "2026-12-31"}, headers=e["h"]
    )
    v2 = (
        await client.post(
            f"/api/v1/projects/{e['proyecto']}/plan/baselines",
            json={"name": "v2 replan", "note": "Se corrió el go-live"},
            headers=e["h"],
        )
    ).json()["id"]
    assert v1 != v2

    listado = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baselines", headers=e["h"]
        )
    ).json()["baselines"]
    assert [b["name"] for b in listado] == ["v2 replan", "v1"]

    # Contra la vigente (v2) no hay desviación; contra v1 sí. Ese es el punto de
    # apilarlas: la promesa vieja sigue existiendo.
    contra_v2 = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert contra_v2["summary"]["slipped"] == 0
    assert contra_v2["baseline_count"] == 2

    contra_v1 = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison"
            f"?baseline_id={v1}",
            headers=e["h"],
        )
    ).json()
    assert contra_v1["summary"]["slipped"] == 1
    assert contra_v1["baseline"]["name"] == "v1"


@pytest.mark.asyncio
async def test_borrar_una_linea_base_capturada_por_error(client, db_session):
    e = await _escenario(client, db_session)
    await e["tarea"]("Build", "1", "2026-10-01", "2026-11-30")
    bid = (
        await client.post(
            f"/api/v1/projects/{e['proyecto']}/plan/baselines",
            json={"name": "typo"},
            headers=e["h"],
        )
    ).json()["id"]
    r = await client.delete(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines/{bid}", headers=e["h"]
    )
    assert r.status_code == 204, r.text
    comp = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert comp["has_baseline"] is False


@pytest.mark.asyncio
async def test_un_plan_vacio_se_puede_capturar(client, db_session):
    """Capturar antes de cargar el plan es una secuencia legítima: el proyecto se
    aprueba y después se detalla. Lo que la comparación dirá es que todo el plan
    es alcance nuevo, que es lo que pasó."""
    e = await _escenario(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines",
        json={"name": "Aprobada en comité"},
        headers=e["h"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["task_count"] == 0
    await e["tarea"]("Todo", "1", "2026-09-01", "2026-09-30")
    comp = (
        await client.get(
            f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison",
            headers=e["h"],
        )
    ).json()
    assert comp["summary"]["added"] == 1


@pytest.mark.asyncio
async def test_una_linea_base_de_otro_proyecto_no_se_puede_pedir(client, db_session):
    e = await _escenario(client, db_session)
    creado = await client.post(
        "/api/v1/projects",
        json={
            "name": "Otro",
            "description": "x",
            "type": "transformacion",
            "priority": 3,
            "organization_id": e["org"],
            "pm_id": e["me"],
        },
        headers=e["h"],
    )
    assert creado.status_code == 201, creado.text
    otro = creado.json()["id"]
    bid = (
        await client.post(
            f"/api/v1/projects/{otro}/plan/baselines",
            json={"name": "del otro"},
            headers=e["h"],
        )
    ).json()["id"]
    r = await client.get(
        f"/api/v1/projects/{e['proyecto']}/plan/baseline-comparison?baseline_id={bid}",
        headers=e["h"],
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_el_nombre_es_obligatorio(client, db_session):
    """«Línea base 3» no le dice a nadie contra qué está comparando."""
    e = await _escenario(client, db_session)
    r = await client.post(
        f"/api/v1/projects/{e['proyecto']}/plan/baselines",
        json={"name": ""},
        headers=e["h"],
    )
    assert r.status_code == 422, r.text
