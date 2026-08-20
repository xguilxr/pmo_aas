"""US-208 — La carga por persona y semana.

El heatmap del artboard «Recursos › Capacidad». Ya existía una matriz **mensual**
(US-186) y no sirve para esto: alguien al 90 % de media en septiembre puede estar
al 160 % la semana del corte y al 40 % el resto, y el promedio mensual esconde
exactamente el pico que hay que renivelar.

Lo que estos tests cuidan es lo que un cálculo por buckets rompe sin ruido:

1. **Una asignación pesa en las semanas que toca y solo en esas.** Si el rango se
   comparara mal —por ejemplo, con el lunes en vez de con el domingo— el valor
   se correría una columna y nadie lo notaría, porque el número sigue siendo
   plausible.
2. **Sin fechas la asignación es indefinida, no inexistente.** Tratar `None`
   como «no aplica» hace desaparecer del heatmap a quien está asignado sin plazo.
3. **La fila de equipo promedia, no suma.** Sumar seis miembros daría 720 %.
4. **La demanda de una persona cuenta todos sus proyectos**, aunque el filtro sea
   de una organización: quien está saturado lo está por la suma de todo.
"""
from datetime import date, timedelta
from itertools import pairwise

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from app.services.capacity import _semanas, weekly_load
from tests.factories import create_admin_role, create_tenant, create_user, login

# Un lunes fijo, para que el test no dependa del día en que corra. La semana
# ISO de esta fecha es la 35 de 2026.
LUNES = date(2026, 8, 24)


