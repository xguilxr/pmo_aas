"""US-127 — Chat IA conversacional del Report Builder (EP020).

Endpoint sincrónico que recibe el canvas actual + un mensaje del PM
y devuelve `{message, actions}` donde `actions` es una lista JSON con
operaciones que el frontend aplica al canvas:

    [{"type": "add_section", "code": "S-09"},
     {"type": "remove_section", "index": 2},
     {"type": "update_section_params", "index": 0, "params": {...}},
     {"type": "reorder_section", "from": 1, "to": 3}]

El modelo recibe el catálogo + el canvas actual y se le pide que
proponga acciones con formato JSON estricto. Reusa la cascada
EP008 (`generate_for_tenant`) → si el tenant está en `platform` usa
Groq, si está en `byo` usa el provider configurado. Si está
`disabled`, devuelve 409.

Cada acción es revertible por el PM (el frontend mantiene el
historial y permite Undo). Reusamos el patrón "JSON-action" en
lugar de tool calling nativo del provider para no requerir refactor
de la cascada IA en v1.0.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import AppError, forbidden
from app.db.session import get_db
from app.models.report_section import ReportSection
from app.services.ai.platform_config import resolve_groq_config
from app.services.ai.provider import generate_for_tenant
from app.services.ai.tenant_ai import load_tenant_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report-builder", tags=["report_builder"])


ALLOWED_ACTION_TYPES = (
    "add_section",
    "remove_section",
    "update_section_params",
    "reorder_section",
    "no_op",
)


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=2000)
    canvas_codes: list[str] = Field(default_factory=list)
    composition_mode: str = Field(default="A", pattern="^(A|B)$")
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatAction(BaseModel):
    type: str
    code: str | None = None
    index: int | None = None
    to: int | None = None
    params: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    message: str
    actions: list[ChatAction] = Field(default_factory=list)
    raw_output: str | None = None


def _format_catalog(sections: list[ReportSection]) -> str:
    lines = []
    for s in sections:
        if not s.enabled:
            continue
        lines.append(f"- {s.code} ({s.category}): {s.name}")
    return "\n".join(lines)


SYSTEM_PROMPT = """Eres un asistente del Report Builder de un PMO.
El usuario quiere construir un reporte combinando "secciones atómicas"
de un catálogo cerrado. Tu trabajo es proponer ACCIONES sobre el
canvas (no reescribir el reporte).

Devuelves ÚNICAMENTE JSON válido en este formato:
{
  "message": "<respuesta corta en español al usuario>",
  "actions": [
    {"type": "add_section", "code": "S-09"},
    {"type": "remove_section", "index": 2},
    {"type": "update_section_params", "index": 0, "params": {"top_n": 5}},
    {"type": "reorder_section", "from": 1, "to": 3}
  ]
}

Reglas:
- `code` debe ser un id válido del catálogo (lo encuentras abajo).
- Índices `index`, `from`, `to` son 0-based sobre el canvas actual.
- Si la petición no requiere cambios, devuelve `actions: []`.
- NO inventes códigos que no estén en el catálogo.
- NO escribas texto fuera del JSON.
"""


def _parse_response(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extrae el JSON de la respuesta del modelo (ENH-147: usa el parser
    tolerante compartido — fence-strip, comas colgantes, recorte entre
    llaves — para no perder acciones cuando el modelo envuelve en fences)."""
    from app.services.ai.json_parse import parse_json_lenient

    data = parse_json_lenient(text)
    if data is None:
        return text.strip()[:500], []
    msg = str(data.get("message", "")).strip()
    raw_actions = data.get("actions") or []
    if not isinstance(raw_actions, list):
        return msg, []
    validated: list[dict[str, Any]] = []
    for a in raw_actions:
        if not isinstance(a, dict):
            continue
        atype = str(a.get("type") or "")
        if atype not in ALLOWED_ACTION_TYPES:
            continue
        validated.append(a)
    return msg or "Acción procesada.", validated


@router.post("/ai-chat", response_model=ChatResponse)
async def chat_with_builder(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
) -> ChatResponse:
    """US-127 — chat conversacional + tool-call style."""
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise forbidden("Sin tenant activo")

    cfg = await load_tenant_ai(db, tenant_id)
    if cfg.mode == "disabled":
        raise AppError(
            409,
            "AI_DISABLED",
            "La IA está deshabilitada en este tenant",
        )

    # Catálogo para anclar el prompt.
    sections = (
        await db.execute(
            select(ReportSection).where(ReportSection.enabled.is_(True))
        )
    ).scalars().all()
    catalog_text = _format_catalog(sections)

    canvas_repr = (
        "\n".join([f"{i}: {c}" for i, c in enumerate(payload.canvas_codes)])
        or "(canvas vacío)"
    )
    history_repr = "\n".join(
        [f"{m.role}: {m.content[:500]}" for m in payload.history[-10:]]
    )

    full_prompt = (
        f"Catálogo disponible:\n{catalog_text}\n\n"
        f"Canvas actual (modo {payload.composition_mode}):\n{canvas_repr}\n\n"
        + (f"Historial reciente:\n{history_repr}\n\n" if history_repr else "")
        + f"Usuario: {payload.user_message}\n\n"
        "Responde SOLO con JSON válido siguiendo el formato indicado."
    )

    platform_cfg = (
        await resolve_groq_config(db) if cfg.mode == "platform" else None
    )

    try:
        result = await generate_for_tenant(
            full_prompt,
            system=SYSTEM_PROMPT,
            tenant_ai_mode=cfg.mode,
            platform_groq_config=platform_cfg,
            byo_config=cfg.byo,
            tenant_id=str(tenant_id),
            json_mode=True,
        )
    except Exception as exc:
        logger.exception("ai-chat generate_for_tenant failed: %s", exc)
        raise AppError(
            502,
            "AI_PROVIDER_ERROR",
            "El proveedor IA falló al generar la respuesta",
            {"error": str(exc)[:200]},
        ) from exc

    text = result.text or ""
    message, actions = _parse_response(text)
    return ChatResponse(
        message=message,
        actions=[ChatAction(**a) for a in actions],
        raw_output=text,
    )
