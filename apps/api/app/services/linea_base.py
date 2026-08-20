"""US-212 — Capturar y comparar líneas base del plan.

La regla vive en `app/dominio/linea_base.py` y no sabe de base de datos
(MCS DEV-02). Aquí se leen las dos fotos y se guardan.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio.linea_base import Comparacion, Fila, Resumen, comparar, resumir
from app.models.plan_baseline import PlanBaseline, PlanBaselineTask
from app.models.task import Task
from app.services.plan_metadata import wbs_sort_key


def _fila_de_tarea(t: Task) -> Fila:
    return Fila(
        task_id=str(t.id),
        wbs_code=t.wbs_code,
        nombre=t.name,
        inicio=t.start_date,
        fin=t.end_date,
        es_hito=t.is_milestone,
        progreso=t.progress,
        cerrada_el=t.closed_at,
    )


def _fila_de_base(b: PlanBaselineTask) -> Fila:
    return Fila(
        task_id=str(b.task_id),
        wbs_code=b.wbs_code,
        nombre=b.name,
        inicio=b.start_date,
        fin=b.end_date,
        es_hito=b.is_milestone,
    )


async def _tareas_del_proyecto(db: AsyncSession, tenant_id: UUID, project_id: UUID) -> list[Task]:
    filas = (
        await db.execute(
            select(Task).where(
                Task.tenant_id == str(tenant_id),
                Task.project_id == str(project_id),
            )
        )
    ).scalars().all()
    return sorted(filas, key=lambda t: wbs_sort_key(t.wbs_code))


async def capturar(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
    nombre: str,
    nota: str | None,
    usuario_id: UUID | None,
) -> PlanBaseline:
    """Copia el plan de hoy a una línea base nueva.

    No sustituye a la anterior: se apilan. Capturar es un acto con fecha y autor,
    y sobrescribir la última borraría la única prueba de que la promesa cambió.

    Un plan **vacío** se puede capturar. Parece un error y no lo es: capturar la
    línea base antes de cargar el plan es una secuencia legítima —el proyecto se
    aprueba y después se detalla—, y rechazarlo obligaría a inventar una tarea
    para poder guardar. Lo que la comparación dirá entonces es que todo el plan
    es alcance nuevo, que es exactamente lo que pasó.
    """
    tareas = await _tareas_del_proyecto(db, tenant_id, project_id)
    base = PlanBaseline(
        tenant_id=str(tenant_id),
        project_id=str(project_id),
        name=nombre,
        note=nota,
        captured_at=datetime.now(UTC),
        captured_by_user_id=str(usuario_id) if usuario_id else None,
        task_count=len(tareas),
    )
    db.add(base)
    await db.flush()
    for t in tareas:
        db.add(
            PlanBaselineTask(
                baseline_id=base.id,
                task_id=str(t.id),
                wbs_code=t.wbs_code,
                name=t.name,
                start_date=t.start_date,
                end_date=t.end_date,
                duration_days=t.duration_days,
                is_milestone=t.is_milestone,
            )
        )
    await db.flush()
    return base


async def listar(db: AsyncSession, *, tenant_id: UUID, project_id: UUID) -> list[PlanBaseline]:
    """Las líneas base del proyecto, la más reciente primero."""
    return list(
        (
            await db.execute(
                select(PlanBaseline)
                .where(
                    PlanBaseline.tenant_id == str(tenant_id),
                    PlanBaseline.project_id == str(project_id),
                )
                .order_by(PlanBaseline.captured_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def vigente(
    db: AsyncSession, *, tenant_id: UUID, project_id: UUID
) -> PlanBaseline | None:
    """La línea base más reciente, o `None` si el proyecto no tiene ninguna.

    `None` es una respuesta, no un fallo: la mayoría de los proyectos no tienen
    línea base hasta que alguien la captura, y quien pregunta tiene que poder
    decir «sin línea base» en vez de mostrar una desviación de cero (MCS DAT-12).
    """
    return (
        await db.execute(
            select(PlanBaseline)
            .where(
                PlanBaseline.tenant_id == str(tenant_id),
                PlanBaseline.project_id == str(project_id),
            )
            .order_by(PlanBaseline.captured_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def obtener(
    db: AsyncSession, *, tenant_id: UUID, baseline_id: UUID
) -> PlanBaseline | None:
    return (
        await db.execute(
            select(PlanBaseline).where(
                PlanBaseline.id == str(baseline_id),
                PlanBaseline.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()


async def comparar_con(
    db: AsyncSession, *, tenant_id: UUID, base: PlanBaseline
) -> tuple[list[Comparacion], Resumen]:
    """La comparación de una línea base contra el plan vivo de su proyecto."""
    filas_base = [
        _fila_de_base(b)
        for b in (
            await db.execute(
                select(PlanBaselineTask).where(PlanBaselineTask.baseline_id == base.id)
            )
        )
        .scalars()
        .all()
    ]
    filas_plan = [
        _fila_de_tarea(t)
        for t in await _tareas_del_proyecto(db, tenant_id, UUID(str(base.project_id)))
    ]
    comparaciones = comparar(filas_base, filas_plan)
    return comparaciones, resumir(filas_base, filas_plan, comparaciones)


async def borrar(db: AsyncSession, *, base: PlanBaseline) -> None:
    """Borra una línea base y sus filas.

    Las filas se borran a mano y no por `CASCADE` de la base de datos: en SQLite
    las claves ajenas no se hacen cumplir salvo que se active el pragma, así que
    confiar en el `ondelete` dejaría filas huérfanas en la suite y no en
    producción — la peor combinación posible, porque el problema solo aparece
    donde nadie lo prueba.
    """
    await db.execute(
        delete(PlanBaselineTask).where(PlanBaselineTask.baseline_id == base.id)
    )
    await db.delete(base)
    await db.flush()


async def cuantas(db: AsyncSession, *, tenant_id: UUID, project_id: UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(PlanBaseline)
                .where(
                    PlanBaseline.tenant_id == str(tenant_id),
                    PlanBaseline.project_id == str(project_id),
                )
            )
        ).scalar()
        or 0
    )
