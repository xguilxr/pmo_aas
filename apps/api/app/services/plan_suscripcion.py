"""US-221 — El plan de un inquilino y su consumo real.

La regla vive en `app/dominio/plan.py` y no sabe de base de datos (MCS DEV-02).
Aquí se leen los límites de `tenants.settings` y se cuenta lo que hay.

## Por qué los límites van en `settings` y no en columnas

Es configuración del inquilino, como la moneda preferida, el modo de IA y la
cadencia de reporte — que ya viven ahí. Cuatro columnas nuevas para lo mismo
obligarían a una migración por cada límite que se añada, y los límites de un plan
comercial son justo lo que cambia.

## El consumo se cuenta, no se guarda

Un contador almacenado se desincroniza el día que alguien borra un proyecto por
un camino que se olvidó de decrementarlo, y entonces el plan dice que el inquilino
está en el tope cuando no lo está. Es la misma razón por la que la completitud
(US-210) y el costo (US-215) se derivan.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio.plan import (
    Tier,
    Uso,
    evaluar,
    hay_algo_fuera,
    normalizar_limites,
    normalizar_tier,
)
from app.models.ai import AIJob
from app.models.organization import Organization
from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User

#: La clave de `tenants.settings` donde vive todo esto.
BLOQUE = "plan"


def _bloque(tenant: Tenant | None) -> dict[str, object]:
    ajustes = (tenant.settings if tenant else None) or {}
    bloque = ajustes.get(BLOQUE)
    return bloque if isinstance(bloque, dict) else {}


def tier_de(tenant: Tenant | None) -> Tier:
    return normalizar_tier(_bloque(tenant).get("tier"))


def limites_de(tenant: Tenant | None) -> dict[str, int | None]:
    return normalizar_limites(_bloque(tenant).get("limits"))


def _inicio_del_mes(hoy: date) -> datetime:
    """El primer instante del mes en curso, en UTC.

    El consumo de IA se cuenta por **mes calendario** y no por ventana de treinta
    días: es lo que dice el artboard y lo que espera quien lee una factura. Una
    ventana móvil daría un número que baja sin que nadie haya hecho nada.
    """
    return datetime(hoy.year, hoy.month, 1, tzinfo=UTC)


async def consumo_de(
    db: AsyncSession, tenant_id: UUID, *, hoy: date | None = None
) -> dict[str, int]:
    """Cuánto usa este inquilino, ahora mismo.

    Cuatro consultas de conteo y no una por recurso en un bucle: son cuatro
    tablas distintas y no hay forma de juntarlas sin un producto cartesiano.

    `hoy` se inyecta para que el corte del mes sea comprobable sin esperar al día
    1. Por defecto es la fecha del sistema.
    """
    hoy = hoy or datetime.now(UTC).date()

    async def contar(modelo: Any, *extra: Any) -> int:
        return int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(modelo)
                    .where(modelo.tenant_id == str(tenant_id), *extra)
                )
            ).scalar()
            or 0
        )

    return {
        # Las organizaciones inactivas no cuentan: no aparecen en ningún selector
        # y cobrar por ellas sería cobrar por algo que no se puede usar.
        "organizations": await contar(Organization, Organization.is_active.is_(True)),
        # Los proyectos borrados tampoco. Un proyecto en papelera no consume.
        "projects": await contar(Project, Project.deleted_at.is_(None)),
        # Usuarios **activos**: desactivar una cuenta libera su lugar, que es lo
        # que espera quien desactiva para dar de alta a otra persona.
        "users": await contar(User, User.is_active.is_(True)),
        "ai_jobs_month": await contar(
            AIJob, AIJob.created_at >= _inicio_del_mes(hoy)
        ),
    }


async def estado_del_plan(
    db: AsyncSession, tenant_id: UUID, *, hoy: date | None = None
) -> dict[str, object]:
    """El plan y su consumo, listos para pintar.

    **No bloquea nada.** El artboard es explícito: «solo lectura — sin paywall ni
    billing en esta fase». Un límite excedido se muestra y se sigue trabajando;
    convertirlo en un bloqueo dejaría a un cliente cuya cartera creció fuera de su
    propia plataforma un viernes por la tarde.
    """
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    limites = limites_de(tenant)
    consumo = await consumo_de(db, tenant_id, hoy=hoy)
    usos: list[Uso] = evaluar(consumo, limites)
    return {
        "tier": tier_de(tenant),
        "enforced": False,
        "usage": [
            {
                "key": u.clave,
                "label": u.etiqueta,
                "used": u.consumo,
                "limit": u.limite,
                "state": u.estado,
                "percent": u.porcentaje,
            }
            for u in usos
        ],
        "over_limit": hay_algo_fuera(usos),
        # Cuántos recursos no tienen tope declarado. Va aparte porque «todo dentro
        # del plan» con cuatro límites sin declarar no significa nada, y quien lo
        # lee tiene que poder distinguir las dos situaciones.
        "undeclared_limits": sum(1 for u in usos if u.limite is None),
    }


def guardar_plan(
    tenant: Tenant, *, tier: str | None, limites: dict[str, int | None] | None
) -> None:
    """Escribe el plan en `settings`, dejando el resto de los ajustes intacto.

    Se reasigna el diccionario completo en vez de mutarlo en sitio: SQLAlchemy no
    detecta la mutación de un JSON y el cambio se perdería sin dar error, que es
    la peor forma de perderse.
    """
    ajustes = dict(tenant.settings or {})
    bloque = dict(ajustes.get(BLOQUE) or {})
    if tier is not None:
        bloque["tier"] = normalizar_tier(tier)
    if limites is not None:
        bloque["limits"] = {k: v for k, v in limites.items() if v is not None}
    ajustes[BLOQUE] = bloque
    tenant.settings = ajustes
