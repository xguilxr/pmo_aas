"""US-221 — El plan de suscripción del inquilino: límites y consumo.

Del artboard «Admin — Plan (suscripción)», con la línea que manda sobre todo lo
demás: **«Solo lectura — sin paywall ni billing en esta fase»**.

## Nada de aquí bloquea nada

Un límite excedido se muestra y se sigue trabajando. Convertirlo en un bloqueo
sería cambiar el producto por cuenta propia, y dejaría a un cliente cuya cartera
creció fuera de su propia plataforma un viernes por la tarde. Cuando el bloqueo
llegue, la respuesta ya está calculada y solo hará falta decidir qué hacer con
ella — que no es una decisión técnica.

## Quién ve y quién escribe

**Ver** es del administrador del inquilino: es su plan y su consumo. **Escribir**
es del superadministrador, porque el tier y sus topes son parte del contrato
comercial: un inquilino que pudiera subirse el propio límite tendría un plan
decorativo.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_superadmin, require_authenticated
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.dominio.plan import (
    CLAVES,
    ETIQUETAS,
    ETIQUETAS_DE_ESTADO,
    RECURSOS,
    TIERS,
    Tier,
    normalizar_limites,
)
from app.models.tenant import Tenant
from app.services.plan_suscripcion import estado_del_plan, guardar_plan

router = APIRouter(tags=["plan"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return UUID(str(cu.effective_tenant_id))


@router.get("/admin/plan")
async def read_plan(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """US-221 — el plan del inquilino activo y lo que consume.

    Trae los rótulos junto a los datos —el nombre del tier, la etiqueta de cada
    estado, la consecuencia de pasarse— porque son parte del vocabulario del
    dominio: escribirlos en el frontend los deja divergiendo en cuanto se añade
    un recurso o se renombra un tier.
    """
    tenant_id = _tenant(cu)
    estado = await estado_del_plan(db, tenant_id)
    return {
        **estado,
        "tier_label": ETIQUETAS[str(estado["tier"])],
        "state_labels": ETIQUETAS_DE_ESTADO,
        "consequences": {r.clave: r.consecuencia for r in RECURSOS},
        # El artboard lo dice en la pantalla, y el contrato también: quien consuma
        # esto no debería tener que leer la documentación para saber que no bloquea.
        "note": (
            "Solo lectura: los límites se informan y no se hacen cumplir. Un "
            "recurso por encima del plan sigue funcionando."
        ),
    }


class PlanBody(BaseModel):
    """Lo que el superadministrador puede fijar.

    `limits` admite `null` por clave para **quitar** el tope: sin eso no habría
    forma de volver a «sin límite declarado», y un plan sin marcha atrás obliga a
    editar el JSON a mano.
    """

    tier: Tier | None = None
    limits: dict[str, int | None] | None = Field(default=None)


@router.put("/superadmin/tenants/{tenant_id}/plan")
async def set_plan(
    tenant_id: UUID,
    body: PlanBody,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """US-221 — fija el tier y los topes de un inquilino.

    Los tres nombres de tier salen del artboard aprobado; los **números** de cada
    uno no están en ningún documento de este repositorio, así que no hay catálogo
    que aplicar: los topes se capturan por inquilino. El día que exista un
    catálogo comercial, este endpoint lo rellena y el resto no cambia.

    Las claves que no correspondan a un recurso conocido se descartan en silencio.
    Rechazar la petición entera por una clave sobrante haría fallar una llamada
    que trae bien los cuatro topes que importan.
    """
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if tenant is None:
        raise not_found("Inquilino")
    limpios: dict[str, int | None] | None = None
    if body.limits is not None:
        # Un `None` explícito quita el tope; el resto pasa por la normalización
        # del dominio, que descarta lo que no es un entero utilizable.
        validos = normalizar_limites(
            {k: v for k, v in body.limits.items() if v is not None}
        )
        limpios = {
            k: (validos.get(k) if body.limits.get(k) is not None else None)
            for k in CLAVES
            if k in body.limits
        }
    guardar_plan(tenant, tier=body.tier, limites=limpios)
    await db.commit()
    return await estado_del_plan(db, tenant_id)


@router.get("/superadmin/plan-catalog")
async def plan_catalog(
    cu: CurrentUser = Depends(get_superadmin),
) -> dict[str, Any]:
    """US-221 — el vocabulario: qué tiers hay y qué recursos se cuentan.

    Alimenta el formulario del superadministrador. Se sirve desde el backend por
    lo mismo que el catálogo de columnas de la importación (US-216): el
    vocabulario vive en el dominio, y dos listas separadas divergen en cuanto se
    añade un recurso.
    """
    return {
        "tiers": [{"key": t, "label": ETIQUETAS[t]} for t in TIERS],
        "resources": [
            {"key": r.clave, "label": r.etiqueta, "consequence": r.consecuencia}
            for r in RECURSOS
        ],
    }
