"""Defaults de AI a nivel de plataforma (US-054).

Superadmin puede ajustar AI_MODE, Ollama base_url/model y timeout sin
redeploy. Los valores se guardan en la tabla singleton
`platform_ai_settings` (id='default') y son leídos por el provider
entre el override per-tenant y las env vars.

Secrets (GEMINI_API_KEY, ANTHROPIC_API_KEY) NO viven aquí — siguen en
env para evitar almacenar secrets sin cifrado.

Endpoints:
- GET  /api/v1/superadmin/ai/defaults — lee config actual + snapshot env.
- PATCH /api/v1/superadmin/ai/defaults — actualiza campos parciales.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import AnyHttpUrl, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_superadmin
from app.core.config import settings
from app.db.session import get_db
from app.models.platform_settings import PLATFORM_SETTINGS_ID, PlatformAISettings
from app.services.audit import write_audit

router = APIRouter(prefix="/superadmin/ai", tags=["superadmin_ai"])


class EnvSnapshot(BaseModel):
    ai_mode: str
    ollama_base_url: str
    ollama_model: str
    ai_timeout_sec: int
    gemini_configured: bool
    claude_configured: bool


class PlatformAIDefaultsRead(BaseModel):
    ai_mode: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    ai_timeout_sec: int | None = None
    env: EnvSnapshot


class PlatformAIDefaultsPatch(BaseModel):
    ai_mode: Literal["ollama", "gemini", "claude", "disabled"] | None = None
    ollama_base_url: AnyHttpUrl | None = None
    ollama_model: str | None = Field(default=None, max_length=100)
    ai_timeout_sec: int | None = Field(default=None, ge=5, le=3600)


async def _get_or_create(db: AsyncSession) -> PlatformAISettings:
    row = (
        await db.execute(
            select(PlatformAISettings).where(PlatformAISettings.id == PLATFORM_SETTINGS_ID)
        )
    ).scalar_one_or_none()
    if row is None:
        row = PlatformAISettings(id=PLATFORM_SETTINGS_ID)
        db.add(row)
        await db.flush()
    return row


def _to_read(row: PlatformAISettings) -> PlatformAIDefaultsRead:
    return PlatformAIDefaultsRead(
        ai_mode=row.ai_mode,
        ollama_base_url=row.ollama_base_url,
        ollama_model=row.ollama_model,
        ai_timeout_sec=row.ai_timeout_sec,
        env=EnvSnapshot(
            ai_mode=settings.AI_MODE,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            ollama_model=settings.OLLAMA_MODEL,
            ai_timeout_sec=settings.AI_TIMEOUT_S,
            gemini_configured=bool(settings.GEMINI_API_KEY),
            claude_configured=bool(settings.ANTHROPIC_API_KEY),
        ),
    )


@router.get("/defaults", response_model=PlatformAIDefaultsRead)
async def read_defaults(
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create(db)
    await db.commit()
    return _to_read(row)


@router.patch("/defaults", response_model=PlatformAIDefaultsRead)
async def update_defaults(
    body: PlatformAIDefaultsPatch,
    cu: CurrentUser = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create(db)
    data = body.model_dump(exclude_unset=True)
    if "ai_mode" in data:
        row.ai_mode = data["ai_mode"]
    if "ollama_base_url" in data:
        row.ollama_base_url = (
            str(data["ollama_base_url"]).rstrip("/")
            if data["ollama_base_url"] is not None
            else None
        )
    if "ollama_model" in data:
        row.ollama_model = data["ollama_model"]
    if "ai_timeout_sec" in data:
        row.ai_timeout_sec = (
            int(data["ai_timeout_sec"]) if data["ai_timeout_sec"] is not None else None
        )

    await write_audit(
        db, action="superadmin.ai.defaults.update", module="superadmin",
        user_id=cu.id, entity_type="platform_ai_settings", entity_id=PLATFORM_SETTINGS_ID,
        details={"fields_set": list(data.keys())},
    )
    await db.commit()
    return _to_read(row)
