"""US-218 — Dependencias entre tareas de proyectos distintos.

El artboard «Proyecto — Plan» pide un Gantt con «dependencias inter-proyecto».
Dentro de un proyecto ya existían (`Task.predecessors`, por código WBS, con su
detección de ciclos, US-090); un WBS no sirve para cruzar proyectos porque el
`1.2` de uno no es el `1.2` de otro. `task_dependencies` ya podía guardar el
enlace: **no hace falta migración**, faltaban la API y el guardarraíl.

Lo que estos tests cuidan:

1. **La validación de ciclos es a nivel de TAREA, no de proyecto.** La respuesta
   fácil —«si A depende de B, prohíbe que B dependa de A»— bloquearía un caso
   normal: «les entregamos el ambiente en la fase 1 y ellos nos devuelven la
   certificación en la fase 3». Eso es A→B y B→A a nivel de proyecto y no hay
   ningún ciclo real.
2. **El recorrido cruza las dos clases de arista.** Un ciclo puede alternar
   entre las internas (por WBS) y las externas (por id); mirar solo una lo deja
   pasar.
3. **Una dependencia del mismo proyecto se rechaza.** Tener dos mecanismos para
   lo mismo es cómo empiezan a discrepar.
4. **`task_dependencies` no lleva `tenant_id`.** Sin el filtro explícito, un
   identificador adivinado tocaría la dependencia de otro cliente.
"""
from datetime import date, timedelta

import pytest

from app.models.project import Project
from app.models.task import Task, TaskDependency
from tests.factories import create_admin_role, create_tenant, create_user, login

HOY = date.today()


