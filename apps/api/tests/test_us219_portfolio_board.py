"""US-219 — El Portfolio Board: proyectos por estatus de reporte.

El artboard «Boards» nombra tres cubos: «al día / vencido / con decisiones
pendientes». Los dos primeros son estados de reporte y se excluyen entre sí; el
tercero es otro eje.

Lo que estos tests cuidan:

1. **«Con decisiones pendientes» no puede ser columna.** Un proyecto al día
   también puede tener decisiones esperando. Como columna habría que duplicar la
   tarjeta —y entonces los conteos de columna dejan de sumar el total— o elegir
   una arbitrariamente y esconder la otra mitad. Va como marcador.
2. **Los cerrados quedan fuera.** Un proyecto cerrado no se reporta: tenerlo en
   «sin reporte» para siempre convierte la columna en un cementerio y esconde
   los vivos.
3. **Las columnas suman el total.** Es la comprobación que detecta que una
   tarjeta se duplicó o se perdió.
"""
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.modules import Issue
from app.models.project import Project
from app.models.report_history import ReportHistory
from tests.factories import create_admin_role, create_tenant, create_user, login


async def _escenario(client, db_session):
    """Cuatro proyectos activos, uno cerrado, y un reporte de distinta edad.

    - Nunca reportado → sin_reporte
    - Reportado hace 20 días (cadencia 14) → vencido
    - Reportado hace 13 días → por_vencer (ventana = 14 // 5 = 2 días)
    - Reportado hoy → al_dia
    - Cerrado y nunca reportado → **fuera del board**
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

    especificaciones = [
        ("Nunca", "ejecucion", None),
        ("Vencido", "ejecucion", 20),
        ("PorVencer", "ejecucion", 13),
        ("AlDia", "ejecucion", 0),
        ("Cerrado", "cerrado", None),
    ]
    proyectos: dict[str, Project] = {}
    for i, (nombre, fase, _atras) in enumerate(especificaciones):
        p = Project(
            tenant_id=t.id,
            organization_id=org,
            folio=f"SEED-2026-{i + 1:03d}",
            name=nombre,
            phase=fase,
        )
        db_session.add(p)
        proyectos[nombre] = p
    await db_session.flush()
    for nombre, _fase, atras in especificaciones:
        if atras is None:
            continue
        db_session.add(
            ReportHistory(
                tenant_id=t.id,
                project_id=str(proyectos[nombre].id),
                report_type="status",
                generated_at=datetime.now(UTC) - timedelta(days=atras),
            )
        )
    await db_session.commit()
    return {"tenant": t, "h": h, "org": org, "proyectos": proyectos}


def _por_estado(cuerpo) -> dict[str, list[str]]:
    return {c["status"]: [p["name"] for p in c["projects"]] for c in cuerpo["columns"]}


@pytest.mark.asyncio
async def test_las_cuatro_columnas_en_orden_de_urgencia(client, db_session):
    """`sin_reporte` primero: un proyecto que nunca se reportó no incumplió una
    fecha, no ha empezado. En un onboarding es la columna que hay que vaciar."""
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/portfolio-board", headers=e["h"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert [c["status"] for c in cuerpo["columns"]] == [
        "sin_reporte",
        "vencido",
        "por_vencer",
        "al_dia",
    ]
    # Y la etiqueta viene en español desde el servidor.
    assert [c["label"] for c in cuerpo["columns"]] == [
        "sin reporte",
        "vencido",
        "por vencer",
        "al día",
    ]


@pytest.mark.asyncio
async def test_cada_proyecto_cae_en_su_columna(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/portfolio-board", headers=e["h"])
    porestado = _por_estado(r.json())
    assert porestado["sin_reporte"] == ["Nunca"]
    assert porestado["vencido"] == ["Vencido"]
    assert porestado["por_vencer"] == ["PorVencer"]
    assert porestado["al_dia"] == ["AlDia"]


@pytest.mark.asyncio
async def test_los_cerrados_quedan_fuera(client, db_session):
    """Tenerlos en «sin reporte» para siempre convierte la columna en un
    cementerio y esconde los vivos."""
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/portfolio-board", headers=e["h"])
    cuerpo = r.json()
    todos = [p["name"] for c in cuerpo["columns"] for p in c["projects"]]
    assert "Cerrado" not in todos
    assert cuerpo["total"] == 4


@pytest.mark.asyncio
async def test_las_columnas_suman_el_total(client, db_session):
    """La comprobación que detecta que una tarjeta se duplicó o se perdió."""
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/dashboard/portfolio-board", headers=e["h"])
    cuerpo = r.json()
    assert sum(len(c["projects"]) for c in cuerpo["columns"]) == cuerpo["total"]


@pytest.mark.asyncio
async def test_las_decisiones_son_marcador_y_no_columna(client, db_session):
    """Un proyecto al día con decisiones pendientes sigue en «al día», con su
    marcador: como columna habría que duplicarlo o esconder la mitad del dato."""
    e = await _escenario(client, db_session)
    al_dia = e["proyectos"]["AlDia"]
    for i, (tipo, estado) in enumerate(
        [("decision", "open"), ("decision", "on_hold"), ("decision", "resolved"),
         ("issue", "open")]
    ):
        db_session.add(
            Issue(
                tenant_id=e["tenant"].id,
                project_id=str(al_dia.id),
                folio=f"ISS-2026-{i + 1:03d}",
                title=f"Item {i + 1}",
                status=estado,
                type=tipo,
                reported_at=datetime.now(UTC),
            )
        )
    await db_session.commit()

    r = await client.get("/api/v1/dashboard/portfolio-board", headers=e["h"])
    cuerpo = r.json()
    porestado = _por_estado(cuerpo)
    # Sigue en su columna: no se mueve ni se duplica.
    assert porestado["al_dia"] == ["AlDia"]
    assert sum(len(c["projects"]) for c in cuerpo["columns"]) == cuerpo["total"]
    tarjeta = next(
        p
        for c in cuerpo["columns"]
        for p in c["projects"]
        if p["name"] == "AlDia"
    )
    # Dos decisiones abiertas: la resuelta no cuenta y el issue tampoco.
    assert tarjeta["pending_decisions"] == 2


@pytest.mark.asyncio
async def test_la_tarjeta_trae_lo_que_la_pila_necesita(client, db_session):
    """Sin el retraso y el hito la tarjeta obliga a abrir el proyecto para
    saber si es urgente, que es lo que un board viene a evitar."""
    from app.models.task import Task

    e = await _escenario(client, db_session)
    vencido = e["proyectos"]["Vencido"]
    db_session.add(
        Task(
            tenant_id=e["tenant"].id,
            project_id=str(vencido.id),
            wbs_code="1",
            name="Corte de servicios",
            is_milestone=True,
            status="not_started",
            end_date=date.today() + timedelta(days=5),
        )
    )
    await db_session.commit()

    r = await client.get("/api/v1/dashboard/portfolio-board", headers=e["h"])
    tarjeta = next(
        p
        for c in r.json()["columns"]
        for p in c["projects"]
        if p["name"] == "Vencido"
    )
    # Veinte días sin reportar con cadencia catorce: seis de retraso.
    assert tarjeta["report_days_late"] == 6
    assert tarjeta["next_milestone"]["name"] == "Corte de servicios"
    assert tarjeta["health"] and tarjeta["phase"] == "ejecucion"


@pytest.mark.asyncio
async def test_el_filtro_de_organizacion_recorta(client, db_session):
    e = await _escenario(client, db_session)
    otra = (
        await client.post(
            "/api/v1/organizations", json={"name": "OrgB"}, headers=e["h"]
        )
    ).json()["id"]
    db_session.add(
        Project(
            tenant_id=e["tenant"].id,
            organization_id=otra,
            folio="SEED-2026-900",
            name="DeOtra",
            phase="ejecucion",
        )
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/dashboard/portfolio-board?organization_id={otra}", headers=e["h"]
    )
    cuerpo = r.json()
    assert cuerpo["total"] == 1
    assert _por_estado(cuerpo)["sin_reporte"] == ["DeOtra"]
