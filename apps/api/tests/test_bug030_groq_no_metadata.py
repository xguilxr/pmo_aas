"""BUG-030: verificar que GroqProvider NO inyecta campo `metadata` al body.

Contexto: Groq usa la API OpenAI-compatible de Chat Completions, que
rechaza con 400 cualquier clave desconocida en el body. El campo
`metadata` (solo presente en la API de Assistants/Responses de OpenAI)
no es aceptado. El bug rompía completamente minutas en modo `platform`.

Este test lockea el contrato para que no vuelva a aparecer por error.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai.provider import GroqProvider


@pytest.mark.asyncio
async def test_bug030_groq_body_does_not_include_metadata():
    """El body enviado a Groq no debe contener `metadata`, aunque el
    caller pase tenant_id/job_id en el override."""

    captured_body: dict = {}

    class _MockResponse:
        status_code = 200

        def json(self) -> dict:
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

        def raise_for_status(self) -> None:
            return None

    async def _fake_post(self, url, *, headers, json=None, **kwargs):  # noqa: A002
        nonlocal captured_body
        captured_body = json or {}
        return _MockResponse()

    with patch("httpx.AsyncClient.post", new=_fake_post):
        provider = GroqProvider()
        result = await provider.generate(
            "test prompt",
            system="test system",
            override={
                "api_key": "gsk_test",
                "model": "llama-3.3-70b-versatile",
                "tenant_id": "tenant-abc",
                "job_id": "job-xyz",
            },
        )

    assert "metadata" not in captured_body, (
        f"Groq body should not contain 'metadata' key, got: "
        f"{json.dumps(captured_body, indent=2)}"
    )
    # Sanity: sí debe tener los campos OpenAI-standard.
    assert captured_body["model"] == "llama-3.3-70b-versatile"
    assert captured_body["messages"][0]["role"] == "system"
    assert captured_body["messages"][1]["role"] == "user"
    assert captured_body["stream"] is False
    # Sanity: el result se parsea normal.
    assert result.text == "ok"
    assert result.model == "groq:llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_bug030_groq_body_fields_whitelist():
    """Hardening: el body de Groq solo debe contener claves whitelisted.

    Si alguien agrega una nueva clave al body de GroqProvider.generate,
    este test la detecta y obliga a validar que Groq la acepta (o
    documentar el cambio)."""

    captured_body: dict = {}

    class _MockResponse:
        status_code = 200

        def json(self) -> dict:
            return {"choices": [{"message": {"content": ""}}], "usage": {}}

        def raise_for_status(self) -> None:
            return None

    async def _fake_post(self, url, *, headers, json=None, **kwargs):  # noqa: A002
        nonlocal captured_body
        captured_body = json or {}
        return _MockResponse()

    with patch("httpx.AsyncClient.post", new=_fake_post):
        provider = GroqProvider()
        await provider.generate(
            "hello",
            override={"api_key": "gsk_test", "model": "llama-3.3-70b-versatile"},
        )

    # Si Groq documenta más claves oficialmente soportadas, agregarlas aquí.
    allowed_keys = {"model", "messages", "stream"}
    unexpected = set(captured_body.keys()) - allowed_keys
    assert not unexpected, (
        f"Unexpected keys in Groq body: {unexpected}. "
        f"If you added a field, confirm Groq accepts it (test against "
        f"api.groq.com directly) before updating the whitelist."
    )
