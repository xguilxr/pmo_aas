"""Proveedores IA con cascada de fallback.

Orden estricto:
 1. Ollama local (default)
 2. Gemini 1.5 Flash (free tier)
 3. Claude Sonnet 4.6 (solo con API key)
Modo `disabled` devuelve stub deterministic útil para tests y fallback.
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

    async def generate(self, prompt: str, *, system: str | None = None) -> AIResult:
        import httpx

        payload = {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        timeout = httpx.Timeout(120.0, connect=5.0)
        async with httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=timeout) as c:
            r = await c.post("/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return AIResult(
                text=data.get("response", ""),
                model=f"ollama:{settings.OLLAMA_MODEL}",
                tokens_in=data.get("prompt_eval_count", 0),
                tokens_out=data.get("eval_count", 0),
                duration_ms=int((data.get("total_duration", 0) or 0) / 1_000_000),
            )


class GeminiProvider:
    name = "gemini"

    async def generate(self, prompt: str, *, system: str | None = None) -> AIResult:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("gemini_no_api_key")
        import httpx

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
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
                model=f"gemini:{settings.GEMINI_MODEL}",
                tokens_in=usage.get("promptTokenCount", 0),
                tokens_out=usage.get("candidatesTokenCount", 0),
            )


class ClaudeProvider:
    name = "claude"

    async def generate(self, prompt: str, *, system: str | None = None) -> AIResult:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("claude_no_api_key")
        import httpx

        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": settings.ANTHROPIC_MODEL,
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
                model=f"claude:{settings.ANTHROPIC_MODEL}",
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
            )


_PROVIDERS: dict[str, AIProvider] = {
    "ollama": OllamaProvider(),
    "gemini": GeminiProvider(),
    "claude": ClaudeProvider(),
    "disabled": DisabledProvider(),
}


async def generate_with_cascade(prompt: str, *, system: str | None = None) -> AIResult:
    """Intenta en orden: configured primary → gemini → disabled stub.

    Se puede inyectar un proveedor custom (por tenant) más adelante.
    """
    mode = settings.AI_MODE
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
    for name in cascade:
        prov = _PROVIDERS[name]
        try:
            return await prov.generate(prompt, system=system)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("ai provider %s failed: %s", name, exc)
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
