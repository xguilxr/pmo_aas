"""Config y smoke de proveedores IA por-tenant (US-057, BUG-053).

3 modos por-tenant: `disabled | platform | byo`. BYO whitelist:
openai / claude / perplexity / gemini.

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

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_capability
from app.core.errors import forbidden, not_found
from app.core.url_externa import asegurar_url_externa, motivo_url_insegura
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.ai.byo_catalog import catalog_for_api
from app.services.ai.provider import BYO_PROVIDERS_ALLOWED
from app.services.ai.tenant_ai import VALID_MODES
from app.services.ai_secrets import encrypt_secret, mask_secret
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/ai", tags=["admin_ai"])


def _tenant_id(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


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
    provider: Literal[
        "openai", "claude", "perplexity", "gemini", "custom", "azure",
    ]
    api_key: str | None = Field(
        default=None,
        description=(
            "Si se omite en PATCH, conserva la key cifrada existente. "
            "Enviar cadena vacía para borrarla."
        ),
    )
    model: str | None = Field(default=None, max_length=100)
    base_url: str | None = Field(default=None, max_length=500)
    # US-110: Azure / Microsoft Copilot M365.
    deployment_name: str | None = Field(default=None, max_length=120)
    api_version: str | None = Field(default=None, max_length=40)
    # US-110 CA4: límites por provider para evitar costos descontrolados.
    rate_limit_rpm: int | None = Field(default=None, ge=1, le=100_000)
    daily_token_limit: int | None = Field(default=None, ge=100, le=100_000_000)
    # US-110 CA3: ack explícito de riesgo cuando el tenant elige custom.
    acknowledge_security: bool | None = Field(default=None)

    @model_validator(mode="after")
    def _provider_specific_requirements(self) -> BYOConfigIn:
        if self.provider == "custom" and not (self.base_url or "").strip():
            raise ValueError("base_url requerido para provider=custom")
        if self.provider == "azure":
            if not (self.base_url or "").strip():
                raise ValueError(
                    "base_url (resource endpoint) requerido para provider=azure",
                )
            if not (self.deployment_name or "").strip():
                raise ValueError(
                    "deployment_name requerido para provider=azure",
                )
        # Modelo de amenazas B5, AM-01: `base_url` la elige el administrador del
        # inquilino y la petición sale desde dentro de nuestra red. Aquí se
        # rechaza lo que se puede juzgar sin resolver el nombre; la resolución
        # la hace `asegurar_url_externa` justo antes de cada petición.
        if (self.base_url or "").strip():
            motivo = motivo_url_insegura(self.base_url)
            if motivo:
                raise ValueError(motivo)
        return self


class BYOConfigRead(BaseModel):
    provider: str
    api_key_mask: str | None = None
    has_api_key: bool = False
    model: str | None = None
    base_url: str | None = None
    deployment_name: str | None = None
    api_version: str | None = None
    rate_limit_rpm: int | None = None
    daily_token_limit: int | None = None
    acknowledge_security: bool | None = None
    last_test_at: str | None = None
    last_test_status: Literal["ok", "fail"] | None = None
    last_test_error: str | None = None


class TenantAIProviderRead(BaseModel):
    mode: Literal["disabled", "platform", "byo"]
    byo: BYOConfigRead | None = None
    byo_catalog: list[dict] = []
    # ENH-189: instrucciones permanentes del tenant (se anexan a los
    # system prompts de minutas/reportes vía prompt_builder).
    instructions_md: str | None = None


class TenantAIProviderPatch(BaseModel):
    mode: Literal["disabled", "platform", "byo"]
    byo: BYOConfigIn | None = None
    # ENH-189: omitir = no cambiar; "" o null = borrar.
    instructions_md: str | None = Field(default=None, max_length=2000)


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
        deployment_name=byo_raw.get("deployment_name"),
        api_version=byo_raw.get("api_version"),
        rate_limit_rpm=byo_raw.get("rate_limit_rpm"),
        daily_token_limit=byo_raw.get("daily_token_limit"),
        acknowledge_security=byo_raw.get("acknowledge_security"),
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
        byo_catalog=catalog_for_api(),
        instructions_md=ai.get("instructions_md"),
    )


@router.patch("/provider", response_model=TenantAIProviderRead)
async def update_provider_config(
    body: TenantAIProviderPatch,
    cu: CurrentUser = Depends(require_capability("ai.configure")),
    db: AsyncSession = Depends(get_db),
    force: bool = Query(
        False,
        description=(
            "US-104: si true, salta el ping pre-guardado (escape hatch "
            "para casos donde el provider esté caído pero el admin "
            "necesita registrar la config igual)."
        ),
    ),
):
    tenant_id = _tenant_id(cu)
    t = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    if t is None:
        raise not_found("Tenant")

    merged = dict(t.settings or {})
    ai = dict(merged.get("ai") or {})

    # ENH-189: instrucciones permanentes del tenant (independientes del
    # modo/provider). Omitido en el PATCH = sin cambio; ""/null = borrar.
    if "instructions_md" in body.model_fields_set:
        ai["instructions_md"] = (body.instructions_md or "").strip() or None

    if body.mode == "byo":
        # BUG-060: si el tenant ya tiene una config BYO persistida, el
        # PATCH puede no incluir `byo` (p. ej. solo se está cambiando
        # `mode` de platform→byo o re-confirmando). Antes esto fallaba
        # con "byo requerido cuando mode='byo'". Ahora permitimos
        # heredar la config existente; solo se exige `byo` cuando la
        # config previa no existe o no tiene provider.
        existing_byo = ai.get("byo") if isinstance(ai.get("byo"), dict) else None
        if body.byo is None:
            if not existing_byo or not existing_byo.get("provider"):
                from app.core.errors import business_rule

                raise business_rule(
                    "byo requerido cuando mode='byo' y no hay config previa",
                )
            # Solo se está re-confirmando mode=byo (o cambiando de
            # platform→byo manteniendo la config existente). No se toca
            # `ai["byo"]`; persistimos el cambio de mode y devolvemos.
            ai["mode"] = "byo"
            t.settings = {**merged, "ai": ai}
            await write_audit(
                db,
                action="admin.ai.update_mode",
                module="admin",
                user_id=cu.id,
                tenant_id=tenant_id,
                entity_type="tenant",
                entity_id=str(tenant_id),
                details={"mode": "byo", "byo_provider": existing_byo.get("provider")},
            )
            await db.commit()
            return await get_provider_config(cu=cu, db=db)  # type: ignore[arg-type]
        if body.byo.provider not in BYO_PROVIDERS_ALLOWED:
            from app.core.errors import business_rule

            raise business_rule(
                f"Provider BYO inválido: {body.byo.provider}",
                code="BYO_PROVIDER_INVALID",
            )
        existing = ai.get("byo") if isinstance(ai.get("byo"), dict) else {}
        # US-110 CA3: provider=custom obliga ack explícito (al crear o al
        # cambiar a custom desde otro provider). Si ya estaba como custom y
        # ack=True existe en BD, se conserva.
        if body.byo.provider == "custom":
            ack = body.byo.acknowledge_security
            if ack is None and existing.get("provider") == "custom":
                ack = bool(existing.get("acknowledge_security"))
            if not ack:
                from app.core.errors import business_rule

                raise business_rule(
                    (
                        "Para conectar un proveedor custom debes confirmar "
                        "que tu tenant es responsable de la seguridad y el "
                        "cumplimiento del proveedor (acknowledge_security)."
                    ),
                    code="BYO_SECURITY_ACK_REQUIRED",
                )
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
        # US-110: persistir deployment Azure + límites + ack.
        byo["deployment_name"] = (
            body.byo.deployment_name or existing.get("deployment_name")
        )
        byo["api_version"] = body.byo.api_version or existing.get("api_version")
        byo["rate_limit_rpm"] = (
            body.byo.rate_limit_rpm
            if body.byo.rate_limit_rpm is not None
            else existing.get("rate_limit_rpm")
        )
        byo["daily_token_limit"] = (
            body.byo.daily_token_limit
            if body.byo.daily_token_limit is not None
            else existing.get("daily_token_limit")
        )
        if body.byo.provider == "custom":
            byo["acknowledge_security"] = (
                body.byo.acknowledge_security
                if body.byo.acknowledge_security is not None
                else existing.get("acknowledge_security")
            )
        else:
            byo["acknowledge_security"] = None

        # US-104: gate test-before-save. Pingueamos con la config nueva
        # antes de tocar nada en BD. Si falla y `force` es false, abortamos
        # con 422 — la config previa (incluso si está rota) se conserva.
        if not force:
            from app.services.ai_secrets import decrypt_secret

            api_key_plain = (
                body.byo.api_key
                if body.byo.api_key is not None
                else decrypt_secret(byo["api_key_encrypted"] or "")
            )
            ping = await _ping_byo_provider(
                byo["provider"], api_key_plain, byo["model"], byo["base_url"],
                deployment_name=byo.get("deployment_name"),
                api_version=byo.get("api_version"),
            )
            if not ping.ok:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "BYO_TEST_FAILED",
                        "message": (
                            f"La prueba de conexión falló: {ping.error or 'sin detalle'}. "
                            "Revisa la API key, el modelo o la base_url. "
                            "Reintenta o usa ?force=true para guardar igual."
                        ),
                        "ping_error": ping.error,
                        "ping_code": ping.code,
                        "latency_ms": ping.latency_ms,
                    },
                )
            byo["last_test_at"] = datetime.now(UTC).isoformat()
            byo["last_test_status"] = "ok"
            byo["last_test_error"] = None
        elif body.byo.api_key is not None or (
            body.byo.provider != (existing or {}).get("provider")
        ):
            # Force: cambiamos credenciales pero no se probó → invalidamos test.
            byo["last_test_at"] = None
            byo["last_test_status"] = None
            byo["last_test_error"] = None
        else:
            byo["last_test_at"] = existing.get("last_test_at")
            byo["last_test_status"] = existing.get("last_test_status")
            byo["last_test_error"] = existing.get("last_test_error")
        ai["byo"] = byo
        ai["mode"] = body.mode
    else:  # platform | disabled
        ai["mode"] = body.mode

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
    """Valida credenciales BYO con un ping mínimo antes de guardar.

    Para cada provider llama el endpoint más barato (GET /models para
    OpenAI y Gemini, POST mínimo para Claude y Perplexity). Devuelve
    ok/latency/error.
    """
    from app.services.ai_secrets import decrypt_secret

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
        deployment_name = byo_raw.get("deployment_name")
        api_version = byo_raw.get("api_version")
    else:
        provider = byo_in.provider
        api_key = byo_in.api_key or ""
        model = byo_in.model
        base_url = byo_in.base_url
        deployment_name = byo_in.deployment_name
        api_version = byo_in.api_version

    result = await _ping_byo_provider(
        provider, api_key, model, base_url,
        deployment_name=deployment_name, api_version=api_version,
    )

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
    deployment_name: str | None = None,
    api_version: str | None = None,
) -> TestConnectionResult:
    import httpx

    # Modelo de amenazas B5, AM-01. Esta función es la que convertía `base_url`
    # en un oráculo de red: devuelve estado, cuerpo y latencia al que llama. La
    # comprobación va ANTES de abrir el cliente, no dentro del `try`, para que
    # un destino rechazado no se confunda con un proveedor caído.
    if base_url:
        try:
            await asegurar_url_externa(base_url)
        except ValueError as exc:
            return TestConnectionResult(ok=False, error=str(exc), code="BASE_URL_NO_PERMITIDA")

    started = time.perf_counter()
    try:
        if provider in ("openai", "custom"):
            if not api_key:
                return TestConnectionResult(ok=False, error="api_key requerida", code="NO_KEY")
            if provider == "custom" and not base_url:
                return TestConnectionResult(
                    ok=False, error="base_url requerida", code="NO_BASE_URL",
                )
            root = (base_url or "https://api.openai.com/v1").rstrip("/")
            url = f"{root}/models"
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url, headers={"Authorization": f"Bearer {api_key}"})
            latency = int((time.perf_counter() - started) * 1000)
            # US-104: muchos servers OpenAI-compatible no exponen GET /models;
            # si vemos 404/405 caemos a un POST mínimo a /chat/completions.
            if r.status_code in (404, 405) and provider == "custom":
                async with httpx.AsyncClient(timeout=10.0) as c:
                    r2 = await c.post(
                        f"{root}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": model or "gpt-4o-mini",
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 4,
                        },
                    )
                latency = int((time.perf_counter() - started) * 1000)
                if r2.status_code >= 300:
                    return TestConnectionResult(
                        ok=False, latency_ms=latency,
                        error=f"HTTP {r2.status_code}: {r2.text[:120]}",
                        code="HTTP_ERROR",
                    )
                return TestConnectionResult(ok=True, latency_ms=latency)
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

        if provider == "azure":
            if not api_key:
                return TestConnectionResult(ok=False, error="api_key requerida", code="NO_KEY")
            if not base_url:
                return TestConnectionResult(
                    ok=False, error="resource endpoint (base_url) requerido",
                    code="NO_BASE_URL",
                )
            if not deployment_name:
                return TestConnectionResult(
                    ok=False, error="deployment_name requerido",
                    code="NO_DEPLOYMENT",
                )
            ver = api_version or "2024-02-15-preview"
            url = (
                f"{base_url.rstrip('/')}/openai/deployments/"
                f"{deployment_name}/chat/completions?api-version={ver}"
            )
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(
                    url,
                    headers={"api-key": api_key, "Content-Type": "application/json"},
                    json={
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
