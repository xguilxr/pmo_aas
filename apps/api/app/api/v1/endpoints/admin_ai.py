"""Config y smoke de proveedores IA por-tenant.

Historia:
- US-045 (2026-04-20): versión inicial con Cloudflare Tunnel +
  Service Token (CF-Access-Client-Id / CF-Access-Client-Secret).
- US-047 (2026-04-21): pivote a Tailscale — se eliminan los campos
  CF-Access. La config Ollama por-tenant se expuso como
  `{base_url, model, timeout_sec}` y se serví bajo `/admin/ai/ollama`.
- US-057 (2026-04-22, DEC-017): se reemplaza el cascade global por
  3 modos por-tenant (`disabled | platform | byo`). El nuevo flujo
  vive en `/admin/ai/provider`.
- BUG-027 (2026-04-23, ver DEC-019): se retiran los endpoints
  `/admin/ai/ollama` (GET/PATCH) y `/admin/ai/test-connection` — ya
  no tienen consumidor en la UI (`OllamaLocalAiForm` borrado). Los
  tenants legacy con `settings.ai.ollama` en BD siguen intactos;
  el worker los ignora porque el schema activo es `settings.ai.mode`.

Endpoints activos:
- GET   /api/v1/admin/ai/provider       — modo + BYO config.
- PATCH /api/v1/admin/ai/provider       — cambia modo o guarda BYO.
- POST  /api/v1/admin/ai/provider/test  — ping al proveedor BYO.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_capability
from app.core.config import settings
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.ai.byo_catalog import catalog_for_api
from app.services.ai.provider import BYO_PROVIDERS_ALLOWED
from app.services.ai.tenant_ai import VALID_MODES
from app.services.ai_secrets import encrypt_secret, mask_secret
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/ai", tags=["admin_ai"])


def _tenant_id(cu: CurrentUser) -> UUID:
    if cu.user.tenant_id is None:
        raise forbidden()
    return cu.user.tenant_id


class TestConnectionResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    ok: bool
    latency_ms: int | None = None
    model_present: bool | None = None
    tags_count: int | None = None
    error: str | None = None
    code: str | None = None


# ============================================================================
# US-057 — Tenant admin: selección de modo IA (disabled / platform / byo)
# ============================================================================


class BYOConfigIn(BaseModel):
    # US-063 follow-up: ollama queda fuera del Literal — para tenants
    # legacy US-048 que ya estén en la BD, el worker sigue funcionando
    # pero el endpoint PATCH rechaza nuevos ollama.
    provider: Literal["openai", "claude", "perplexity", "gemini"]
    api_key: str | None = Field(
        default=None,
        description=(
            "Si se omite en PATCH, conserva la key cifrada existente. "
            "Enviar cadena vacía para borrarla."
        ),
    )
    model: str | None = Field(default=None, max_length=100)
    base_url: str | None = Field(default=None, max_length=500)


class BYOConfigRead(BaseModel):
    provider: str
    api_key_mask: str | None = None
    has_api_key: bool = False
    model: str | None = None
    base_url: str | None = None
    last_test_at: str | None = None
    last_test_status: Literal["ok", "fail"] | None = None
    last_test_error: str | None = None


class TenantAIProviderRead(BaseModel):
    mode: Literal["disabled", "platform", "byo"]
    byo: BYOConfigRead | None = None
    # US-063 follow-up: feature-flag del modo BYO. Cuando está off, el
    # wizard de conexión en la UI queda deshabilitado ("Próximamente")
    # pero las cards con metadata de cada proveedor siguen visibles.
    byo_enabled: bool = False
    # Catálogo de proveedores BYO soportados con sus deep-links a la
    # consola + modelos sugeridos. Se lee de la UI para renderizar las
    # cards sin hardcodear URLs.
    byo_catalog: list[dict] = []


class TenantAIProviderPatch(BaseModel):
    mode: Literal["disabled", "platform", "byo"]
    byo: BYOConfigIn | None = None


def _build_byo_read(byo_raw: dict) -> BYOConfigRead:
    enc = byo_raw.get("api_key_encrypted") or ""
    from app.services.ai_secrets import decrypt_secret

    plain = decrypt_secret(enc) if enc else ""
    mask = mask_secret(plain) if plain else None
    return BYOConfigRead(
        provider=str(byo_raw.get("provider") or ""),
        api_key_mask=mask,
        has_api_key=bool(plain),
        model=byo_raw.get("model"),
        base_url=byo_raw.get("base_url"),
        last_test_at=byo_raw.get("last_test_at"),
        last_test_status=byo_raw.get("last_test_status"),
        last_test_error=byo_raw.get("last_test_error"),
    )


@router.get("/provider", response_model=TenantAIProviderRead)
async def get_provider_config(
    cu: CurrentUser = Depends(require_capability("ai.configure")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")
    ai = dict((t.settings or {}).get("ai") or {})
    mode = str(ai.get("mode") or "disabled")
    if mode not in VALID_MODES:
        mode = "disabled"
    byo_raw = ai.get("byo") if isinstance(ai.get("byo"), dict) else None
    return TenantAIProviderRead(
        mode=mode,  # type: ignore[arg-type]
        byo=_build_byo_read(byo_raw) if byo_raw else None,
        byo_enabled=bool(settings.AI_BYO_ENABLED),
        byo_catalog=catalog_for_api(),
    )


@router.patch("/provider", response_model=TenantAIProviderRead)
async def update_provider_config(
    body: TenantAIProviderPatch,
    cu: CurrentUser = Depends(require_capability("ai.configure")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    merged = dict(t.settings or {})
    ai = dict(merged.get("ai") or {})
    ai["mode"] = body.mode

    if body.mode == "byo":
        # US-063 follow-up: feature flag. El backend aún acepta BYO vía
        # API (para tests y scripts), pero desde /admin/ai el wizard
        # queda deshabilitado hasta que el owner encienda el flag.
        if not settings.AI_BYO_ENABLED:
            from app.core.errors import business_rule

            raise business_rule(
                "El modo BYO aún no está habilitado en esta plataforma. "
                "Habilítalo con AI_BYO_ENABLED=1 en Railway cuando el "
                "wizard de conexión esté listo.",
                code="BYO_NOT_ENABLED",
            )
        if body.byo is None:
            from app.core.errors import business_rule

            raise business_rule("byo requerido cuando mode='byo'")
        if body.byo.provider not in BYO_PROVIDERS_ALLOWED:
            from app.core.errors import business_rule

            raise business_rule(
                f"Provider BYO inválido: {body.byo.provider}",
                code="BYO_PROVIDER_INVALID",
            )
        existing = ai.get("byo") if isinstance(ai.get("byo"), dict) else {}
        byo: dict = {"provider": body.byo.provider}
        # Re-cifrar solo si el usuario envía api_key explícita; si no,
        # conservar la cifrada existente.
        if body.byo.api_key is None:
            byo["api_key_encrypted"] = existing.get("api_key_encrypted") or ""
        else:
            byo["api_key_encrypted"] = (
                encrypt_secret(body.byo.api_key) if body.byo.api_key else ""
            )
        byo["model"] = body.byo.model or existing.get("model")
        byo["base_url"] = body.byo.base_url or existing.get("base_url")
        # Al cambiar credenciales limpiamos el último test.
        if body.byo.api_key is not None or (
            body.byo.provider != (existing or {}).get("provider")
        ):
            byo["last_test_at"] = None
            byo["last_test_status"] = None
            byo["last_test_error"] = None
        else:
            byo["last_test_at"] = existing.get("last_test_at")
            byo["last_test_status"] = existing.get("last_test_status")
            byo["last_test_error"] = existing.get("last_test_error")
        ai["byo"] = byo
    elif body.mode == "platform":
        # Preservamos byo previo archivado por si el user vuelve a byo.
        pass
    else:  # disabled
        pass

    merged["ai"] = ai
    t.settings = merged

    await write_audit(
        db,
        action="tenant.ai.mode.change",
        module="admin.ai",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="tenant",
        entity_id=str(t.id),
        details={
            "mode": body.mode,
            "byo_provider": body.byo.provider if body.byo else None,
            "byo_api_key_changed": body.byo is not None and body.byo.api_key is not None,
        },
    )
    await db.commit()
    return await get_provider_config(cu=cu, db=db)  # type: ignore[arg-type]


class ProviderTestBody(BaseModel):
    """Si se envía `byo`, se usa esa config; si no, la del tenant actual."""

    byo: BYOConfigIn | None = None


@router.post("/provider/test", response_model=TestConnectionResult)
async def test_provider_connection(
    body: ProviderTestBody,
    cu: CurrentUser = Depends(require_capability("ai.configure")),
    db: AsyncSession = Depends(get_db),
):
    """US-057: valida credenciales BYO con un ping mínimo antes de guardar.

    Para cada provider llama el endpoint más barato (GET /models para
    OpenAI y Gemini, POST mínimo para Claude y Perplexity, GET /api/tags
    para Ollama). Devuelve ok/latency/error.
    """
    from app.services.ai_secrets import decrypt_secret

    # Gate BYO feature flag (US-063 follow-up).
    if not settings.AI_BYO_ENABLED:
        return TestConnectionResult(
            ok=False,
            error=(
                "BYO aún no habilitado. Activa AI_BYO_ENABLED cuando el "
                "wizard de conexión esté listo."
            ),
            code="BYO_NOT_ENABLED",
        )

    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    byo_in = body.byo
    if byo_in is None:
        ai = dict((t.settings or {}).get("ai") or {})
        byo_raw = ai.get("byo") if isinstance(ai.get("byo"), dict) else None
        if not byo_raw:
            return TestConnectionResult(
                ok=False, error="No hay BYO configurado", code="NOT_CONFIGURED",
            )
        provider = byo_raw.get("provider")
        api_key = decrypt_secret(byo_raw.get("api_key_encrypted") or "")
        model = byo_raw.get("model")
        base_url = byo_raw.get("base_url")
    else:
        provider = byo_in.provider
        api_key = byo_in.api_key or ""
        model = byo_in.model
        base_url = byo_in.base_url

    result = await _ping_byo_provider(provider, api_key, model, base_url)

    # Persistir el resultado en el tenant para el panel del superadmin,
    # SOLO si estamos validando la config ya guardada (body.byo == None).
    if byo_in is None:
        merged = dict(t.settings or {})
        ai = dict(merged.get("ai") or {})
        byo = dict(ai.get("byo") or {})
        byo["last_test_at"] = datetime.now(UTC).isoformat()
        byo["last_test_status"] = "ok" if result.ok else "fail"
        byo["last_test_error"] = result.error if not result.ok else None
        ai["byo"] = byo
        merged["ai"] = ai
        t.settings = merged
        await db.commit()

    return result


async def _ping_byo_provider(
    provider: str | None,
    api_key: str,
    model: str | None,
    base_url: str | None,
) -> TestConnectionResult:
    import httpx

    started = time.perf_counter()
    try:
        if provider == "openai":
            if not api_key:
                return TestConnectionResult(ok=False, error="api_key requerida", code="NO_KEY")
            url = f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/models"
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url, headers={"Authorization": f"Bearer {api_key}"})
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code >= 300:
                return TestConnectionResult(
                    ok=False, latency_ms=latency,
                    error=f"HTTP {r.status_code}: {r.text[:120]}",
                    code="HTTP_ERROR",
                )
            return TestConnectionResult(ok=True, latency_ms=latency)

        if provider == "claude":
            if not api_key:
                return TestConnectionResult(ok=False, error="api_key requerida", code="NO_KEY")
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model or "claude-3-5-haiku-20241022",
                        "max_tokens": 4,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                )
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code >= 300:
                return TestConnectionResult(
                    ok=False, latency_ms=latency,
                    error=f"HTTP {r.status_code}: {r.text[:120]}",
                    code="HTTP_ERROR",
                )
            return TestConnectionResult(ok=True, latency_ms=latency)

        if provider == "perplexity":
            if not api_key:
                return TestConnectionResult(ok=False, error="api_key requerida", code="NO_KEY")
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(
                    f"{(base_url or 'https://api.perplexity.ai').rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model or "sonar",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 4,
                    },
                )
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code >= 300:
                return TestConnectionResult(
                    ok=False, latency_ms=latency,
                    error=f"HTTP {r.status_code}: {r.text[:120]}",
                    code="HTTP_ERROR",
                )
            return TestConnectionResult(ok=True, latency_ms=latency)

        if provider == "gemini":
            if not api_key:
                return TestConnectionResult(ok=False, error="api_key requerida", code="NO_KEY")
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={api_key}"
            )
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url)
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code >= 300:
                return TestConnectionResult(
                    ok=False, latency_ms=latency,
                    error=f"HTTP {r.status_code}",
                    code="HTTP_ERROR",
                )
            return TestConnectionResult(ok=True, latency_ms=latency)

        if provider == "ollama":
            if not base_url:
                return TestConnectionResult(
                    ok=False, error="base_url requerida", code="NO_BASE_URL",
                )
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(f"{base_url.rstrip('/')}/api/tags")
            latency = int((time.perf_counter() - started) * 1000)
            if r.status_code >= 300:
                return TestConnectionResult(
                    ok=False, latency_ms=latency,
                    error=f"HTTP {r.status_code}",
                    code="HTTP_ERROR",
                )
            return TestConnectionResult(ok=True, latency_ms=latency)

        return TestConnectionResult(
            ok=False, error=f"Provider no soportado: {provider}", code="UNSUPPORTED",
        )
    except httpx.TimeoutException:
        return TestConnectionResult(
            ok=False, error="Timeout al conectar", code="TIMEOUT",
        )
    except Exception as exc:
        return TestConnectionResult(
            ok=False, error=str(exc)[:200], code="UNKNOWN",
        )
