"""Asistente IA conversacional — lógica de prompt + acciones (US-165, EP008).

El widget global manda el mensaje del usuario + un `page_context` (texto
que describe dónde está parado: ruta, entidad, datos visibles) + el
historial reciente. El asistente responde SIEMPRE con JSON estructurado:

    {"message": "<respuesta en español>", "actions": [ <acción>, ... ]}

Acciones soportadas (v1 — solo lectura/navegación, sin escrituras para
mantener el blast radius en cero):

    {"type": "navigate", "path": "/pmo/projects/<id>", "label": "Abrir proyecto"}
    {"type": "none"}

La ejecución de tool-calling nativo del provider queda para una iteración
futura; reusamos el patrón "JSON-action" ya probado en el Report Builder
(report_builder_chat) que funciona en los 6 proveedores por igual.
"""
from __future__ import annotations

from typing import Any

from app.services.ai.json_parse import parse_json_lenient

# Acciones permitidas que el frontend sabe ejecutar. Todas son seguras
# (no mutan datos); navegar es la única con efecto y es reversible.
ALLOWED_ACTION_TYPES: frozenset[str] = frozenset({"navigate", "none"})

ASSISTANT_SYSTEM = """Eres el copiloto IA de PMO-aaS, una plataforma de
gestión de portafolios, programas y proyectos (PMO). Ayudas a Project
Managers a entender su información y a moverse por la plataforma.

Tienes el CONTEXTO de la página donde está el usuario (ruta + datos
visibles). Úsalo para responder con precisión y en español, claro y breve.

Devuelves SIEMPRE y ÚNICAMENTE un objeto JSON válido con esta forma:
{
  "message": "<respuesta breve y útil en español>",
  "actions": [
    {"type": "navigate", "path": "/pmo/...", "label": "<texto del botón>"}
  ]
}

Reglas:
- `actions` es opcional; si no hay nada que navegar, usa [].
- SOLO usa rutas internas que aparezcan en el contexto o que sean
  claramente válidas del producto (/pmo, /pmo/projects/<id>, /pmo/projects/<id>/raid,
  /pmo/organizations/<id>, /pmo/reports, etc.). NO inventes ids.
- NO propongas acciones de escritura (crear/editar/borrar): esta versión
  es de solo lectura y navegación.
- NO escribas texto fuera del JSON. NO uses bloques de código ni comentarios.
- Si no sabes algo o no está en el contexto, dilo con honestidad y sugiere
  a dónde ir para encontrarlo.
"""


def build_assistant_prompt(
    user_message: str,
    page_context: str | None,
    history: list[dict[str, str]],
) -> str:
    """Arma el prompt de usuario con contexto de página + historial."""
    parts: list[str] = []
    if page_context:
        parts.append(f"CONTEXTO DE LA PÁGINA ACTUAL:\n{page_context.strip()[:4000]}\n")
    if history:
        hist = "\n".join(
            f"{m.get('role', 'user')}: {str(m.get('content', ''))[:500]}"
            for m in history[-10:]
        )
        parts.append(f"HISTORIAL RECIENTE:\n{hist}\n")
    parts.append(f"MENSAJE DEL USUARIO:\n{user_message.strip()}")
    parts.append(
        "\nResponde SOLO con el objeto JSON {message, actions} indicado."
    )
    return "\n\n".join(parts)


def parse_assistant_reply(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Extrae (message, actions) de la salida del modelo. Si no es JSON
    válido, trata todo el texto como el mensaje (sin acciones) — así el
    usuario siempre recibe una respuesta útil aunque el modelo no respete
    el formato."""
    data = parse_json_lenient(text)
    if data is None:
        return (text.strip()[:2000] or "No pude generar una respuesta."), []
    message = str(data.get("message") or "").strip()
    raw_actions = data.get("actions")
    actions: list[dict[str, Any]] = []
    if isinstance(raw_actions, list):
        for a in raw_actions:
            if not isinstance(a, dict):
                continue
            atype = str(a.get("type") or "")
            if atype not in ALLOWED_ACTION_TYPES:
                continue
            if atype == "navigate":
                path = str(a.get("path") or "").strip()
                # Solo rutas internas relativas (seguridad: nada de URLs externas).
                if not path.startswith("/") or path.startswith("//"):
                    continue
                actions.append(
                    {"type": "navigate", "path": path, "label": str(a.get("label") or "Ir")}
                )
            elif atype == "none":
                continue
    if not message:
        message = "Listo."
    return message, actions
