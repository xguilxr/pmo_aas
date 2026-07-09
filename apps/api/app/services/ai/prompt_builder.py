"""ENH-189 — Composición de system prompts (menos hardcode, más sistema).

Arquitectura de prompts por capas (Revamp 1.0):

    system efectivo = base (catálogo prompts.py)
                    + instrucciones permanentes del TENANT
                      (tenants.settings.ai.instructions_md — admin)
    prompt de usuario = <CONTEXTO_DEL_PROYECTO> (US-185: memoria del
                      proyecto: contexto + instrucciones del PM + resumen)
                    + payload de la tarea (transcript / datos del reporte)

Los prompts base siguen versionados en código (services/ai/prompts.py) —
lo configurable son las capas de instrucciones tenant/proyecto, que no
requieren deploy.
"""
from __future__ import annotations

TENANT_INSTRUCTIONS_MAX_CHARS = 2000


def build_system_prompt(base: str, tenant_instructions: str | None) -> str:
    """Compone el system prompt efectivo: base + instrucciones del tenant.

    Las instrucciones del tenant NO pueden anular el contrato de salida
    (formato JSON/HTML) del prompt base — por eso se anexan con una regla
    explícita de precedencia.
    """
    instructions = (tenant_instructions or "").strip()
    if not instructions:
        return base
    if len(instructions) > TENANT_INSTRUCTIONS_MAX_CHARS:
        instructions = instructions[: TENANT_INSTRUCTIONS_MAX_CHARS - 1].rstrip() + "…"
    return (
        f"{base}\n\n"
        "<INSTRUCCIONES_DEL_TENANT>\n"
        "Instrucciones permanentes configuradas por el administrador. "
        "Aplícalas en el contenido y estilo, pero NUNCA cambies el formato "
        "de salida exigido arriba.\n"
        f"{instructions}\n"
        "</INSTRUCCIONES_DEL_TENANT>"
    )
