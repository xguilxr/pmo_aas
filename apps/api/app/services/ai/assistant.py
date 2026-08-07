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

import re
from typing import Any

from app.services.ai.frontera import aplicar_frontera, bloque_para_prompt
from app.services.ai.json_parse import parse_json_lenient
from app.services.ai.untrusted import envolver_no_confiable, neutralizar

# Acciones permitidas que el frontend sabe ejecutar. Todas son seguras
# (no mutan datos); navegar es la única con efecto y es reversible.
ALLOWED_ACTION_TYPES: frozenset[str] = frozenset({"navigate", "none"})

# Caracteres que convierten una ruta «interna» en una salida del sitio.
#
# `assistant-widget.tsx` hace `router.push(a.path)`, y el router resuelve con
# `new URL(path, location)`. El parser de URL del navegador (WHATWG §4.4)
# trata `\` como `/` en esquemas especiales y **borra** tabuladores y saltos
# de línea ANTES de parsear. Comprobado contra el parser de Node:
#
#     "/\evil.example/x"    →  https://evil.example/x
#     "/\t/evil.example/x"  →  https://evil.example/x
#     "/\n/evil.example/x"  →  https://evil.example/x
#     "/\r/evil.example/x"  →  https://evil.example/x
#
# Los cuatro empiezan por `/` y no por `//`, que era toda la comprobación que
# había. Un modelo que obedece una instrucción inyectada en una minuta podía
# devolver cualquiera de ellos y el copiloto ofrecía el botón. Encontrado al
# construir el conjunto de evaluación (B3, MCS IA-07/08/09); los cuatro son
# ahora casos permanentes suyos (S-02..S-05).
_RE_RUTA_INSEGURA = re.compile(r"[\\\x00-\x1f\x7f]")


def ruta_interna_segura(path: str) -> bool:
    """¿Es `path` una ruta relativa a la raíz que no puede salir del sitio?

    Lista blanca de forma, no lista negra de dominios: tiene que empezar por
    una sola barra y no puede contener ningún carácter que el parser del
    navegador reinterprete o descarte.
    """
    if not path.startswith("/") or path.startswith("//"):
        return False
    return not _RE_RUTA_INSEGURA.search(path)

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

{{FRONTERA}}
"""

# MCS CON-05 — la frontera se GENERA desde `frontera.py`, que refleja
# `06-COMPETENCIA.md` §3. Escribirla aquí permitiría que la instrucción dijera
# algo que el documento no dice.
#
# Y decírselo al modelo es el paso 1 de tres: el propio documento avisa de que
# «una frontera que solo vive en el texto de un prompt se erosiona con cada
# cambio de modelo y nadie se entera». El paso 2 —`aplicar_frontera`— corre
# DESPUÉS y no le pide permiso al modelo.
ASSISTANT_SYSTEM = ASSISTANT_SYSTEM.replace("{{FRONTERA}}", bloque_para_prompt())


def build_assistant_prompt(
    user_message: str,
    page_context: str | None,
    history: list[dict[str, str]],
) -> str:
    """Arma el prompt de usuario con contexto de página + historial.

    B2 (MCS IA-11): el `page_context` lo compone el frontend con los datos que
    la pantalla está mostrando —nombres de proyecto, títulos de riesgo,
    descripciones de RAID extraídas de minutas—, así que es contenido de
    terceros y va envuelto. El `history` también: arrastra turnos previos del
    modelo, que pudieron contaminarse con un contexto anterior.

    El `user_message` lo teclea quien está usando el widget en ese momento: es
    su petición y es a lo que el asistente debe responder. Se neutraliza, no se
    envuelve.
    """
    parts: list[str] = []
    if page_context:
        parts.append(
            "CONTEXTO DE LA PÁGINA ACTUAL:\n"
            + envolver_no_confiable(
                page_context.strip()[:4000],
                origen="datos que muestra la pantalla, redactados por usuarios",
            )
            + "\n"
        )
    if history:
        hist = "\n".join(
            f"{m.get('role', 'user')}: {str(m.get('content', ''))[:500]}"
            for m in history[-10:]
        )
        parts.append(
            "HISTORIAL RECIENTE:\n"
            + envolver_no_confiable(hist, origen="turnos previos de la conversación")
            + "\n"
        )
    parts.append(f"MENSAJE DEL USUARIO:\n{neutralizar(user_message.strip())}")
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
                if not ruta_interna_segura(path):
                    continue
                actions.append(
                    {"type": "navigate", "path": path, "label": str(a.get("label") or "Ir")}
                )
            elif atype == "none":
                continue
    if not message:
        message = "Listo."
    return message, actions


def responder(salida_modelo: str, consulta: str) -> tuple[str, list[dict[str, Any]]]:
    """La respuesta que llega al usuario: se interpreta y se aplica la frontera.

    **Es la puerta que deben usar el punto de acceso y el evaluador**, no
    `parse_assistant_reply` a secas. Existe como función propia por eso: con
    dos consumidores llamando cada uno a lo que le parezca, la comprobación de
    CON-05 se cae del camino sin que nadie lo note — que es la forma en que un
    control desaparece.
    """
    mensaje, acciones = parse_assistant_reply(salida_modelo)
    return aplicar_frontera(mensaje, consulta), acciones
