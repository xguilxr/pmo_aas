"""US-224 (EP021) — catálogo de plantillas de operación: listar y ejecutar.

- ``GET  /ai/plantillas`` — el catálogo que este inquilino puede usar.
- ``POST /ai/plantillas/{id}/ejecutar`` — corre una plantilla sobre datos y
  devuelve el JSON del contrato.

El catálogo es **de solo lectura**: no hay ruta para crear, editar ni borrar
una plantilla, y no la habrá mientras la decisión de EP021 (pregunta 1) siga
siendo (b)+(c). Un prompt editable por el inquilino deja al conjunto de
evaluación midiendo otra cosa que la que corre.

**Todo lo que entra por `datos` es contenido no confiable** y viaja envuelto
como tal (MCS IA-11, AM-03): la mayor parte sale de campos que llenó un usuario
—descripciones de cambio, notas de cierre, nombres de tarea importados de un
`.mpp`— y una instrucción escondida ahí dentro no debe leerse como una orden de
la plataforma.

**Ninguna plantilla escribe.** La salida es una propuesta que una persona
confirma en la pantalla correspondiente, igual que el flujo minuta→RAID que ya
existe. Es la respuesta de EP021 a la pregunta 2, y es lo que impide que una
inyección se convierta en una escritura.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import AppError
from app.db.session import get_db
from app.services.ai import catalogo
from app.services.ai.json_parse import parse_json_lenient
from app.services.ai.platform_config import resolve_groq_config
from app.services.ai.prompt_builder import build_system_prompt
from app.services.ai.provider import generate_for_tenant
from app.services.ai.tenant_ai import load_tenant_ai
from app.services.ai.untrusted import envolver_no_confiable

router = APIRouter(prefix="/ai/plantillas", tags=["ai"])

# Tope del payload de datos. No es una defensa de seguridad —el modelo cobra
# por token y un plan de 4 000 tareas es un caso legítimo que hay que cortar
# antes de mandarlo, no después de pagarlo.
MAX_DATOS_CHARS = 60_000


class PlantillaRead(BaseModel):
    id: str
    nombre: str
    proposito: str
    categoria: str
    modo_minimo: str
    entradas: list[str]
    claves_salida: list[str]
    version: int


class EjecutarRequest(BaseModel):
    datos: dict[str, Any] = Field(
        ...,
        description="Los campos que la plantilla declara en `entradas`.",
    )


class EjecutarResponse(BaseModel):
    plantilla_id: str
    version: int
    resultado: dict[str, Any]


def _tenant(cu: CurrentUser) -> UUID:
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise AppError(403, "NO_TENANT", "La sesión no tiene inquilino activo")
    return tenant_id


@router.get("", response_model=list[PlantillaRead])
async def listar_plantillas(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> list[PlantillaRead]:
    """El catálogo filtrado por el modo de IA del inquilino.

    Con la IA deshabilitada devuelve una lista vacía y **no** un 409: la
    pantalla que la consume es un catálogo, y una lista vacía es una respuesta
    correcta a «qué puedo usar» cuando la respuesta es «nada».
    """
    cfg = await load_tenant_ai(db, _tenant(cu))
    return [
        PlantillaRead(**catalogo.plantilla_publica(p))
        for p in catalogo.listar(modo_tenant=cfg.mode)
    ]


@router.post("/{plantilla_id}/ejecutar", response_model=EjecutarResponse)
async def ejecutar_plantilla(
    plantilla_id: str,
    body: EjecutarRequest,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
) -> EjecutarResponse:
    tenant_id = _tenant(cu)
    plantilla = catalogo.obtener(plantilla_id)
    if plantilla is None:
        raise AppError(
            404, "PLANTILLA_NO_ENCONTRADA", f"No existe la plantilla {plantilla_id}"
        )

    cfg = await load_tenant_ai(db, tenant_id)
    if cfg.mode == "disabled":
        raise AppError(409, "AI_DISABLED", "La IA está deshabilitada en este tenant")
    if plantilla.modo_minimo == catalogo.MODO_BYO and cfg.mode != catalogo.MODO_BYO:
        # Mismo código que el resto de EP008: Groq de plataforma se limita a
        # minutas (DEC-017), y el cliente ya sabe interpretarlo.
        raise AppError(
            409,
            "AI_PLATFORM_SCOPE_LIMITED",
            f"«{plantilla.nombre}» necesita un proveedor propio (BYOK)",
            {"plantilla_id": plantilla.id, "modo_minimo": plantilla.modo_minimo},
        )

    faltantes = catalogo.validar_entradas(plantilla, body.datos)
    if faltantes:
        raise AppError(
            422,
            "ENTRADAS_FALTANTES",
            "Faltan datos que la plantilla necesita",
            {"faltantes": faltantes},
        )

    datos_texto = json.dumps(body.datos, ensure_ascii=False, default=str)
    if len(datos_texto) > MAX_DATOS_CHARS:
        raise AppError(
            413,
            "DATOS_DEMASIADO_GRANDES",
            "Los datos superan el tamaño que se puede enviar al modelo",
            {"chars": len(datos_texto), "maximo": MAX_DATOS_CHARS},
        )

    prompt = envolver_no_confiable(
        datos_texto, origen=f"datos de la plataforma para «{plantilla.nombre}»"
    )
    platform_cfg = (
        await resolve_groq_config(db) if cfg.mode == catalogo.MODO_PLATAFORMA else None
    )

    try:
        result = await generate_for_tenant(
            prompt,
            system=build_system_prompt(plantilla.sistema, cfg.instructions_md),
            tenant_ai_mode=cfg.mode,
            platform_groq_config=platform_cfg,
            byo_config=cfg.byo,
            tenant_id=str(tenant_id),
            json_mode=True,
        )
    except Exception as exc:
        raise AppError(
            502,
            "AI_PROVIDER_ERROR",
            "El proveedor IA falló al ejecutar la plantilla",
            {"error": str(exc)[:200]},
        ) from exc

    salida = parse_json_lenient(result.text or "")
    incumplidas = catalogo.validar_salida(plantilla, salida)
    if incumplidas:
        # Se falla en vez de devolver lo que llegó. Media respuesta con las
        # claves que sí vinieron se pinta en la pantalla como si estuviera
        # completa, y el hueco lo descubre quien firma el documento.
        raise AppError(
            502,
            "AI_CONTRATO_INCUMPLIDO",
            "El modelo no devolvió las claves que la plantilla declara",
            {"faltantes": incumplidas, "plantilla_id": plantilla.id},
        )

    assert salida is not None  # `validar_salida` ya lo garantizó
    return EjecutarResponse(
        plantilla_id=plantilla.id,
        version=plantilla.version,
        resultado=salida,
    )
