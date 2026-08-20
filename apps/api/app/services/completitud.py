"""US-210 — Los hechos que la completitud necesita, en lote.

La regla vive en `app/dominio/completitud.py` y no sabe de base de datos
(MCS DEV-02). Aquí se averigua lo que pregunta, y se averigua **en lote**: la
vista maestra tiene veintitrés filas hoy y ninguna razón para no tener
doscientas, y tres consultas por fila son seiscientas consultas.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio.completitud import Completitud, evaluar
from app.models.project import Project


def _hechos_del_registro(p: Project) -> dict[str, bool]:
    """Los requisitos que se leen del propio proyecto, sin consultar nada más.

    `budget` se compara contra `None` y **no** por verdad: un presupuesto
    declarado de cero es un dato capturado —un proyecto sin costo— y tratarlo
    como ausente diría que falta algo que sí está. Lo mismo con `priority`, que
    no tiene el valor cero pero seguiría la misma regla si lo tuviera.

    `sponsor` es texto libre, así que la cadena vacía y los espacios cuentan
    como ausente: «capturado con nada» no es capturado.
    """
    return {
        "type": bool(p.type),
        "priority": p.priority is not None,
        "portfolio_id": p.portfolio_id is not None,
        "pm_id": p.pm_id is not None,
        "sponsor": bool((p.sponsor or "").strip()),
        "start_date": p.start_date is not None,
        "end_date": p.end_date is not None,
        "budget": p.budget is not None,
    }


async def _ids_con_filas(
    db: AsyncSession, modelo: Any, project_ids: list[str]
) -> set[str]:
    """Los proyectos de la lista que tienen al menos una fila en `modelo`.

    Un `GROUP BY` y no un `COUNT` por proyecto: la pregunta es «¿hay alguna?»,
    así que el conteo exacto sobra y traerlo cuesta lo mismo que no traerlo.
    """
    if not project_ids:
        return set()
    filas = (
        await db.execute(
            select(modelo.project_id)
            .where(modelo.project_id.in_(project_ids))
            .group_by(modelo.project_id)
        )
    ).scalars().all()
    return {str(i) for i in filas}


async def completitud_de(
    db: AsyncSession, proyectos: list[Project]
) -> dict[str, Completitud]:
    """`project_id → Completitud` para todos los proyectos de una vez.

    Tres consultas agrupadas —acta, actividades y participaciones— más lo que ya
    viene en la fila del proyecto. Con la lista vacía no consulta nada: es el
    caso de una cartera recién creada, y tres consultas con `IN ()` es trabajo
    para no encontrar nada.
    """
    if not proyectos:
        return {}

    ids = [str(p.id) for p in proyectos]

    # Importes locales: los tres modelos son de epics distintos (EP005, EP006,
    # EP017) y este servicio no tiene por qué acoplar su carga a la de ellos.
    from app.models.project_charter import ProjectCharter
    from app.models.project_participation import ProjectParticipation
    from app.models.task import Task

    con_acta = await _ids_con_filas(db, ProjectCharter, ids)
    con_plan = await _ids_con_filas(db, Task, ids)
    con_recursos = await _ids_con_filas(db, ProjectParticipation, ids)

    salida: dict[str, Completitud] = {}
    for p in proyectos:
        pid = str(p.id)
        hechos = _hechos_del_registro(p)
        hechos["charter"] = pid in con_acta
        hechos["plan"] = pid in con_plan
        hechos["recursos"] = pid in con_recursos
        salida[pid] = evaluar(hechos)
    return salida


async def completitud_de_uno(
    db: AsyncSession, tenant_id: UUID | str, project_id: UUID | str
) -> Completitud | None:
    """La completitud de un proyecto, o `None` si no existe en el inquilino."""
    proyecto = (
        await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.tenant_id == str(tenant_id),
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if proyecto is None:
        return None
    return (await completitud_de(db, [proyecto])).get(str(project_id))


def a_json(c: Completitud) -> dict[str, Any]:
    """La forma que viaja por la API.

    Los faltantes van con su etiqueta y su porqué, no solo con la clave: el
    checklist se pinta en tres superficies —vista maestra, resumen del proyecto e
    importación— y traducir once claves a español en cada una es tres copias del
    mismo diccionario esperando a desincronizarse.
    """
    return {
        "pct": c.pct,
        "presentes": c.presentes,
        "total": c.total,
        "faltantes": [
            {
                "clave": f.clave,
                "etiqueta": f.etiqueta,
                "grupo": f.grupo,
                "porque": f.porque,
            }
            for f in c.faltantes
        ],
    }
