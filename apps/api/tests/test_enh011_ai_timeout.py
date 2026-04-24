"""ENH-011 — AI_TIMEOUT_S env driven timeout fallback for OllamaProvider."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.ai.provider import OllamaProvider


class _FakeResponse:
    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


class _FakeAsyncClient:
    """Captura el Timeout y el payload sin tocar la red."""

    captured_timeout = None
    captured_base_url = None

    def __init__(self, *, base_url: str, timeout, headers=None):
        _FakeAsyncClient.captured_timeout = timeout
        _FakeAsyncClient.captured_base_url = base_url

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def post(self, path: str, json: dict):
        return _FakeResponse({
            "response": "ok", "prompt_eval_count": 1,
            "eval_count": 1, "total_duration": 1_000_000,
        })


def _patch_httpx():
    import httpx
    return patch.object(httpx, "AsyncClient", _FakeAsyncClient)


@pytest.mark.asyncio
async def test_tc_enh011_01_default_timeout_is_120(monkeypatch):
    """Sin override del tenant, sin env custom → timeout=120."""
    from app.core import config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "AI_TIMEOUT_S", 120, raising=False)
    with _patch_httpx():
        await OllamaProvider().generate("hola", system=None)
    assert _FakeAsyncClient.captured_timeout.read == 120.0


@pytest.mark.asyncio
async def test_tc_enh011_02_env_overrides_hardcoded(monkeypatch):
    """Con AI_TIMEOUT_S=500 → timeout=500s sin override tenant."""
    from app.core import config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "AI_TIMEOUT_S", 500, raising=False)
    with _patch_httpx():
        await OllamaProvider().generate("hola", system=None)
    assert _FakeAsyncClient.captured_timeout.read == 500.0


@pytest.mark.asyncio
async def test_tc_enh011_03_tenant_override_wins(monkeypatch):
    """Tenant override gana sobre env AI_TIMEOUT_S."""
    from app.core import config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "AI_TIMEOUT_S", 500, raising=False)
    override = {
        "base_url": "http://ollama-host.taile4df9d.ts.net:11434",
        "model": "qwen2.5:7b-instruct-q4_K_M",
        "timeout_sec": 300,
    }
    with _patch_httpx():
        await OllamaProvider().generate("hola", system=None, override=override)
    assert _FakeAsyncClient.captured_timeout.read == 300.0
    assert _FakeAsyncClient.captured_base_url == override["base_url"]
