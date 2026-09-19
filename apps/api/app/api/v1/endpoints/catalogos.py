"""US-286 — la API de los catálogos de proyecto del inquilino.

Sobre `services/catalogos.py` (US-285). Dos catálogos: `tipo_proyecto` y
`fase_proyecto`.

## Por qué agregar una fase todavía no se puede

Se pueden renombrar, reordenar y desactivar las cinco que hay, pero no crear
una sexta. No es una omisión: una fase no es una etiqueta suelta. El endpoint
de cambio de fase valida contra `dominio/proyecto.py::TRANSICIONES`, los KPIs y
los cortes de snapshot leen `FASES_ACTIVAS`, y una fase nueva no estaría en
ninguno de los dos. Quedaría aceptada al crearla y atrapada al usarla —sin
transiciones de salida, invisible para los KPIs— y el síntoma no apuntaría a la
causa.

Las fases configurables de verdad, con su grafo derivado del orden, son US-289.
Hasta entonces el `POST` sobre `fase_proyecto` dice eso mismo en vez de
aceptarlo a medias.
"""
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_capability
from app.core.errors import business_rule, forbidden, mensaje
from app.db.session import get_db
from app.models.tenant_catalog import (
    CATALOGO_FASE_PROYECTO,
    CATALOGOS,
    TenantCatalogValue,
)
from app.services import catalogos as svc
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/catalogos", tags=["catalogos"])


def _tenant(cu: CurrentUser) -> UUID:
    """El inquilino que está mirando quien llama.

    Mismo caso que en `organizations.py`: un super admin sin inquilino activo
    no tiene catálogo que configurar, y dejarlo pasar escribiría en ninguna
    parte.
    """
    tid = cu.effective_tenant_id
    if tid is None:
        raise forbidden(
            detail=mensaje(
                que="Acción no disponible sin inquilino activo",
                porque="Los catálogos son de un inquilino y no hay ninguno elegido.",
                accion="Elige un inquilino en el selector y repite la acción.",
            )
        )
    # Los identificadores de este repo son UUID **como texto** (`String(36)`) y
    # los modelos los declaran `UUID`. El `cast` sostiene esa convención en un
    # sitio, en vez de repartir `str(...)` por cada llamada.
    return cast(UUID, tid)


class ValorRead(BaseModel):
    id: UUID
    catalogo: str
    clave: str
    etiqueta: str
    orden: int
    activo: bool
    datos: dict[str, object]


class ValorCreate(BaseModel):
    etiqueta: str = Field(min_length=1, max_length=120)
    #: Opcional: se deriva de la etiqueta. Se acepta explícita para poder
    #: reconstruir un valor con la clave exacta que ya tienen los proyectos.
    clave: str | None = Field(default=None, max_length=64)
    datos: dict[str, object] | None = None


class ValorUpdate(BaseModel):
    etiqueta: str | None = Field(default=None, min_length=1, max_length=120)
    activo: bool | None = None
    datos: dict[str, object] | None = None


class OrdenBody(BaseModel):
    #: Todas las claves del catálogo, en el orden deseado. Se pide la lista
    #: entera y no un «mover arriba»: con movimientos sueltos, dos pestañas
    #: abiertas dejan un orden que ninguna de las dos pidió.
    claves: list[str]


def _leer(v: TenantCatalogValue) -> ValorRead:
    return ValorRead(
        id=v.id,
        catalogo=v.catalogo,
        clave=v.clave,
        etiqueta=v.etiqueta,
        orden=v.orden,
        activo=v.activo,
        datos=dict(v.datos or {}),
    )


def _validar_catalogo(catalogo: str) -> None:
    if catalogo not in CATALOGOS:
        raise business_rule(
            mensaje(
                que=f"«{catalogo}» no es un catálogo de esta plataforma",
                porque="Solo se configuran los que el producto sabe interpretar.",
                accion=f"Usa uno de estos: {', '.join(CATALOGOS)}.",
            ),
            code="CATALOGO_DESCONOCIDO",
        )


