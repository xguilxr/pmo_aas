"""Resolución de defaults de AI a nivel de plataforma (US-054, BUG-053).

Construye la config Groq efectiva para el modo `platform` mergeando
`platform_ai_settings` (editable por superadmin) con env. La fuente de
la API key es `platform_ai_settings.groq_api_key_encrypted` (cifrada
con Fernet); si está vacía cae al env `GROQ_API_KEY`.

BUG-053 (2026-05-08): se eliminaron `resolve_ollama_config` y los
campos Ollama del row singleton.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.platform_settings import PLATFORM_SETTINGS_ID, PlatformAISettings


async def get_platform_ai_defaults(db: AsyncSession) -> dict[str, Any]:
    """Lee la row singleton. Devuelve dict crudo (solo columnas seteadas)."""
    row = (
        await db.execute(
            select(PlatformAISettings).where(PlatformAISettings.id == PLATFORM_SETTINGS_ID)
        )
    ).scalar_one_or_none()
    if row is None:
        return {}
    out: dict[str, Any] = {}
    if row.ai_mode:
        out["ai_mode"] = row.ai_mode
    if row.groq_api_key_encrypted:
        out["groq_api_key_encrypted"] = row.groq_api_key_encrypted
    if row.groq_model:
        out["groq_model"] = row.groq_model
    return out


async def resolve_groq_config(db: AsyncSession) -> dict[str, Any] | None:
    """Resuelve la config Groq para el modo `platform`.

    Orden: `platform_ai_settings.groq_api_key_encrypted` (descifrada) →
    env `GROQ_API_KEY`. Si no hay key en ningún lado, devuelve None y
    el caller debe fallar con un error explícito al superadmin.
    """
    from app.services.ai_secrets import decrypt_secret

    platform = await get_platform_ai_defaults(db)
    api_key = (
        decrypt_secret(platform.get("groq_api_key_encrypted") or "")
        or settings.GROQ_API_KEY
    )
    model = platform.get("groq_model") or settings.GROQ_MODEL
    if not api_key:
        return None
    return {"api_key": api_key, "model": model}


async def resolve_ai_mode(db: AsyncSession) -> str:
    """Devuelve el AI_MODE efectivo: platform override > env."""
    platform = await get_platform_ai_defaults(db)
    return str(platform.get("ai_mode") or settings.AI_MODE)
