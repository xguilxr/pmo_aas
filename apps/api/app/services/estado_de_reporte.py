"""US-211 — El próximo hito y el estatus de reporte, en lote.

Las reglas viven en `app/dominio/reporte.py` y no saben de base de datos
(MCS DEV-02). Aquí se averigua lo que preguntan para **todos** los proyectos de
una vez: la vista maestra tiene veintitrés filas hoy y dos consultas por fila
son cuarenta y seis.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio.reporte import Hito, Reporte, evaluar_reporte, proximo_hito
from app.models.project import Project
from app.models.report_history import ReportHistory
from app.models.task import Task

#: Los estados de tarea que cuentan como «el hito ya pasó». Escritos aquí y no
#: como una comparación suelta: la lista de estados de `Task` puede crecer, y un
#: `!= "completed"` se queda mudo el día que aparezca «cancelada».
_ESTADOS_CERRADOS: frozenset[str] = frozenset({"completed", "cancelled"})


async def _ultimo_reporte_por_proyecto(
    db: AsyncSession, project_ids: list[str]
) -> dict[str, date]:
    """`project_id → fecha del último reporte generado`.

    Un `MAX` agrupado y no una fila por proyecto: lo único que la regla necesita
    es la fecha más reciente, y traer el reporte entero para leerle un campo es
    cargar ficheros y tamaños que nadie va a mirar.
    """
    if not project_ids:
        return {}
    filas = (
        await db.execute(
            select(ReportHistory.project_id, func.max(ReportHistory.generated_at))
            .where(ReportHistory.project_id.in_(project_ids))
            .group_by(ReportHistory.project_id)
        )
    ).all()
    salida: dict[str, date] = {}
    for pid, cuando in filas:
        if cuando is None:
            continue
        # `generated_at` es un instante con zona; la cadencia se cuenta en días,
        # así que se compara por fecha. Guardar la hora aquí llevaría a que un
        # reporte de las 23:50 y otro de las 00:10 del día siguiente parezcan
        # separados por un día entero cuando son veinte minutos.
        salida[str(pid)] = cuando.date() if hasattr(cuando, "date") else cuando
    return salida


async def _hitos_abiertos_por_proyecto(
    db: AsyncSession, project_ids: list[str]
) -> dict[str, list[tuple[str, date]]]:
    """`project_id → [(nombre, fecha)]` de los hitos **abiertos** y con fecha.

    Un hito sin fecha no puede ser «el próximo» de nada: no hay contra qué
    ordenarlo. Se excluye en la consulta y no después, para no traer filas que
    se van a descartar.
    """
    if not project_ids:
        return {}
    filas = (
        await db.execute(
            select(Task.project_id, Task.name, Task.end_date).where(
                Task.project_id.in_(project_ids),
                Task.is_milestone.is_(True),
                Task.end_date.is_not(None),
                Task.status.notin_(tuple(_ESTADOS_CERRADOS)),
            )
        )
    ).all()
    salida: dict[str, list[tuple[str, date]]] = {}
    for pid, nombre, fecha in filas:
        salida.setdefault(str(pid), []).append((nombre, fecha))
    return salida


async def estado_de_reporte_de(
    db: AsyncSession,
    proyectos: list[Project],
    *,
    cadencia_dias: int,
    hoy: date | None = None,
) -> dict[str, tuple[Reporte, Hito | None]]:
    """`project_id → (estatus de reporte, próximo hito o None)`.

    Dos consultas agrupadas para toda la lista. `hoy` se inyecta para que los
    tests no dependan del día en que corren; en producción es la fecha de hoy.
    """
    if not proyectos:
        return {}
    hoy = hoy or date.today()
    ids = [str(p.id) for p in proyectos]

    ultimos = await _ultimo_reporte_por_proyecto(db, ids)
    hitos = await _hitos_abiertos_por_proyecto(db, ids)

    return {
        pid: (
            evaluar_reporte(ultimos.get(pid), hoy=hoy, cadencia_dias=cadencia_dias),
            proximo_hito(hitos.get(pid, []), hoy=hoy),
        )
        for pid in ids
    }


def a_json(reporte: Reporte, hito: Hito | None) -> dict[str, object]:
    """Las dos columnas, en la forma que viaja por la API.

    La etiqueta va resuelta desde el servidor porque el vocabulario de estados
    («al día», «por vencer») es del dominio y no de la pantalla: tres
    superficies lo muestran —tabla, board y resumen del proyecto— y un
    diccionario por superficie son tres copias que se desincronizan.
    """
    return {
        "report_status": reporte.estado,
        "report_status_label": reporte.etiqueta,
        "report_due_date": reporte.vence.isoformat() if reporte.vence else None,
        "report_days_late": reporte.dias_de_retraso,
        "next_milestone": (
            {
                "name": hito.nombre,
                "date": hito.fecha.isoformat(),
                "overdue": hito.vencido,
            }
            if hito
            else None
        ),
    }