async def _setup(client, db_session):
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
        await client.post("/api/v1/organizations", json={"name": "Org1"}, headers=h)
    ).json()["id"]
    me = (await client.get("/api/v1/auth/me", headers=h)).json()["id"]

    async def proyecto(nombre):
        r = await client.post(
            "/api/v1/projects",
            json={
                "name": nombre,
                "description": "US-208",
                "type": "transformacion",
                "priority": 3,
                "organization_id": org,
                "pm_id": me,
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    tenant = (
        await db_session.execute(select(Tenant).where(Tenant.id == str(t.id)))
    ).scalar_one()
    return h, tenant, org, proyecto


async def _actor(client, h, nombre, capacidad=100, **extra):
    r = await client.post(
        "/api/v1/actors",
        json={"name": nombre, "project_capacity_pct": capacidad, **extra},
        headers=h,
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _equipo(client, h, org, nombre):
    """Un equipo con su área.

    `Team.area_id` es obligatorio —un equipo operativo pertenece a un área
    funcional, no flota— y el área necesita alcance (BUG-085): un área sin
    alcance no aparecería en ninguna pantalla.
    """
    ra = await client.post(
        "/api/v1/areas",
        json={"name": f"Área de {nombre}", "organization_id": org},
        headers=h,
    )
    assert ra.status_code in (200, 201), ra.text
    area = ra.json()["id"]
    r = await client.post(
        "/api/v1/teams", json={"name": nombre, "area_id": area}, headers=h
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _asignar(client, h, pid, actor_id, pct, inicio=None, fin=None):
    cuerpo = {"actor_id": actor_id, "allocation_pct": pct}
    if inicio:
        cuerpo["start_date"] = inicio.isoformat()
    if fin:
        cuerpo["end_date"] = fin.isoformat()
    r = await client.post(
        f"/api/v1/projects/{pid}/participations", json=cuerpo, headers=h
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


# ---------------------------------------------------------------------------
# TC-208.1 — Las semanas del horizonte
# ---------------------------------------------------------------------------


def test_las_semanas_empiezan_el_lunes_de_la_semana_en_curso():
    """Media semana como primera columna daría un porcentaje incomparable con
    las de al lado."""
    # Un miércoles: la primera semana tiene que empezar el lunes anterior.
    semanas = _semanas(3, date(2026, 8, 26))
    assert semanas[0][1] == LUNES
    assert semanas[0][2] == LUNES + timedelta(days=6)
    assert [e for e, _, _ in semanas] == ["s35", "s36", "s37"]
    # Consecutivas y sin huecos: el domingo de una es el día antes del lunes de
    # la siguiente.
    for anterior, siguiente in pairwise(semanas):
        assert anterior[2] + timedelta(days=1) == siguiente[1]


def test_el_numero_de_semana_es_el_iso():
    """La etiqueta es lo que una PMO usa para hablar de fechas («a la s37»)."""
    semanas = _semanas(1, LUNES)
    assert semanas[0][0] == f"s{LUNES.isocalendar().week}"


# ---------------------------------------------------------------------------
# TC-208.2 — Una asignación pesa en las semanas que toca
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_asignacion_pesa_solo_en_sus_semanas(client, db_session):
    h, tenant, _org, proyecto = await _setup(client, db_session)
    pid = await proyecto("ERP")
    actor = await _actor(client, h, "L. Fuentes", capacidad=100)
    # Dos semanas exactas: la primera y la segunda del horizonte.
    await _asignar(
        client, h, pid, actor, 60, inicio=LUNES, fin=LUNES + timedelta(days=13)
    )
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=4, today=LUNES)
    fila = next(f for f in datos["rows"] if f["name"] == "L. Fuentes")
    # 60 en s35 y s36; 0 en s37 y s38. Un desfase de una columna daría
    # [0, 60, 60, 0], que es igual de plausible y está mal.
    assert fila["per_week"] == [60.0, 60.0, 0.0, 0.0]
    assert fila["peak_pct"] == 60.0


@pytest.mark.asyncio
async def test_dos_asignaciones_se_suman_en_la_semana_que_solapan(client, db_session):
    """Es el caso que el heatmap existe para encontrar: el pico."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    p1 = await proyecto("ERP")
    p2 = await proyecto("Data Center")
    actor = await _actor(client, h, "R. Cantú", capacidad=100)
    await _asignar(client, h, p1, actor, 80, inicio=LUNES, fin=LUNES + timedelta(days=6))
    await _asignar(
        client,
        h,
        p2,
        actor,
        60,
        inicio=LUNES + timedelta(days=3),
        fin=LUNES + timedelta(days=13),
    )
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=3, today=LUNES)
    fila = next(f for f in datos["rows"] if f["name"] == "R. Cantú")
    assert fila["per_week"] == [140.0, 60.0, 0.0]
    assert fila["projects_count"] == 2


@pytest.mark.asyncio
async def test_sin_fechas_la_asignacion_es_indefinida(client, db_session):
    """`None` es «sin plazo», no «no aplica».

    Tratarlo como lo segundo hace desaparecer del heatmap a quien está asignado
    sin fecha de fin — que es la mitad de las asignaciones reales.
    """
    h, tenant, _org, proyecto = await _setup(client, db_session)
    pid = await proyecto("BAU")
    actor = await _actor(client, h, "S. Peralta", capacidad=100)
    await _asignar(client, h, pid, actor, 50)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=4, today=LUNES)
    fila = next(f for f in datos["rows"] if f["name"] == "S. Peralta")
    assert fila["per_week"] == [50.0, 50.0, 50.0, 50.0]


# ---------------------------------------------------------------------------
# TC-208.3 — Filas de equipo: promedio, no suma
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_la_fila_de_equipo_promedia_a_sus_miembros(client, db_session):
    h, tenant, org, proyecto = await _setup(client, db_session)
    pid = await proyecto("QA")
    equipo = await _equipo(client, h, org, "Equipo QA")
    a1 = await _actor(client, h, "QA Uno", capacidad=100, team_id=equipo)
    a2 = await _actor(client, h, "QA Dos", capacidad=100, team_id=equipo)
    await _asignar(client, h, pid, a1, 100)
    await _asignar(client, h, pid, a2, 40)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=2, today=LUNES)
    equipo_fila = next(
        f for f in datos["rows"] if f["kind"] == "team" and f["name"] == "Equipo QA"
    )
    # (100 + 40) / 2 = 70. La suma daría 140, que como «carga del equipo» no
    # significa nada.
    assert equipo_fila["per_week"] == [70.0, 70.0]
    assert equipo_fila["members"] == 2
    # Y las personas siguen ahí: la fila de equipo se suma, no las reemplaza.
    nombres = {f["name"] for f in datos["rows"] if f["kind"] == "actor"}
    assert {"QA Uno", "QA Dos"} <= nombres


@pytest.mark.asyncio
async def test_un_equipo_de_uno_no_genera_fila(client, db_session):
    """Repetiría la fila de su único miembro."""
    h, tenant, org, proyecto = await _setup(client, db_session)
    pid = await proyecto("QA")
    equipo = await _equipo(client, h, org, "Equipo Solo")
    a1 = await _actor(client, h, "Único", capacidad=100, team_id=equipo)
    await _asignar(client, h, pid, a1, 80)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=2, today=LUNES)
    assert not [f for f in datos["rows"] if f["kind"] == "team"]


# ---------------------------------------------------------------------------
# TC-208.4 — Quién entra en el heatmap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_los_recursos_sin_asignacion_no_ensucian_el_heatmap(client, db_session):
    """Treinta y ocho filas en cero se leen peor que su ausencia."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    pid = await proyecto("ERP")
    asignado = await _actor(client, h, "Asignada", capacidad=100)
    await _actor(client, h, "Sin nada", capacidad=100)
    await _asignar(client, h, pid, asignado, 50)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=2, today=LUNES)
    assert [f["name"] for f in datos["rows"]] == ["Asignada"]


@pytest.mark.asyncio
async def test_sin_recursos_devuelve_las_semanas_y_ninguna_fila(client, db_session):
    """DIS-03 — la pantalla necesita las columnas para decir «no hay nadie»."""
    h, tenant, _org, _proyecto = await _setup(client, db_session)
    await db_session.commit()
    datos = await weekly_load(db_session, tenant, weeks=5, today=LUNES)
    assert len(datos["weeks"]) == 5
    assert datos["rows"] == []
    assert datos["shared_critical"] == []
    assert datos["suggested"] == []


# ---------------------------------------------------------------------------
# TC-208.5 — Los otros tres paneles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capacidad_vs_demanda_en_fte(client, db_session):
    """En FTE y no en porcentaje: «1.4 de 2.0 personas» se entiende sin
    convertir, y «140 % de 200 %» no."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    pid = await proyecto("ERP")
    a1 = await _actor(client, h, "Uno", capacidad=100)
    a2 = await _actor(client, h, "Dos", capacidad=100)
    await _asignar(client, h, pid, a1, 100)
    await _asignar(client, h, pid, a2, 40)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=4, today=LUNES)
    assert datos["capacity_vs_demand"], "hay que devolver al menos un mes"
    primero = datos["capacity_vs_demand"][0]
    assert primero["capacity_fte"] == 2.0
    assert primero["demand_fte"] == 1.4


@pytest.mark.asyncio
async def test_criticos_compartidos_son_los_de_dos_o_mas_proyectos(
    client, db_session
):
    """«Compartido» es medido, no declarado: con un proyecto no hay nada que
    compartir, tenga la marca puesta o no."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    p1 = await proyecto("ERP")
    p2 = await proyecto("Data Center")
    compartido = await _actor(client, h, "Compartida", capacidad=100)
    solo = await _actor(client, h, "Dedicada", capacidad=100)
    await _asignar(client, h, p1, compartido, 60)
    await _asignar(client, h, p2, compartido, 60)
    await _asignar(client, h, p1, solo, 100)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=2, today=LUNES)
    assert [c["name"] for c in datos["shared_critical"]] == ["Compartida"]
    assert datos["shared_critical"][0]["projects_count"] == 2
    assert sorted(datos["shared_critical"][0]["projects"]) == ["Data Center", "ERP"]


@pytest.mark.asyncio
async def test_la_sugerencia_nombra_recurso_y_semanas(client, db_session):
    """Un consejo genérico no es una acción. La frase tiene que decir quién y
    cuándo, porque es lo que hace falta para renivelar."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    p1 = await proyecto("ERP")
    p2 = await proyecto("Data Center")
    actor = await _actor(client, h, "L. Fuentes", capacidad=100)
    await _asignar(client, h, p1, actor, 100, inicio=LUNES, fin=LUNES + timedelta(days=13))
    await _asignar(client, h, p2, actor, 60, inicio=LUNES, fin=LUNES + timedelta(days=13))
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=4, today=LUNES)
    assert datos["suggested"], "un recurso al 160 % tiene que producir sugerencia"
    frase = datos["suggested"][0]
    assert "L. Fuentes" in frase
    assert "s35" in frase and "s36" in frase
    assert "160" in frase


@pytest.mark.asyncio
async def test_sin_sobrecarga_no_hay_sugerencia(client, db_session):
    """Inventar un consejo cuando no hay nada que hacer entrena a la gente a
    ignorar el panel."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    pid = await proyecto("ERP")
    actor = await _actor(client, h, "Tranquila", capacidad=100)
    await _asignar(client, h, pid, actor, 40)
    await db_session.commit()

    datos = await weekly_load(db_session, tenant, weeks=3, today=LUNES)
    assert datos["suggested"] == []


# ---------------------------------------------------------------------------
# TC-208.6 — El endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_endpoint_responde_con_el_desglose_de_la_celda(client, db_session):
    """`assignments` es lo que resuelve el «click en una celda» del mockup sin
    una ida al servidor por celda."""
    h, tenant, _org, proyecto = await _setup(client, db_session)
    pid = await proyecto("ERP Rollout")
    actor = await _actor(client, h, "L. Fuentes", capacidad=100)
    await _asignar(client, h, pid, actor, 70)
    await db_session.commit()

    r = await client.get("/api/v1/capacity/weekly-load?weeks=6", headers=h)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert len(cuerpo["weeks"]) == 6
    fila = next(f for f in cuerpo["rows"] if f["name"] == "L. Fuentes")
    assert len(fila["per_week"]) == 6
    assert [a["project_name"] for a in fila["assignments"]] == ["ERP Rollout"]
    assert fila["assignments"][0]["allocation_pct"] == 70


@pytest.mark.asyncio
async def test_el_endpoint_rechaza_un_horizonte_absurdo(client, db_session):
    """La respuesta lleva una serie por recurso: el ancho multiplica."""
    h, _tenant, _org, _proyecto = await _setup(client, db_session)
    r = await client.get("/api/v1/capacity/weekly-load?weeks=500", headers=h)
    assert r.status_code == 422