async def _escenario(client, db_session):
    """Dos proyectos con dos tareas cada uno.

    A: a1 → a2 (arista interna, por WBS)
    B: b1 → b2 (arista interna, por WBS)
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

    proyectos: dict[str, Project] = {}
    for i, nombre in enumerate(("A", "B")):
        p = Project(
            tenant_id=t.id,
            organization_id=org,
            folio=f"SEED-2026-{i + 1:03d}",
            name=f"Proyecto {nombre}",
            phase="ejecucion",
        )
        db_session.add(p)
        proyectos[nombre] = p
    await db_session.flush()

    tareas: dict[str, Task] = {}
    for clave, proyecto, wbs, preds, sucs in [
        ("a1", "A", "1", [], ["2"]),
        ("a2", "A", "2", ["1"], []),
        ("b1", "B", "1", [], ["2"]),
        ("b2", "B", "2", ["1"], []),
    ]:
        tarea = Task(
            tenant_id=t.id,
            project_id=str(proyectos[proyecto].id),
            wbs_code=wbs,
            name=f"Tarea {clave}",
            predecessors=preds,
            successors=sucs,
            end_date=HOY + timedelta(days=10),
        )
        db_session.add(tarea)
        tareas[clave] = tarea
    await db_session.flush()
    await db_session.commit()
    return {"tenant": t, "h": h, "org": org, "p": proyectos, "t": tareas}


def _crear(client, h, project_id, pre, suc, **extra):
    return client.post(
        f"/api/v1/projects/{project_id}/external-dependencies",
        json={
            "predecessor_task_id": str(pre.id),
            "successor_task_id": str(suc.id),
            **extra,
        },
        headers=h,
    )


# ---------------------------------------------------------------------------
# TC-218.1 — Crear el enlace
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_se_puede_enlazar_una_tarea_de_otro_proyecto(client, db_session):
    e = await _escenario(client, db_session)
    r = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["predecessor_task_id"] == str(e["t"]["a2"].id)
    assert cuerpo["successor_task_id"] == str(e["t"]["b1"].id)
    assert cuerpo["type"] == "FS"


@pytest.mark.asyncio
async def test_repetir_la_misma_dependencia_es_idempotente(client, db_session):
    """Quien la vuelve a pedir quiere que exista, y ya existe."""
    e = await _escenario(client, db_session)
    primera = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    segunda = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    assert segunda.status_code == 201
    assert segunda.json()["id"] == primera.json()["id"]


@pytest.mark.asyncio
async def test_una_tarea_no_depende_de_si_misma(client, db_session):
    e = await _escenario(client, db_session)
    r = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a1"], e["t"]["a1"])
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_el_mismo_proyecto_se_rechaza(client, db_session):
    """Dentro de un proyecto las dependencias van por WBS. Dos mecanismos para
    lo mismo es cómo empiezan a discrepar."""
    e = await _escenario(client, db_session)
    r = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a1"], e["t"]["a2"])
    assert r.status_code == 400, r.text
    assert "mismo proyecto" in r.text


@pytest.mark.asyncio
async def test_un_tipo_de_vinculo_inventado_se_rechaza(client, db_session):
    e = await _escenario(client, db_session)
    r = await _crear(
        client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"], type="XY"
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_los_cuatro_vinculos_de_ms_project_se_aceptan(client, db_session):
    """El importador ya los escribe: rechazarlos aquí haría que una dependencia
    importada no se pudiera recrear a mano."""
    e = await _escenario(client, db_session)
    for tipo in ("FS", "SS", "FF", "SF"):
        # Cada uno con un par distinto para no chocar con el índice único.
        r = await client.post(
            f"/api/v1/projects/{e['p']['A'].id}/external-dependencies",
            json={
                "predecessor_task_id": str(e["t"]["a1"].id),
                "successor_task_id": str(e["t"]["b1"].id),
                "type": tipo,
            },
            headers=e["h"],
        )
        # El primero crea; los demás son idempotentes sobre el mismo par.
        assert r.status_code == 201, (tipo, r.text)


# ---------------------------------------------------------------------------
# TC-218.2 — El guardarraíl de ciclos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_el_ciclo_directo_se_rechaza(client, db_session):
    e = await _escenario(client, db_session)
    ida = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    assert ida.status_code == 201, ida.text
    # b1 → a2 cerraría el ciclo a2 → b1 → a2.
    vuelta = await _crear(client, e["h"], e["p"]["B"].id, e["t"]["b1"], e["t"]["a2"])
    assert vuelta.status_code == 400, vuelta.text
    assert "ciclo" in vuelta.text


@pytest.mark.asyncio
async def test_el_ciclo_que_alterna_aristas_internas_y_externas_se_rechaza(
    client, db_session
):
    """El caso que un guardarraíl que mire solo una clase de arista deja pasar.

    a1 →(interna) a2 →(externa) b1 →(interna) b2, y entonces b2 → a1 cierra el
    ciclo pasando dos veces por dentro de un proyecto y dos por fuera.
    """
    e = await _escenario(client, db_session)
    r = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    assert r.status_code == 201, r.text
    cierre = await _crear(client, e["h"], e["p"]["B"].id, e["t"]["b2"], e["t"]["a1"])
    assert cierre.status_code == 400, cierre.text
    assert "ciclo" in cierre.text


@pytest.mark.asyncio
async def test_la_ida_y_la_vuelta_en_cadenas_distintas_se_permiten(
    client, db_session
):
    """El caso normal que un guardarraíl a nivel de proyecto bloquearía.

    «Les entregamos el ambiente en la fase 1 y ellos nos devuelven la
    certificación en la fase 3»: a1 → b2 y b1 → a2. A nivel de proyecto es A→B y
    B→A; a nivel de tarea son dos cadenas que no se tocan, y no hay ciclo.
    """
    e = await _escenario(client, db_session)
    # Se rompen las aristas internas para que las dos cadenas sean disjuntas.
    e["t"]["a2"].predecessors = []
    e["t"]["a1"].successors = []
    e["t"]["b2"].predecessors = []
    e["t"]["b1"].successors = []
    await db_session.commit()

    ida = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a1"], e["t"]["b2"])
    assert ida.status_code == 201, ida.text
    vuelta = await _crear(client, e["h"], e["p"]["B"].id, e["t"]["b1"], e["t"]["a2"])
    assert vuelta.status_code == 201, vuelta.text


# ---------------------------------------------------------------------------
# TC-218.3 — Listar y borrar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_las_entrantes_y_las_salientes_van_separadas(client, db_session):
    """Significan cosas distintas: una entrante es algo que este proyecto
    espera; una saliente, alguien esperándonos.

    Hace falta un tercer proyecto: encadenar A→B y B→A sobre las mismas cadenas
    **es** un ciclo, y el guardarraíl lo rechaza —lo comprueba
    `test_el_ciclo_que_alterna_...`—. Con C la ida y la vuelta son de proyectos
    distintos y no hay nada que cerrar.
    """
    e = await _escenario(client, db_session)
    tercero = Project(
        tenant_id=e["tenant"].id,
        organization_id=e["org"],
        folio="SEED-2026-003",
        name="Proyecto C",
        phase="ejecucion",
    )
    db_session.add(tercero)
    await db_session.flush()
    c1 = Task(
        tenant_id=e["tenant"].id,
        project_id=str(tercero.id),
        wbs_code="1",
        name="Tarea c1",
        end_date=HOY + timedelta(days=5),
    )
    db_session.add(c1)
    await db_session.commit()

    saliente = await _crear(
        client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"]
    )
    assert saliente.status_code == 201, saliente.text
    entrante = await _crear(client, e["h"], e["p"]["A"].id, c1, e["t"]["a1"])
    assert entrante.status_code == 201, entrante.text

    r = await client.get(
        f"/api/v1/projects/{e['p']['A'].id}/external-dependencies", headers=e["h"]
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    # Para A: la que sale de a2 es saliente; la que entra a a1 es entrante.
    assert [d["successor"]["task_name"] for d in cuerpo["salientes"]] == ["Tarea b1"]
    assert [d["predecessor"]["task_name"] for d in cuerpo["entrantes"]] == ["Tarea c1"]


@pytest.mark.asyncio
async def test_el_otro_extremo_trae_su_proyecto(client, db_session):
    """Sin el proyecto del otro extremo la fila no dice nada: «Tarea b1» sin
    saber de quién es no permite decidir nada."""
    e = await _escenario(client, db_session)
    await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    r = await client.get(
        f"/api/v1/projects/{e['p']['A'].id}/external-dependencies", headers=e["h"]
    )
    otro = r.json()["salientes"][0]["successor"]
    assert otro["project_name"] == "Proyecto B"
    assert otro["project_folio"] == "SEED-2026-002"
    assert otro["end_date"]


@pytest.mark.asyncio
async def test_se_puede_quitar_desde_cualquiera_de_los_dos_proyectos(
    client, db_session
):
    """Los dos planes están encadenados: los dos dueños pueden desligarlos."""
    e = await _escenario(client, db_session)
    creada = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    dep_id = creada.json()["id"]
    r = await client.delete(
        f"/api/v1/projects/{e['p']['B'].id}/external-dependencies/{dep_id}",
        headers=e["h"],
    )
    assert r.status_code == 204, r.text
    quedan = await client.get(
        f"/api/v1/projects/{e['p']['A'].id}/external-dependencies", headers=e["h"]
    )
    assert quedan.json()["salientes"] == []


@pytest.mark.asyncio
async def test_no_se_puede_quitar_la_dependencia_de_otro_proyecto(
    client, db_session
):
    """`task_dependencies` no lleva `tenant_id`: sin la comprobación de que la
    dependencia toca a una tarea de ESTE proyecto, un identificador adivinado
    borraría la de otro cliente."""
    e = await _escenario(client, db_session)
    creada = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a2"], e["t"]["b1"])
    dep_id = creada.json()["id"]

    tercero = Project(
        tenant_id=e["tenant"].id,
        organization_id=e["org"],
        folio="SEED-2026-003",
        name="Proyecto C",
        phase="ejecucion",
    )
    db_session.add(tercero)
    await db_session.commit()

    r = await client.delete(
        f"/api/v1/projects/{tercero.id}/external-dependencies/{dep_id}",
        headers=e["h"],
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_una_tarea_de_otro_inquilino_no_se_puede_enlazar(client, db_session):
    """404 y no 422: desde fuera no se distingue «no existe» de «es de otro
    inquilino», y decirlo confirmaría que existe."""
    e = await _escenario(client, db_session)
    otro = await create_tenant(db_session, slug="otro", name="Otro")
    ajeno = Project(
        tenant_id=otro.id,
        organization_id=e["org"],
        folio="OTRO-001",
        name="Ajeno",
        phase="ejecucion",
    )
    db_session.add(ajeno)
    await db_session.flush()
    tarea_ajena = Task(
        tenant_id=otro.id,
        project_id=str(ajeno.id),
        wbs_code="1",
        name="Ajena",
    )
    db_session.add(tarea_ajena)
    await db_session.commit()

    r = await _crear(client, e["h"], e["p"]["A"].id, e["t"]["a1"], tarea_ajena)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_un_proyecto_sin_dependencias_devuelve_las_dos_listas_vacias(
    client, db_session
):
    """DIS-03 — la pantalla necesita las dos claves para decir «ninguna»."""
    e = await _escenario(client, db_session)
    r = await client.get(
        f"/api/v1/projects/{e['p']['A'].id}/external-dependencies", headers=e["h"]
    )
    assert r.json() == {"entrantes": [], "salientes": []}


@pytest.mark.asyncio
async def test_las_internas_del_importador_no_se_listan_como_externas(
    client, db_session
):
    """El importador de MS Project escribe `task_dependencies` **dentro** de un
    proyecto. Esas no son externas y listarlas duplicaría lo que ya dice
    `predecessors`."""
    e = await _escenario(client, db_session)
    db_session.add(
        TaskDependency(
            predecessor_id=str(e["t"]["a1"].id),
            successor_id=str(e["t"]["a2"].id),
            type="FS",
            lag_days=0,
        )
    )
    await db_session.commit()

    r = await client.get(
        f"/api/v1/projects/{e['p']['A'].id}/external-dependencies", headers=e["h"]
    )
    assert r.json() == {"entrantes": [], "salientes": []}
