"""Resolución del modo IA por tenant (US-057).

Lee `tenants.settings.ai.{mode, byo}` y construye la config efectiva
que el worker (o el endpoint que gatea 409) necesita para enrutar al
provider correcto.

Shape canónico de `tenants.settings.ai`:

    {
      "mode": "disabled" | "platform" | "byo",
      "byo": {
        "provider": "openai" | "claude" | "perplexity" | "gemini" | "ollama",
        "api_key_encrypted": "enc::...",
        "model": "...",
        "base_url": "...",              # sólo ollama (tailnet) y opcional openai
        "last_test_at": "2026-04-23T...",
        "last_test_status": "ok" | "fail",
        "last_test_error": "..."        # opcional
      } | null,
      "ollama": {...}                    # legacy US-048 — se migra al commit 0022
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.services.ai.provider import BYO_PROVIDERS
from app.services.ai_secrets import decrypt_secret

VALID_MODES: tuple[str, ...] = ("disabled", "platform", "byo")


@dataclass
class TenantAIConfig:
    """Resultado canónico para el worker y los endpoints."""

    mode: str  # "disabled" | "platform" | "byo"
    byo: dict[str, Any] | None = None  # api_key descifrada + provider + model/base_url
    legacy_ollama: dict[str, Any] | None = None  # US-048 retro-compat

    @property
    def enabled(self) -> bool:
        return self.mode != "disabled"


async def load_tenant_ai(db: AsyncSession, tenant_id: UUID | str) -> TenantAIConfig:
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        return TenantAIConfig(mode="disabled")

    ai = dict((t.settings or {}).get("ai") or {})
    mode = str(ai.get("mode") or "disabled").lower()
    if mode not in VALID_MODES:
        mode = "disabled"

    byo_effective: dict[str, Any] | None = None
    byo_raw = ai.get("byo")
    if mode == "byo" and isinstance(byo_raw, dict):
        provider = str(byo_raw.get("provider") or "").lower()
        if provider not in BYO_PROVIDERS:
            # Config inválida → el worker fallará duro.
            return TenantAIConfig(
                mode="byo", byo={"provider": provider, "api_key": "", "model": None}
            )
        byo_effective = {
            "provider": provider,
            "api_key": decrypt_secret(byo_raw.get("api_key_encrypted") or ""),
            "model": byo_raw.get("model") or None,
            "base_url": byo_raw.get("base_url") or None,
        }
        # Limpiar Nones para que el factory use defaults del provider.
        byo_effective = {k: v for k, v in byo_effective.items() if v is not None}

    legacy_ollama = ai.get("ollama") if isinstance(ai.get("ollama"), dict) else None

    return TenantAIConfig(
        mode=mode, byo=byo_effective, legacy_ollama=legacy_ollama
    )
