"""Proveedores IA con selección por tenant (US-057, BUG-053).

Modos canónicos en `tenants.settings.ai.mode`:

 - `disabled`: ningún request IA (el endpoint devuelve 409).
 - `platform`: Groq (llama-3.3-70b-versatile por default) con la key
   de la plataforma compartida. Trazabilidad cross-tenant vive en
   `ai_jobs` + logs estructurados del worker.
 - `byo`: tenant trae su propio proveedor (openai / anthropic /
   perplexity / gemini) con credenciales cifradas en
   `tenants.settings.ai.byo`.

BUG-053 (2026-05-08): Ollama eliminado. La cascada legacy
`generate_with_cascade` se borró; usar `generate_for_tenant` siempre.
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


class GeminiProvider:
    name = "gemini"

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        override: dict | None = None,
    ) -> AIResult:
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
        logger.info(
            "ai.byo.gemini call model=%s timeout=60 tenant=%s",
            model, ov.get("tenant_id"),
        )
        try:
            async with httpx.AsyncClient(timeout=60.0) as c:
                r = await c.post(url, json=body)
                r.raise_for_status()
                data = r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise RuntimeError(
                f"gemini_connect_error model={model}: {type(exc).__name__}"
            ) from exc
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
        url = "https://api.anthropic.com/v1/messages"
        logger.info(
            "ai.byo.claude call url=%s model=%s timeout=90 tenant=%s",
            url, model, ov.get("tenant_id"),
        )
        try:
            async with httpx.AsyncClient(timeout=90.0) as c:
                r = await c.post(url, headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise RuntimeError(
                f"claude_connect_error url={url}: {type(exc).__name__}"
            ) from exc
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
    `platform_config.resolve_groq_config`).
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
    """BYO. API key y modelo vienen del tenant."""

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
        logger.info(
            "ai.byo.openai call base_url=%s model=%s timeout=90 tenant=%s",
            base_url, model, ov.get("tenant_id"),
        )
        try:
            async with httpx.AsyncClient(timeout=90.0) as c:
                r = await c.post(f"{base_url}/chat/completions", headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise RuntimeError(
                f"openai_connect_error base_url={base_url}: {type(exc).__name__}"
            ) from exc
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
    """BYO. API compatible con OpenAI, modelos sonar-*."""

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
        logger.info(
            "ai.byo.perplexity call base_url=%s model=%s timeout=90 tenant=%s",
            base_url, model, ov.get("tenant_id"),
        )
        try:
            async with httpx.AsyncClient(timeout=90.0) as c:
                r = await c.post(f"{base_url}/chat/completions", headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise RuntimeError(
                f"perplexity_connect_error base_url={base_url}: {type(exc).__name__}"
            ) from exc
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
    "gemini": GeminiProvider(),
    "claude": ClaudeProvider(),
    "groq": GroqProvider(),
    "openai": OpenAIProvider(),
    "perplexity": PerplexityProvider(),
    "disabled": DisabledProvider(),
}

# BUG-053 (2026-05-08): proveedores BYO whitelist (sin Ollama).
BYO_PROVIDERS: tuple[str, ...] = (
    "openai",
    "claude",
    "perplexity",
    "gemini",
)

# Alias mantenido para minimizar diff con código que importaba esta tupla.
BYO_PROVIDERS_ALLOWED: tuple[str, ...] = BYO_PROVIDERS


async def generate_for_tenant(
    prompt: str,
    *,
    system: str | None = None,
    tenant_ai_mode: str,
    platform_groq_config: dict | None = None,
    byo_config: dict | None = None,
    tenant_id: str | None = None,
    job_id: str | None = None,
) -> AIResult:
    """Enruta según `tenant_ai_mode` sin cascada.

    - `disabled`: stub. El caller debería haber chequeado esto antes y
      respondido 409.
    - `platform`: usa `GroqProvider` con la config de plataforma. No
      cae a otros proveedores (privacidad/costo).
    - `byo`: usa el provider de `byo_config['provider']`. Falla duro si
      las credenciales están mal; no cae a plataforma.
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
        override = dict(cfg)
        if tenant_id:
            override.setdefault("tenant_id", tenant_id)
        return await prov.generate(prompt, system=system, override=override)

    raise RuntimeError(f"tenant_ai_mode_invalid: {tenant_ai_mode!r}")


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