@router.get("/{catalogo}", response_model=list[ValorRead])
async def listar_valores(
    catalogo: str,
    incluir_inactivos: bool = Query(default=False),
    cu: CurrentUser = Depends(require_capability("tenant.manage")),
    db: AsyncSession = Depends(get_db),
) -> list[ValorRead]:
    _validar_catalogo(catalogo)
    valores = await svc.listar(
        db, _tenant(cu), catalogo, incluir_inactivos=incluir_inactivos
    )
    return [_leer(v) for v in valores]


@router.post("/{catalogo}", response_model=ValorRead, status_code=201)
async def crear_valor(
    catalogo: str,
    body: ValorCreate,
    cu: CurrentUser = Depends(require_capability("tenant.manage")),
    db: AsyncSession = Depends(get_db),
) -> ValorRead:
    _validar_catalogo(catalogo)
    if catalogo == CATALOGO_FASE_PROYECTO:
        raise business_rule(
            mensaje(
                que="Todavía no se pueden agregar fases",
                porque=(
                    "Una fase nueva no tendría transiciones de salida ni "
                    "contaría en los KPIs: quedaría aceptada al crearla y "
                    "atrapada al usarla."
                ),
                accion=(
                    "Renombra, reordena o desactiva las que hay. Agregar fases "
                    "llega con su grafo de transiciones en US-289."
                ),
            ),
            code="FASE_NUEVA_NO_DISPONIBLE",
        )
    tenant_id = _tenant(cu)
    valor = await svc.crear(
        db,
        tenant_id,
        catalogo,
        etiqueta=body.etiqueta,
        clave=body.clave,
        datos=body.datos,
    )
    await write_audit(
        db,
        action="catalogo.valor.create",
        module="catalogos",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant_catalog_value",
        entity_id=str(valor.id),
        details={"catalogo": catalogo, "clave": valor.clave, "etiqueta": valor.etiqueta},
    )
    await db.commit()
    await db.refresh(valor)
    return _leer(valor)


@router.patch("/{catalogo}/{valor_id}", response_model=ValorRead)
async def editar_valor(
    catalogo: str,
    valor_id: UUID,
    body: ValorUpdate,
    cu: CurrentUser = Depends(require_capability("tenant.manage")),
    db: AsyncSession = Depends(get_db),
) -> ValorRead:
    """Cambia etiqueta, estado o metadatos. La clave **no** está en la lista.

    Renombrarla dejaría huérfano a cada `projects.type` que la tenga guardada, y
    desde aquí no hay forma de saber cuántos son.
    """
    _validar_catalogo(catalogo)
    tenant_id = _tenant(cu)
    valor = await svc.obtener(db, tenant_id, valor_id)
    if valor.catalogo != catalogo:
        raise business_rule(
            mensaje(
                que="Ese valor no pertenece a este catálogo",
                porque="La ruta y el valor tienen que hablar de lo mismo.",
                accion=f"Búscalo en «{valor.catalogo}».",
            )
        )
    antes = {"etiqueta": valor.etiqueta, "activo": valor.activo}
    await svc.editar(
        db, valor, etiqueta=body.etiqueta, activo=body.activo, datos=body.datos
    )
    await write_audit(
        db,
        action="catalogo.valor.update",
        module="catalogos",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant_catalog_value",
        entity_id=str(valor.id),
        details={
            "catalogo": catalogo,
            "clave": valor.clave,
            "antes": antes,
            "despues": {"etiqueta": valor.etiqueta, "activo": valor.activo},
        },
    )
    await db.commit()
    await db.refresh(valor)
    return _leer(valor)


@router.put("/{catalogo}/orden", response_model=list[ValorRead])
async def reordenar_valores(
    catalogo: str,
    body: OrdenBody,
    cu: CurrentUser = Depends(require_capability("tenant.manage")),
    db: AsyncSession = Depends(get_db),
) -> list[ValorRead]:
    _validar_catalogo(catalogo)
    tenant_id = _tenant(cu)
    valores = await svc.reordenar(db, tenant_id, catalogo, body.claves)
    await write_audit(
        db,
        action="catalogo.reorden",
        module="catalogos",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant_catalog_value",
        entity_id=None,
        details={"catalogo": catalogo, "orden": body.claves},
    )
    await db.commit()
    return [_leer(v) for v in valores]
