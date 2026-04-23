"""Proveedores IA con selección por tenant (US-057).

Hasta US-054 el sistema tenía una cascada global `AI_MODE` en env.
Desde US-057 cada tenant elige entre tres modos (`tenants.settings.ai.mode`):

 - `disabled`: ningún request IA (el endpoint devuelve 409).
 - `platform`: Groq (llama-3.1-70b-versatile por default) con la key
   de la plataforma compartida, aislamiento cross-tenant por
   `metadata.tenant_id` que Groq acepta. Scope limitado a minutas.
 - `byo`: el tenant trae su propio proveedor (OpenAI / Claude /
   Perplexity / Gemini / Ollama tailnet) con credenciales cifradas
   en `tenants.settings.ai.byo`.

La vieja cascada de env `AI_MODE` (ollama/gemini/claude/disabled) se
conserva para retro-compat hasta que todos los tenants migren a modos
`disabled|platform|byo`. `generate_with_cascade(..., tenant_ai_mode=...)`
es la nueva ruta; sin ese argumento se mantiene el comportamiento legacy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("pmoaas.ai")


@dataclass
class AIResult:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0


class AIProvider(Protocol):
    name: str

    async def generate(self, prompt: str, *, system: str | None = None) -> AIResult: ...


class DisabledProvider:
    name = "disabled"

    async def generate(self, prompt: str, *, system: str | None = None) -> AIResult:
        snippet = prompt[:200].replace("\n", " ")
        text = f"[AI disabled — mock]\nSystem={system}\nPrompt_head={snippet!r}"
        return AIResult(text=text, model="stub", tokens_in=0, tokens_out=len(text) // 4)


class OllamaProvider:
    name = "ollama"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
        """Llama a Ollama.

        US-048: si `override` trae `base_url`/`model`/`timeout_sec` del
        tenant (leídos desde `tenants.settings.ai.ollama`), se usan para
        este call; en caso contrario cae a los env `OLLAMA_BASE_URL` /
        `OLLAMA_MODEL`. Esto permite que cada tenant apunte a su propio
        endpoint tailnet sin tocar env del worker.

        ENH-011: el fallback del timeout total de httpx ahora viene de
        `settings.AI_TIMEOUT_S` (default 120s). Antes estaba hardcoded.
        Orden de prioridad: override tenant > env AI_TIMEOUT_S > 120s.
        """
        import httpx

        ov = override or {}
        base_url = str(ov.get("base_url") or settings.OLLAMA_BASE_URL).rstrip("/")
        model = str(ov.get("model") or settings.OLLAMA_MODEL)
        timeout_total = float(ov.get("timeout_sec") or settings.AI_TIMEOUT_S)

        payload = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        timeout = httpx.Timeout(timeout_total, connect=5.0)
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as c:
                r = await c.post("/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                return AIResult(
                    text=data.get("response", ""),
                    model=f"ollama:{model}",
                    tokens_in=data.get("prompt_eval_count", 0),
                    tokens_out=data.get("eval_count", 0),
                    duration_ms=int((data.get("total_duration", 0) or 0) / 1_000_000),
                )
        except Exception as exc:
            raise RuntimeError(f"ollama@{base_url} model={model}: {type(exc).__name__}: {exc}") from exc


class GeminiProvider:
    name = "gemini"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
        """US-057: `override` permite inyectar api_key/model del tenant
        (modo BYO). Si no hay override cae a los env globales."""
        ov = override or {}
        api_key = ov.get("api_key") or settings.GEMINI_API_KEY
        model = ov.get("model") or settings.GEMINI_MODEL
        if not api_key:
            raise RuntimeError("gemini_no_api_key")
        import httpx

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        parts = [{"text": prompt}]
        body = {"contents": [{"role": "user", "parts": parts}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(url, json=body)
            r.raise_for_status()
            data = r.json()
            text = ""
            for cand in data.get("candidates", []):
                for p in cand.get("content", {}).get("parts", []):
                    text += p.get("text", "")
            usage = data.get("usageMetadata", {})
            return AIResult(
                text=text,
                model=f"gemini:{model}",
                tokens_in=usage.get("promptTokenCount", 0),
                tokens_out=usage.get("candidatesTokenCount", 0),
            )


class ClaudeProvider:
    name = "claude"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
        ov = override or {}
        api_key = ov.get("api_key") or settings.ANTHROPIC_API_KEY
        model = ov.get("model") or settings.ANTHROPIC_MODEL
        if not api_key:
            raise RuntimeError("claude_no_api_key")
        import httpx

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        async with httpx.AsyncClient(timeout=90.0) as c:
            r = await c.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            text = "".join(
                b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
            )
            usage = data.get("usage", {})
            return AIResult(
                text=text,
                model=f"claude:{model}",
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
            )


class GroqProvider:
    """IA base de la plataforma (US-057, modo `platform`).

    API OpenAI-compatible bajo `https://api.groq.com/openai/v1`. La key
    y el modelo se resuelven desde `platform_ai_settings` (ver
    `platform_config.resolve_groq_config`). Cada call lleva
    `metadata.tenant_id` + `metadata.job_id` para trazabilidad cross-
    tenant en el dashboard de uso del superadmin.
    """

    name = "groq"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
        ov = override or {}
        api_key = ov.get("api_key") or settings.GROQ_API_KEY
        model = ov.get("model") or settings.GROQ_MODEL
        if not api_key:
            raise RuntimeError("groq_no_api_key")
        import httpx

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict = {"model": model, "messages": messages, "stream": False}
        # Trazabilidad cross-tenant para el dashboard + soporte Groq.
        metadata: dict = {}
        if ov.get("tenant_id"):
            metadata["tenant_id"] = ov["tenant_id"]
        if ov.get("job_id"):
            metadata["job_id"] = ov["job_id"]
        if metadata:
            body["metadata"] = metadata
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90.0) as c:
            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=body,
            )
            r.raise_for_status()
            data = r.json()
            text = ""
            choices = data.get("choices") or []
            if choices:
                text = choices[0].get("message", {}).get("content", "") or ""
            usage = data.get("usage", {})
            return AIResult(
                text=text,
                model=f"groq:{model}",
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )


class OpenAIProvider:
    """BYO (US-057). API key y modelo vienen del tenant."""

    name = "openai"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
        ov = override or {}
        api_key = ov.get("api_key")
        if not api_key:
            raise RuntimeError("openai_no_api_key")
        model = ov.get("model") or "gpt-4o-mini"
        base_url = str(ov.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        import httpx

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {"model": model, "messages": messages, "stream": False}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90.0) as c:
            r = await c.post(f"{base_url}/chat/completions", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            text = ""
            choices = data.get("choices") or []
            if choices:
                text = choices[0].get("message", {}).get("content", "") or ""
            usage = data.get("usage", {})
            return AIResult(
                text=text,
                model=f"openai:{model}",
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )


class PerplexityProvider:
    """BYO (US-057). API compatible con OpenAI, modelos sonar-*."""

    name = "perplexity"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
        ov = override or {}
        api_key = ov.get("api_key")
        if not api_key:
            raise RuntimeError("perplexity_no_api_key")
        model = ov.get("model") or "sonar"
        base_url = str(ov.get("base_url") or "https://api.perplexity.ai").rstrip("/")
        import httpx

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {"model": model, "messages": messages, "stream": False}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90.0) as c:
            r = await c.post(f"{base_url}/chat/completions", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            text = ""
            choices = data.get("choices") or []
            if choices:
                text = choices[0].get("message", {}).get("content", "") or ""
            usage = data.get("usage", {})
            return AIResult(
                text=text,
                model=f"perplexity:{model}",
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )


_PROVIDERS: dict[str, AIProvider] = {
    "ollama": OllamaProvider(),
    "gemini": GeminiProvider(),
    "claude": ClaudeProvider(),
    "groq": GroqProvider(),
    "openai": OpenAIProvider(),
    "perplexity": PerplexityProvider(),
    "disabled": DisabledProvider(),
}

# US-057: proveedores válidos para modo BYO. `ollama` absorbió US-048
# como sub-caso (base_url = tailnet del tenant).
BYO_PROVIDERS: tuple[str, ...] = (
    "openai",
    "claude",
    "perplexity",
    "gemini",
    "ollama",
)


async def generate_for_tenant(
    prompt: str,
    *,
    system: str | None = None,
    tenant_ai_mode: str,
    platform_groq_config: dict | None = None,
    byo_config: dict | None = None,
    tenant_ollama_config: dict | None = None,
    tenant_id: str | None = None,
    job_id: str | None = None,
) -> AIResult:
    """Ruta nueva (US-057): enruta según `tenant_ai_mode` sin cascada.

    - `disabled`: no se llama IA. El caller debe haber chequeado esto
      antes y devolver 409; esta función si se invoca devuelve el stub.
    - `platform`: usa `GroqProvider` con la config de plataforma. No cae
      a otros proveedores (owner dixit — privacidad/costo); 3 reintentos
      internos se hacen en el `GroqProvider.generate` del caller.
    - `byo`: usa el provider de `byo_config['provider']`. Falla duro si
      las credenciales están mal; no cae a plataforma (ídem).
    """
    if tenant_ai_mode == "disabled":
        return await _PROVIDERS["disabled"].generate(prompt, system=system)

    if tenant_ai_mode == "platform":
        cfg = dict(platform_groq_config or {})
        if tenant_id:
            cfg.setdefault("tenant_id", tenant_id)
        if job_id:
            cfg.setdefault("job_id", job_id)
        return await _PROVIDERS["groq"].generate(
            prompt, system=system, override=cfg,
        )

    if tenant_ai_mode == "byo":
        cfg = byo_config or {}
        provider_name = cfg.get("provider")
        if provider_name not in BYO_PROVIDERS:
            raise RuntimeError(f"byo_provider_invalid: {provider_name!r}")
        prov = _PROVIDERS[provider_name]
        # Ollama BYO puede heredar el legacy de US-048 cuando migremos.
        override = dict(cfg)
        if provider_name == "ollama" and tenant_ollama_config:
            override = {**tenant_ollama_config, **cfg}
        return await prov.generate(prompt, system=system, override=override)

    raise RuntimeError(f"tenant_ai_mode_invalid: {tenant_ai_mode!r}")


async def generate_with_cascade(
    prompt: str,
    *,
    system: str | None = None,
    tenant_ollama_config: dict | None = None,
    ai_mode_override: str | None = None,
) -> AIResult:
    """Intenta en orden: configured primary → gemini → disabled stub.

    US-048: `tenant_ollama_config`, si se pasa, se inyecta solo al
    `OllamaProvider` para que use el endpoint tailnet del tenant en vez
    del env global. Los demás providers ignoran el parámetro.

    US-054: `ai_mode_override` permite al worker Celery pasar el modo
    efectivo resuelto desde `platform_ai_settings` (superadmin) en vez
    de leer `settings.AI_MODE` del env. Si es None, cae al env.
    """
    mode = ai_mode_override or settings.AI_MODE
    if mode == "disabled":
        return await _PROVIDERS["disabled"].generate(prompt, system=system)

    cascade: list[str] = []
    if mode == "ollama":
        cascade = ["ollama", "gemini", "claude", "disabled"]
    elif mode == "gemini":
        cascade = ["gemini", "ollama", "claude", "disabled"]
    elif mode == "claude":
        cascade = ["claude", "gemini", "ollama", "disabled"]
    else:
        cascade = ["disabled"]

    last_err: Exception | None = None
    for idx, name in enumerate(cascade):
        prov = _PROVIDERS[name]
        try:
            if name == "ollama" and tenant_ollama_config:
                return await prov.generate(
                    prompt, system=system, override=tenant_ollama_config,
                )
            return await prov.generate(prompt, system=system)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            next_name = cascade[idx + 1] if idx + 1 < len(cascade) else None
            # Mensaje con razón visible en logs estándar; extras para el
            # futuro exporter Prometheus ai_cascade_fallback_total{from,to}.
            logger.warning(
                "ai_cascade_fallback from=%s to=%s err=%s: %s",
                name, next_name, type(exc).__name__, str(exc)[:200],
                extra={
                    "ai_provider_from": name,
                    "ai_provider_to": next_name,
                    "ai_cascade_error": str(exc)[:200],
                },
            )
            continue
    raise RuntimeError(f"all ai providers failed: {last_err}")


def chunk_text(text: str, *, max_tokens: int = 3000, overlap_tokens: int = 200) -> list[str]:
    """Chunk by approximate tokens (~4 chars/token). Overlap preserves context."""
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap_chars
    return chunks
