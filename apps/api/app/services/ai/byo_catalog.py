"""Catálogo de proveedores BYO y su metadata UX (US-063 follow-up).

La UI `/admin/ai` pinta cards por proveedor con:
- Label legible.
- Descripción breve.
- Link a la consola donde generar la API key.
- Link a la documentación del proveedor.
- Modelos sugeridos (datalist del selector).

Se expone vía `GET /api/v1/admin/ai/provider` para que el frontend no
hardcodee URLs y pueda actualizarse vía backend sin redeploy del web.
"""
from __future__ import annotations

from typing import TypedDict


class BYOProviderInfo(TypedDict):
    key: str
    label: str
    description: str
    api_keys_url: str
    docs_url: str
    suggested_models: list[str]
    requires_base_url: bool


BYO_CATALOG: list[BYOProviderInfo] = [
    {
        "key": "openai",
        "label": "OpenAI (ChatGPT)",
        "description": (
            "Conecta tu cuenta de OpenAI. Funciona con gpt-4o y la familia "
            "gpt-4. Costo por tokens lo paga tu cuenta."
        ),
        "api_keys_url": "https://platform.openai.com/api-keys",
        "docs_url": "https://platform.openai.com/docs/api-reference/authentication",
        "suggested_models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        "requires_base_url": False,
    },
    {
        "key": "claude",
        "label": "Anthropic (Claude)",
        "description": (
            "Conecta tu cuenta de Anthropic. Claude Sonnet 4.x o Haiku, "
            "excelente para minutas largas y reportes con estructura."
        ),
        "api_keys_url": "https://console.anthropic.com/settings/keys",
        "docs_url": "https://docs.anthropic.com/en/api/getting-started",
        "suggested_models": [
            "claude-3-5-haiku-20241022",
            "claude-sonnet-4-6",
        ],
        "requires_base_url": False,
    },
    {
        "key": "gemini",
        "label": "Google Gemini",
        "description": (
            "Conecta tu cuenta de Google AI Studio. Gemini 1.5 Flash tiene "
            "free tier generoso (1M tokens/día)."
        ),
        "api_keys_url": "https://aistudio.google.com/apikey",
        "docs_url": "https://ai.google.dev/gemini-api/docs/api-key",
        "suggested_models": ["gemini-1.5-flash", "gemini-1.5-pro"],
        "requires_base_url": False,
    },
    {
        "key": "perplexity",
        "label": "Perplexity",
        "description": (
            "Conecta Perplexity. Los modelos sonar-* combinan LLM con "
            "búsqueda web actualizada — útil para reportes con referencias."
        ),
        "api_keys_url": "https://www.perplexity.ai/settings/api",
        "docs_url": "https://docs.perplexity.ai/api-reference/chat-completions-post",
        "suggested_models": ["sonar", "sonar-pro"],
        "requires_base_url": False,
    },
]


def catalog_for_api() -> list[dict]:
    """Versión serializable para el endpoint GET."""
    return [dict(entry) for entry in BYO_CATALOG]
