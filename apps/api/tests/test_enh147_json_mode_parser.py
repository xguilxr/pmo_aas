"""ENH-147 — confiabilidad Minutas→RAID.

Cubre las dos piezas centrales del fix:
1. `parse_json_lenient`: tolera fences ```json, comas colgantes, JSON
   envuelto en prosa, y NO corrompe URLs con `//` dentro de strings.
2. `json_mode`: los proveedores OpenAI-compatibles inyectan
   `response_format={"type":"json_object"}` solo cuando se pide.
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.services.ai.json_parse import parse_json_lenient
from app.services.ai.provider import GroqProvider

# Captura el generate REAL antes de que conftest._stub_ai_providers lo
# reemplace con el stub DisabledProvider.
_GROQ_GENERATE = GroqProvider.generate


def test_parse_lenient_plain_object():
    assert parse_json_lenient('{"a": 1, "b": [2, 3]}') == {"a": 1, "b": [2, 3]}


def test_parse_lenient_strips_json_fences():
    assert parse_json_lenient('```json\n{"raid": []}\n```') == {"raid": []}


def test_parse_lenient_trailing_comma():
    assert parse_json_lenient('{"x": 1, "y": 2,}') == {"x": 1, "y": 2}


def test_parse_lenient_prose_wrapped():
    text = 'Claro, aquí está: {"type": "A", "description": "x"} ¿algo más?'
    assert parse_json_lenient(text) == {"type": "A", "description": "x"}


def test_parse_lenient_does_not_corrupt_urls():
    # `//` dentro de un string NO debe ser tratado como comentario.
    assert parse_json_lenient('{"u": "https://x.com/a//b"}') == {
        "u": "https://x.com/a//b"
    }


def test_parse_lenient_returns_none_on_garbage():
    assert parse_json_lenient("no hay json aquí") is None
    assert parse_json_lenient("") is None
    assert parse_json_lenient(None) is None


class _FakeResp:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


@pytest.mark.asyncio
async def test_groq_json_mode_sets_response_format():
    captured: dict = {}

    async def _fake_post(self, url, **kwargs):
        captured.update(kwargs.get("json") or {})
        return _FakeResp()

    with patch.object(httpx.AsyncClient, "post", _fake_post):
        await _GROQ_GENERATE(
            GroqProvider(),
            "dame json",
            system="sys",
            override={"api_key": "k", "model": "m"},
            json_mode=True,
        )
    assert captured.get("response_format") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_groq_without_json_mode_omits_response_format():
    captured: dict = {}

    async def _fake_post(self, url, **kwargs):
        captured.update(kwargs.get("json") or {})
        return _FakeResp()

    with patch.object(httpx.AsyncClient, "post", _fake_post):
        await _GROQ_GENERATE(
            GroqProvider(),
            "texto libre",
            system="sys",
            override={"api_key": "k", "model": "m"},
            json_mode=False,
        )
    assert "response_format" not in captured
