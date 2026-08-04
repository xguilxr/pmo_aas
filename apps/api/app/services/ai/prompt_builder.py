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

B2 (MCS IA-11): esta función es el ÚNICO punto donde se compone un mensaje de
sistema, así que es donde se ancla la regla de contenido no confiable. Va la
última, después de las instrucciones del tenant, para que sea lo último que el
modelo lee antes de recibir el dato.
"""
from __future__ import annotations

from app.services.ai.untrusted import REGLA_CONTENIDO_NO_CONFIABLE, neutralizar

TENANT_INSTRUCTIONS_MAX_CHARS = 2000


def build_system_prompt(base: str, tenant_instructions: str | None) -> str:
    """Compone el system prompt efectivo: base + instrucciones del tenant +
    regla de contenido no confiable.

    Las instrucciones del tenant NO pueden anular el contrato de salida
    (formato JSON/HTML) del prompt base — por eso se anexan con una regla
    explícita de precedencia.

    La regla de contenido no confiable se anexa SIEMPRE, con o sin
    instrucciones del tenant. Antes esta función devolvía `base` intacto
    cuando no había instrucciones; ahora nunca lo hace, y es deliberado: el
    prompt de sistema sin la regla deja el bloque `<CONTENIDO_NO_CONFIABLE>`
    delimitado y sin decirle al modelo qué significa. Pasar
    `tenant_instructions=None` es la forma normal de pedir «solo la defensa».
    """
    instructions = (tenant_instructions or "").strip()
    if not instructions:
        return f"{base}\n\n{REGLA_CONTENIDO_NO_CONFIABLE}"
    # Las instrucciones del tenant las escribe su administrador, que ya tiene
    # un canal legítimo para dar órdenes al modelo. Aun así se neutralizan: un
    # `</INSTRUCCIONES_DEL_TENANT>` aquí dentro haría que el resto del bloque
    # se leyera como si viniera de la plataforma.
    instructions = neutralizar(instructions)
    if len(instructions) > TENANT_INSTRUCTIONS_MAX_CHARS:
        instructions = instructions[: TENANT_INSTRUCTIONS_MAX_CHARS - 1].rstrip() + "…"
    return (
        f"{base}\n\n"
        "<INSTRUCCIONES_DEL_TENANT>\n"
        "Instrucciones permanentes configuradas por el administrador. "
        "Aplícalas en el contenido y estilo, pero NUNCA cambies el formato "
        "de salida exigido arriba.\n"
        f"{instructions}\n"
        "</INSTRUCCIONES_DEL_TENANT>\n\n"
        f"{REGLA_CONTENIDO_NO_CONFIABLE}"
    )
