"""D-9 — un hito tiene duración cero, y ahora se hace cumplir.

Regla del glosario (`docs/dominio/02-GLOSARIO.md` §1.2): «`is_milestone = true`
⟹ `duration_days = 0`. Hoy no está validado». La revisión la aprobó como D-9.

El caso que la incumplía **no era raro**: `compute_duration_days` cuenta días
inclusivos, así que un hito con la misma fecha de inicio y fin daba 1. Es decir,
el hito normal, creado de la forma normal.

Se reparte en dos mitades porque las dos contradicciones no son iguales:

- **La duración se normaliza**, no se rechaza. Es un valor derivado: el endpoint
  ignora el que manda el cliente y lo recalcula de las fechas (US-090). Un 422
  sobre algo que el usuario no controla lo deja sin salida. Y como las tareas se
  escriben desde seis sitios, la normalización va en el modelo.
- **El rango sí se rechaza.** Marcar «hito» y darle tres días es una
  contradicción que quien la escribe puede arreglar, y el mensaje dice cómo.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.task import Task, normalizar_hito
from tests.factories import create_admin_role, create_tenant, create_user, login


@pytest.fixture
async def proyecto(client, db_session):
    """Un proyecto con su administrador, para colgarle tareas."""
    inquilino = await create_tenant(db_session, slug="d9", name="D-9")
    rol = await create_admin_role(db_session, inquilino)
    await create_user(
        db_session, tenant=inquilino, username="d9_admin",
        email="d9@ejemplo.test", password="Str0ng-Pass-A1!", roles=[rol],
    )
    auth = await login(client, "d9_admin", "Str0ng-Pass-A1!")

    org = await client.post(
        "/api/v1/organizations", json={"name": "Org D-9"}, headers=auth["_authz"]
    )
    yo = await client.get("/api/v1/auth/me", headers=auth["_authz"])
    r = await client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto D-9", "description": "d", "type": "innovacion",
            "priority": 3, "organization_id": org.json()["id"],
            "pm_id": yo.json()["id"],
        },
        headers=auth["_authz"],
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"], auth["_authz"]


# ---------------------------------------------------------------------------
# La regla, sin pasar por HTTP
# ---------------------------------------------------------------------------


def test_el_normalizador_pone_la_duracion_en_cero():
    tarea = Task(name="Firma del contrato", is_milestone=True, duration_days=5)

    normalizar_hito(tarea)

    assert tarea.duration_days == 0


def test_el_normalizador_no_toca_las_actividades():
    """La regla es solo para hitos: una actividad de 5 días sigue siendo de 5."""
    tarea = Task(name="Desarrollo", is_milestone=False, duration_days=5)

    normalizar_hito(tarea)

    assert tarea.duration_days == 5


# ---------------------------------------------------------------------------
# La regla, al guardar — que es donde tiene que valer pase lo que pase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_al_insertar_un_hito_la_duracion_queda_en_cero(db_session):
    """Cubre los seis caminos de escritura de una vez: el evento es del modelo."""
    tarea = Task(
        tenant_id="t", project_id="p", name="Puesta en marcha",
        is_milestone=True, duration_days=7,
    )
    db_session.add(tarea)
    await db_session.commit()

    guardada = (
        await db_session.execute(select(Task).where(Task.id == tarea.id))
    ).scalar_one()
    assert guardada.duration_days == 0


@pytest.mark.asyncio
async def test_convertir_una_actividad_en_hito_le_pone_la_duracion_en_cero(db_session):
    tarea = Task(
        tenant_id="t", project_id="p", name="Revisión", duration_days=3,
        is_milestone=False,
    )
    db_session.add(tarea)
    await db_session.commit()

    tarea.is_milestone = True
    await db_session.commit()

    assert tarea.duration_days == 0


# ---------------------------------------------------------------------------
# Por HTTP — el caso corriente que incumplía la regla
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_un_hito_de_un_solo_dia_ya_no_dura_uno(client, proyecto):
    """Era el caso normal: días inclusivos daban 1 donde la regla pide 0."""
    proyecto_id, cabeceras = proyecto

    r = await client.post(
        f"/api/v1/projects/{proyecto_id}/tasks",
        json={
            "name": "Aprobación del comité",
            "is_milestone": True,
            "start_date": "2026-09-01",
            "end_date": "2026-09-01",
        },
        headers=cabeceras,
    )

    assert r.status_code in (200, 201), r.text
    assert r.json()["duration_days"] == 0


@pytest.mark.asyncio
async def test_un_hito_con_rango_de_varios_dias_se_rechaza(client, proyecto):
    proyecto_id, cabeceras = proyecto

    r = await client.post(
        f"/api/v1/projects/{proyecto_id}/tasks",
        json={
            "name": "Fase de pruebas",
            "is_milestone": True,
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
        },
        headers=cabeceras,
    )

    assert r.status_code == 400
    cuerpo = r.json()["detail"]
    assert cuerpo["code"] == "VALIDATION_ERROR"
    # LEN-02: dice qué pasó, por qué y qué hacer.
    assert "hito" in cuerpo["detail"].lower()
    assert "desmarca" in cuerpo["detail"].lower()


@pytest.mark.asyncio
async def test_una_actividad_con_rango_sigue_funcionando(client, proyecto):
    """El control no sirve si de paso rompe la tarea normal."""
    proyecto_id, cabeceras = proyecto

    r = await client.post(
        f"/api/v1/projects/{proyecto_id}/tasks",
        json={
            "name": "Fase de pruebas",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
        },
        headers=cabeceras,
    )

    assert r.status_code in (200, 201), r.text
    assert r.json()["duration_days"] == 5  # días inclusivos


@pytest.mark.asyncio
async def test_un_hito_sin_fechas_tambien_queda_en_cero(client, proyecto):
    """No se exige fecha: lo que se exige es que no simule duración."""
    proyecto_id, cabeceras = proyecto

    r = await client.post(
        f"/api/v1/projects/{proyecto_id}/tasks",
        json={"name": "Cierre", "is_milestone": True, "duration_days": 10},
        headers=cabeceras,
    )

    assert r.status_code in (200, 201), r.text
    assert r.json()["duration_days"] == 0


@pytest.mark.asyncio
async def test_ninguna_tarea_guardada_contradice_la_regla(db_session):
    """La invariante, dicha entera: si es hito, dura cero. Sin excepciones."""
    for i, (hito, duracion) in enumerate(
        [(True, 9), (False, 4), (True, None), (False, None)]
    ):
        db_session.add(
            Task(
                tenant_id="t", project_id="p", name=f"T{i}",
                is_milestone=hito, duration_days=duracion,
                start_date=date(2026, 9, 1),
            )
        )
    await db_session.commit()

    incumplen = [
        t.name
        for t in (await db_session.execute(select(Task))).scalars().all()
        if t.is_milestone and t.duration_days != 0
    ]
    assert not incumplen, f"Estas tareas son hitos y no duran cero: {incumplen}"
