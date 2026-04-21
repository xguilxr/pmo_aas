"""Resolución de defaults de AI a nivel de plataforma (US-054).

El provider (`OllamaProvider.generate()`) recibe un `override` que es el
merge de **tenant → platform_ai_settings → env**. Este módulo se encarga
de construir ese merge desde los tres lados:

1. `tenants.settings.ai.ollama` (JSON per-tenant) — highest priority.
2. `platform_ai_settings` (singleton) — mid priority, editable por superadmin.
3. `settings.OLLAMA_BASE_URL` / `OLLAMA_MODEL` / `AI_TIMEOUT_S` (env) — lowest.

El cache es muy sencillo (dict en módulo). Se invalida en el mismo
proceso cuando el superadmin hace PATCH; en multi-worker (api + celery)
cada proceso refresca solo-en-arranque — es aceptable porque cambiar
defaults de plataforma es evento raro.
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
    if row.ollama_base_url:
        out["ollama_base_url"] = row.ollama_base_url
    if row.ollama_model:
        out["ollama_model"] = row.ollama_model
    if row.ai_timeout_sec is not None:
        out["ai_timeout_sec"] = int(row.ai_timeout_sec)
    return out


async def resolve_ollama_config(
    db: AsyncSession, tenant_cfg: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Merge tenant → platform → env, listo para pasar a OllamaProvider.

    Devuelve `None` si no hay `base_url` en ningún nivel — el provider
    caerá directo al env como fallback (mismo comportamiento legacy).
    """
    platform = await get_platform_ai_defaults(db)
    tenant = dict(tenant_cfg or {})

    base_url = (
        tenant.get("base_url")
        or platform.get("ollama_base_url")
        or settings.OLLAMA_BASE_URL
    )
    model = (
        tenant.get("model")
        or platform.get("ollama_model")
        or settings.OLLAMA_MODEL
    )
    timeout_sec = (
        tenant.get("timeout_sec")
        or platform.get("ai_timeout_sec")
        or settings.AI_TIMEOUT_S
    )

    if not base_url:
        return None
    return {
        "base_url": base_url,
        "model": model,
        "timeout_sec": int(timeout_sec),
    }


async def resolve_ai_mode(db: AsyncSession) -> str:
    """Devuelve el AI_MODE efectivo: platform override > env.

    Notar que no existe override per-tenant del modo de cascada — el
    modo es decisión de plataforma. Si un tenant configuró su propio
    `base_url`, el cascade sigue empezando por "ollama" igual.
    """
    platform = await get_platform_ai_defaults(db)
    return str(platform.get("ai_mode") or settings.AI_MODE)
