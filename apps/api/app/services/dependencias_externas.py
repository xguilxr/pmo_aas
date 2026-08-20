"""US-218 — Dependencias entre tareas de proyectos distintos.

El artboard «Proyecto — Plan» pide un Gantt con «dependencias inter-proyecto».
Dentro de un proyecto las dependencias ya existen: viven en `Task.predecessors`
como códigos WBS, con su propia detección de ciclos (US-090). Un código WBS no
sirve para cruzar proyectos —el `1.2` de uno no es el `1.2` de otro—, y para eso
está `task_dependencies`, que enlaza por identificador y que hasta ahora solo
llenaba el importador de MS Project.

**No hace falta migración**: la tabla ya podía guardar el enlace. Lo que faltaba
era la API, el guardarraíl y la forma de verlo.

## Por qué la validación de ciclos se hace a nivel de TAREA

La respuesta fácil sería mirarlo a nivel de proyecto: si A depende de B, prohibir
que B dependa de A. Es incorrecta y bloquearía un caso normal: «les entregamos el
ambiente en la fase 1 y ellos nos devuelven la certificación en la fase 3». Eso
es A→B y B→A a nivel de proyecto, y no hay ningún ciclo real — son dos cadenas
que no se tocan.

Lo que sí es un ciclo es un camino de tareas que vuelve a su origen, y para
verlo hay que recorrer **las dos** clases de arista: las de dentro del proyecto
(`predecessors`, por WBS) y las de fuera (`task_dependencies`, por id). Mirar
solo una deja pasar el ciclo que alterna entre ambas, que es el que un plan
grande produce sin que nadie lo vea venir.

## El recorrido y su coste

Se camina hacia adelante desde el sucesor propuesto buscando llegar al
predecesor. Las tareas se cargan por proyecto y **a demanda**: un plan de un
proyecto entra de golpe porque sus aristas internas están en sus propias filas,
y solo se abre otro proyecto si una arista externa lleva hasta él. En la práctica
eso son uno o dos proyectos, no el inquilino entero.

El conjunto de visitados garantiza que termina. No hay tope artificial: un tope
convertiría un ciclo real en un «no encontré ninguno», y aceptar la arista es
peor que tardar.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import mensaje, not_found, validation_error
from app.models.task import Task, TaskDependency

#: Los tipos de vínculo de MS Project. Se aceptan los cuatro porque el
#: importador ya los escribe y rechazarlos aquí haría que una dependencia
#: importada no se pudiera recrear a mano.
TIPOS = ("FS", "SS", "FF", "SF")


class _Grafo:
    """Las tareas necesarias para el recorrido, cargadas a demanda por proyecto.

    Guarda las tareas por identificador y por `(project_id, wbs_code)`, que son
    las dos formas en que una arista las nombra.
    """

    def __init__(self, db: AsyncSession, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._por_id: dict[str, Task] = {}
        self._por_wbs: dict[tuple[str, str], Task] = {}
        self._proyectos_cargados: set[str] = set()
        #: `predecessor_id → [successor_id]`, de las aristas externas.
        self._externas: dict[str, list[str]] = {}
        self._externas_cargadas = False

    async def cargar_proyecto(self, project_id: str) -> None:
        if project_id in self._proyectos_cargados:
            return
        self._proyectos_cargados.add(project_id)
        tareas = (
            await self._db.execute(
                select(Task).where(
                    Task.tenant_id == self._tenant_id,
                    Task.project_id == project_id,
                )
            )
        ).scalars().all()
        for t in tareas:
            self._por_id[str(t.id)] = t
            self._por_wbs[(str(t.project_id), str(t.wbs_code))] = t

    async def _cargar_externas(self) -> None:
        """Las aristas externas **del inquilino**, en una consulta.

        Se traen de golpe y no por tarea: son las pocas que alguien capturó a
        mano o importó, y una consulta por nodo visitado convertiría el recorrido
        en el problema que el recorrido viene a evitar.

        El `join` con la tarea predecesora no es opcional: `task_dependencies` no
        tiene `tenant_id` —enlaza por identificador— así que sin él la consulta
        trae las aristas de **todos** los inquilinos. El recorrido las
        descartaría al resolver el proyecto, pero antes las habría visitado, y un
        recorrido que pasa por datos de otro cliente es un recorrido que no se
        puede defender.
        """
        if self._externas_cargadas:
            return
        self._externas_cargadas = True
        filas = (
            await self._db.execute(
                select(TaskDependency.predecessor_id, TaskDependency.successor_id)
                .join(Task, Task.id == TaskDependency.predecessor_id)
                .where(Task.tenant_id == self._tenant_id)
            )
        ).all()
        for pre, suc in filas:
            self._externas.setdefault(str(pre), []).append(str(suc))

    async def sucesores(self, task_id: str) -> list[str]:
        """Los identificadores de las tareas que dependen de esta."""
        await self._cargar_externas()
        tarea = self._por_id.get(task_id)
        salida: list[str] = list(self._externas.get(task_id, []))
        if tarea is None:
            return salida
        # Aristas internas: las tareas del mismo proyecto que declaran a esta
        # como predecesora. `successors` es derivado en escritura (US-090) y se
        # usa tal cual; recalcularlo aquí sería una segunda fuente de verdad.
        for wbs in tarea.successors or []:
            vecina = self._por_wbs.get((str(tarea.project_id), str(wbs)))
            if vecina is not None:
                salida.append(str(vecina.id))
        return salida

    async def proyecto_de(self, task_id: str) -> str | None:
        """El proyecto de una tarea, consultándolo si no está cargada.

        Un nodo puede llegar por una arista externa a un proyecto que el
        recorrido no ha abierto todavía. Sin resolverlo aquí, sus aristas
        internas serían invisibles y el ciclo que las use pasaría.
        """
        cacheada = self._por_id.get(task_id)
        if cacheada is not None:
            return str(cacheada.project_id)
        pid = (
            await self._db.execute(
                select(Task.project_id).where(
                    Task.id == task_id, Task.tenant_id == self._tenant_id
                )
            )
        ).scalar_one_or_none()
        return str(pid) if pid else None


async def _hay_camino(
    grafo: _Grafo, desde: str, hasta: str
) -> bool:
    """`True` si siguiendo sucesores desde `desde` se llega a `hasta`."""
    pila = [desde]
    vistos: set[str] = set()
    while pila:
        actual = pila.pop()
        if actual == hasta:
            return True
        if actual in vistos:
            continue
        vistos.add(actual)
        # Abrir el proyecto de este nodo antes de pedirle sus vecinos: sin esto
        # las aristas internas del proyecto al que se acaba de saltar serían
        # invisibles y el ciclo que las use pasaría.
        proyecto = await grafo.proyecto_de(actual)
        if proyecto is None:
            # La tarea no existe o es de otro inquilino: la arista apunta a la
            # nada y no puede cerrar ningún ciclo.
            continue
        await grafo.cargar_proyecto(proyecto)
        pila.extend(await grafo.sucesores(actual))
    return False


async def crear_dependencia_externa(
    db: AsyncSession,
    tenant_id: UUID | str,
    *,
    predecessor_id: UUID | str,
    successor_id: UUID | str,
    tipo: str = "FS",
    lag_days: int = 0,
) -> TaskDependency:
    """Enlaza dos tareas de **proyectos distintos** del mismo inquilino."""
    tenant_id = str(tenant_id)
    pre_id, suc_id = str(predecessor_id), str(successor_id)

    if pre_id == suc_id:
        raise validation_error(
            mensaje(
                que="una tarea no puede depender de sí misma",
                porque="La dependencia no tendría orden posible.",
                accion="Elige dos tareas distintas.",
            )
        )
    if tipo not in TIPOS:
        raise validation_error(
            mensaje(
                que=f"tipo de vínculo inválido: {tipo}",
                porque="Solo existen los cuatro vínculos de un cronograma.",
                accion=f"Usa uno de {', '.join(TIPOS)}.",
            )
        )

    tareas = (
        await db.execute(
            select(Task).where(Task.id.in_([pre_id, suc_id]), Task.tenant_id == tenant_id)
        )
    ).scalars().all()
    por_id = {str(t.id): t for t in tareas}
    if pre_id not in por_id or suc_id not in por_id:
        # 404 y no 422: desde fuera no se distingue «no existe» de «es de otro
        # inquilino», y decirlo sería confirmar que existe.
        raise not_found("Tarea")

    pre, suc = por_id[pre_id], por_id[suc_id]
    if str(pre.project_id) == str(suc.project_id):
        raise validation_error(
            mensaje(
                que="las dos tareas son del mismo proyecto",
                porque="Dentro de un proyecto las dependencias van en el campo "
                "`predecessors` de la tarea, por código WBS. Tener dos "
                "mecanismos para lo mismo es cómo empiezan a discrepar.",
                accion="Usa la edición de la tarea para su predecesora interna.",
            )
        )

    ya = (
        await db.execute(
            select(TaskDependency).where(
                TaskDependency.predecessor_id == pre_id,
                TaskDependency.successor_id == suc_id,
            )
        )
    ).scalar_one_or_none()
    if ya is not None:
        # Idempotente: repetir la misma dependencia devuelve la que hay en vez
        # de un error. Quien la vuelve a pedir quiere que exista, y ya existe.
        return ya

    grafo = _Grafo(db, tenant_id)
    await grafo.cargar_proyecto(str(pre.project_id))
    await grafo.cargar_proyecto(str(suc.project_id))
    if await _hay_camino(grafo, suc_id, pre_id):
        raise validation_error(
            mensaje(
                que="la dependencia cerraría un ciclo",
                porque="Siguiendo las dependencias desde la tarea sucesora se "
                "llega otra vez a la predecesora, y un ciclo no tiene orden "
                "posible: el cronograma no se puede calcular.",
                accion="Rompe el camino quitando una de las dependencias "
                "intermedias, o invierte el sentido de esta.",
            )
        )

    dep = TaskDependency(
        predecessor_id=pre_id, successor_id=suc_id, type=tipo, lag_days=lag_days
    )
    db.add(dep)
    await db.flush()
    return dep


async def externas_de_proyecto(
    db: AsyncSession, tenant_id: UUID | str, project_id: UUID | str
) -> dict[str, list[dict[str, Any]]]:
    """Las dependencias externas de un proyecto, en las dos direcciones.

    Se devuelven separadas —`entrantes` y `salientes`— porque significan cosas
    distintas para quien mira el plan: una entrante es algo que **este** proyecto
    espera (y que puede retrasarlo), y una saliente es alguien esperándonos. Una
    lista sola obligaría a leer el sentido en cada fila.
    """
    tenant_id, project_id = str(tenant_id), str(project_id)
    mias = (
        await db.execute(
            select(Task.id).where(
                Task.tenant_id == tenant_id, Task.project_id == project_id
            )
        )
    ).scalars().all()
    ids = [str(i) for i in mias]
    if not ids:
        return {"entrantes": [], "salientes": []}

    # Aquí no hace falta el `join` por inquilino que sí necesita el recorrido:
    # `ids` son las tareas de **este** proyecto, ya filtradas por inquilino, y
    # una arista tiene que tocar una de ellas para entrar.
    filas = (
        await db.execute(
            select(TaskDependency).where(
                TaskDependency.predecessor_id.in_(ids)
                | TaskDependency.successor_id.in_(ids)
            )
        )
    ).scalars().all()
    if not filas:
        return {"entrantes": [], "salientes": []}

    # Los datos de las tareas del otro lado, en una consulta.
    from app.models.project import Project

    otros_ids = {
        str(d.predecessor_id) if str(d.successor_id) in ids else str(d.successor_id)
        for d in filas
    }
    otras = (
        await db.execute(select(Task).where(Task.id.in_(list(otros_ids | set(ids)))))
    ).scalars().all()
    tarea_por_id = {str(t.id): t for t in otras}
    proyectos = (
        await db.execute(
            select(Project.id, Project.folio, Project.name).where(
                Project.id.in_([str(t.project_id) for t in otras])
            )
        )
    ).all()
    proyecto_por_id = {str(i): (f, n) for i, f, n in proyectos}

    def ficha(task_id: str) -> dict[str, Any]:
        t = tarea_por_id.get(task_id)
        if t is None:
            return {"task_id": task_id}
        folio, nombre = proyecto_por_id.get(str(t.project_id), ("", ""))
        return {
            "task_id": task_id,
            "task_name": t.name,
            "wbs_code": t.wbs_code,
            "end_date": t.end_date.isoformat() if t.end_date else None,
            "status": t.status,
            "project_id": str(t.project_id),
            "project_folio": folio,
            "project_name": nombre,
        }

    entrantes, salientes = [], []
    propios = set(ids)
    for d in filas:
        pre, suc = str(d.predecessor_id), str(d.successor_id)
        registro = {
            "id": str(d.id),
            "type": d.type,
            "lag_days": d.lag_days,
            "predecessor": ficha(pre),
            "successor": ficha(suc),
        }
        # Una dependencia entre dos tareas propias es interna y no se lista aquí:
        # la trae `predecessors`. Solo llegan aquí las que el importador escribió.
        if pre in propios and suc in propios:
            continue
        if suc in propios:
            entrantes.append(registro)
        else:
            salientes.append(registro)
    return {"entrantes": entrantes, "salientes": salientes}
