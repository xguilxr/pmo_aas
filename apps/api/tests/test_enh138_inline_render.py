"""ENH-138 — preview en vivo del canvas (plantilla efímera).

Unit del helper `_resolve_template_ref`: con `section_codes` inline arma
una `ReportBuilderTemplate` efímera (sin persistir); con `template` la
pasa tal cual; sin ninguno, error de validación.
"""
from __future__ import annotations

import pytest

from app.api.v1.endpoints.report_builder_render import (
    RenderRequest,
    _resolve_template_ref,
)
from app.core.errors import AppError
from app.models.report_builder_template import ReportBuilderTemplate


def test_resolve_inline_codes_builds_ephemeral_template():
    req = RenderRequest(
        section_codes=["S-01", "S-09"],
        composition_mode="B",
        name="Mi reporte",
        level=3,
    )
    tpl = _resolve_template_ref(req)
    assert isinstance(tpl, ReportBuilderTemplate)
    assert tpl.section_codes == ["S-01", "S-09"]
    assert tpl.composition_mode == "B"
    assert tpl.name == "Mi reporte"
    assert tpl.id == "preview"


def test_resolve_inline_defaults_mode_a():
    req = RenderRequest(section_codes=["S-01"])
    tpl = _resolve_template_ref(req)
    assert tpl.composition_mode == "A"
    assert tpl.name == "Reporte custom"


def test_resolve_template_string_passthrough():
    req = RenderRequest(template="L3-AVANCE")
    assert _resolve_template_ref(req) == "L3-AVANCE"


def test_resolve_requires_template_or_codes():
    with pytest.raises(AppError):
        _resolve_template_ref(RenderRequest())
