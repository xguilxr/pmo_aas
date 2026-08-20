"""US-215 — Congelar la tarifa de una asignación y derivar su costo.

La regla vive en `app/dominio/costo.py` y no sabe de base de datos (MCS DEV-02).
Aquí se busca la tarifa en el catálogo, se resuelve la moneda y se guarda.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio import moneda as dominio_moneda
from app.dominio.costo import costo_de_asignacion, costo_por_moneda, sin_tarifa
from app.models.area import Actor
from app.models.project import Project
from app.models.project_participation import ProjectParticipation
from app.services.moneda_tenant import preferida as moneda_preferida


async def _moneda_del_proyecto(
    db: AsyncSession, tenant_id: UUID, project_id: UUID
) -> str:
    """La moneda que rotula el costo: la del proyecto, o la preferida, o la default.

    Es la cascada de `dominio/moneda.resolver` (decisión del owner en BUG-092:
    la moneda va sobre el proyecto). Se resuelve **al congelar** y se guarda: si
    el proyecto cambia de moneda después, los costos ya congelados conservan la
    que tenían — cambiarlos convertiría importes sin tipo de cambio, que es
    inventar el número.
    """
    del_proyecto = (
        await db.execute(select(Project.currency).where(Project.id == str(project_id)))
    ).scalar_one_or_none()
    preferida = await moneda_preferida(db, tenant_id)
    return dominio_moneda.resolver(del_proyecto, preferida)


async def congelar(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    participacion: ProjectParticipation,
) -> bool:
    """Copia la tarifa del catálogo a la participación. `False` si no había qué copiar.

    Devuelve un booleano y no lanza: al **crear** una participación, que el actor
    no tenga tarifa capturada es lo normal y no puede impedir asignarlo a un
    proyecto. Quien llama decide si el «no se pudo» es un error (el endpoint
    explícito) o un dato (la creación).

    Hacen falta las **dos** cosas, tarifa y periodo. Con la tarifa sola el número
    no tiene unidad de tiempo, y congelarlo así dejaría un importe que parece
    utilizable y no lo es.
    """
    fila = (
        await db.execute(
            select(Actor.fte_cost_rate, Actor.cost_rate_period).where(
                Actor.id == str(participacion.actor_id),
                Actor.tenant_id == str(tenant_id),
            )
        )
    ).one_or_none()
    if fila is None:
        return False
    tarifa, periodo = fila
    if tarifa is None or not periodo:
        return False
    participacion.cost_rate_snapshot = Decimal(tarifa)
    participacion.cost_rate_period = periodo
    participacion.cost_currency = await _moneda_del_proyecto(
        db, tenant_id, UUID(str(participacion.project_id))
    )
    participacion.cost_rate_captured_at = datetime.now(UTC)
    return True


def costo(participacion: ProjectParticipation) -> Decimal | None:
    """El costo de una asignación con su tarifa congelada, o `None`.

    Derivado y no guardado. Un costo almacenado se queda viejo el día que alguien
    mueve las fechas o el % de dedicación por un camino que se olvidó de
    recalcularlo — es la misma razón por la que la completitud de US-210 se
    deriva.
    """
    return costo_de_asignacion(
        tarifa=participacion.cost_rate_snapshot,
        periodo=participacion.cost_rate_period,
        allocation_pct=participacion.allocation_pct,
        desde=participacion.start_date,
        hasta=participacion.end_date,
    )


def resumen_de_proyecto(
    participaciones: list[ProjectParticipation],
) -> dict[str, object]:
    """El costo de recursos de un proyecto, por moneda, con lo que falta declarado.

    Solo cuentan las asignaciones **activas**: una tentativa no es un compromiso
    de gasto y una cancelada no lo fue nunca. Es el mismo criterio que el motor
    de saturación de US-183, y usar dos criterios distintos para las mismas filas
    haría que el costo y la carga hablaran de conjuntos diferentes.

    `sin_tarifa` va **junto** al total y no en otra llamada: «$400.000 en
    recursos» con doce asignaciones sin tarifa es un presupuesto a medias
    presentado como completo, y separarlos permite mostrar uno sin el otro.
    """
    activas = [p for p in participaciones if p.status == "activa"]
    pares = [(p.cost_currency, costo(p)) for p in activas]
    por_moneda = costo_por_moneda(pares)
    return {
        "by_currency": {k: float(v) for k, v in por_moneda.items()},
        "assignments": len(activas),
        "without_rate": sin_tarifa(pares),
        # Con una sola moneda se puede pintar un número; con varias hay que
        # pintarlas todas y con ninguna no hay nada que pintar. Los tres casos son
        # distintos y quien consume tiene que verlos distintos.
        "single_currency": dominio_moneda.unica(por_moneda),
    }
