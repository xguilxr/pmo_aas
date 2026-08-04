"""ENH-053 — sugerencia de mapeo de columnas para el wizard US-070.

Estrategia:
1. **Heurística siempre.** Match case-insensitive de cada header contra
   un diccionario de sinónimos por system field. Confianza fija por
   match (1.0 exact, 0.8 substring).
2. **AI (si tenant `ai_mode != disabled`).** Usa `generate_for_tenant`
   con un prompt JSON estricto pidiendo `{header: {field, confidence}}`.
   El resultado se merge sobre la heurística — la AI gana sólo si
   devuelve confidence ≥ 0.7.

Salida:
    {
      "<header original>": {
        "field": "name|wbs|...|null",
        "confidence": 0.0..1.0,
        "source": "ai|heuristic|none"
      },
      ...
    }
"""
from __future__ import annotations

import json
from typing import TypedDict

from app.services.ai.prompt_builder import build_system_prompt
from app.services.ai.provider import generate_for_tenant
from app.services.ai.tenant_ai import TenantAIConfig
from app.services.ai.untrusted import envolver_no_confiable

SYSTEM_FIELDS: tuple[str, ...] = (
    "name",
    "wbs",
    "start_date",
    "end_date",
    "duration_days",
    "progress",
    "is_milestone",
    # ENH-191: estado de la tarea.
    "status",
    # US-096.
    "criticality",
    # ENH-097: boolean explicito de criticidad.
    "is_critical",
    "related_milestone",
    "predecessors",
    # ENH-134: área responsable (se resuelve a area_id al importar).
    "area",
    "resources",
)

# Sinónimos por field. Match case-insensitive contra el header.
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "name": ("tarea", "task", "title", "nombre", "actividad", "name"),
    "wbs": ("wbs", "edt", "code", "código", "id"),
    "start_date": (
        "inicio", "start", "comienza", "fecha inicio", "start date",
    ),
    "end_date": ("fin", "end", "finaliza", "fecha fin", "end date", "due"),
    "duration_days": (
        "duración", "duracion", "duration", "días", "dias", "days",
    ),
    "progress": ("avance", "progreso", "progress", "%", "percent", "porcentaje"),
    "is_milestone": ("hito", "milestone", "es hito"),
    # ENH-191.
    "status": ("estado", "status", "estatus", "state"),
    # ENH-134: "Criticidad" (Sí/No) → is_critical booleano.
    "criticality": ("prioridad criticidad",),
    "is_critical": (
        "criticidad", "criticality", "is_critical",
        "es critico", "es crítico", "critico", "crítico",
    ),
    "related_milestone": (
        "hito relacionado", "related milestone", "milestone relacionado",
    ),
    "predecessors": ("predecesor", "predecesoras", "predecessor", "pred"),
    "area": ("área responsable", "area responsable", "área", "area"),
    "resources": (
        "recurso", "recursos", "resource", "asignado", "owner",
        "responsable", "owner_id",
    ),
}

_AI_SYSTEM_PROMPT = (
    "You are a column mapping assistant for a project management import "
    "wizard. Map each provided header to one of these system fields: "
    f"{', '.join(SYSTEM_FIELDS)}. When sample rows are provided, use the "
    "VALUES to decide (a column full of '45%' is progress even if its "
    "header is cryptic; dates → start/end by ordering; 'En curso' → "
    "status). Reply ONLY with strict JSON of shape "
    '{"<header>": {"field": "<one of the system fields or null>", '
    '"confidence": <number 0..1>}}. Do not include any prose.'
)


class Suggestion(TypedDict):
    field: str | None
    confidence: float
    source: str  # "ai" | "heuristic" | "none"


def heuristic_suggestion(header: str) -> Suggestion:
    h = (header or "").strip().lower()
    if not h:
        return {"field": None, "confidence": 0.0, "source": "none"}
    # Exact match a uno de los sinónimos.
    for field, syns in _SYNONYMS.items():
        if h in syns:
            return {"field": field, "confidence": 1.0, "source": "heuristic"}
    # Substring match.
    best_field: str | None = None
    best_conf = 0.0
    for field, syns in _SYNONYMS.items():
        for s in syns:
            if s in h or h in s:
                conf = 0.8 if len(s) >= 3 else 0.6
                if conf > best_conf:
                    best_field = field
                    best_conf = conf
    if best_field is None:
        return {"field": None, "confidence": 0.0, "source": "none"}
    return {"field": best_field, "confidence": best_conf, "source": "heuristic"}


async def suggest_column_mapping(
    headers: list[str],
    *,
    tenant_cfg: TenantAIConfig,
    platform_groq_config: dict | None = None,
    tenant_id: str | None = None,
    sample_rows: list[list[str | None]] | None = None,
) -> dict[str, Suggestion]:
    """Devuelve `{header: Suggestion}` con AI + heurística merged.

    US-188 nivel 1: `sample_rows` (hasta 5 filas de datos) se incluye
    en el prompt para que la IA decida por contenido, no solo por
    header — una columna '45%' es progress aunque el header sea
    críptico."""
    out: dict[str, Suggestion] = {h: heuristic_suggestion(h) for h in headers}

    if tenant_cfg.mode == "disabled" or not headers:
        return out

    # Llamada AI; si falla cae a heurística (no aborta el endpoint).
    try:
        payload: dict = {"headers": headers}
        if sample_rows:
            payload["sample_rows"] = [
                [None if c is None else str(c)[:120] for c in r[:30]]
                for r in sample_rows[:5]
            ]
        # B2 (MCS IA-11): las cabeceras y las filas de muestra salen de la
        # hoja de cálculo que subió el usuario. Es el mismo vector que las
        # minutas, con una consecuencia distinta: lo que el modelo devuelve
        # aquí decide a qué campo se mapea cada columna del plan importado.
        prompt = envolver_no_confiable(
            json.dumps(payload, ensure_ascii=False),
            origen="cabeceras y filas del archivo subido por el usuario",
        )
        res = await generate_for_tenant(
            prompt,
            system=build_system_prompt(_AI_SYSTEM_PROMPT, None),
            tenant_ai_mode=tenant_cfg.mode,
            platform_groq_config=platform_groq_config,
            byo_config=tenant_cfg.byo,
            tenant_id=tenant_id,
        )
        parsed = _safe_parse_ai_response(res.text)
    except Exception:
        return out

    for h, ai_sug in parsed.items():
        if h not in out:
            continue
        field = ai_sug.get("field")
        if field is not None and field not in SYSTEM_FIELDS:
            continue
        try:
            conf = float(ai_sug.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        # AI gana sólo si su confianza es alta.
        if conf >= 0.7 and conf > out[h]["confidence"]:
            out[h] = {"field": field, "confidence": conf, "source": "ai"}
    return out


def _safe_parse_ai_response(text: str) -> dict[str, dict]:
    """Extrae el JSON aunque el LLM lo envuelva en backticks o prosa."""
    s = (text or "").strip()
    if s.startswith("```"):
        # Remueve ```json ... ``` o similar.
        lines = s.splitlines()
        if lines:
            s = "\n".join(line for line in lines if not line.startswith("```"))
    # Trim a las llaves externas si hay prosa antes/después.
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        data = json.loads(s[start : end + 1])
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, dict)}
    except json.JSONDecodeError:
        pass
    return {}
