"""Infra compartida para render HTML → PDF (US-037).

Motor oficial: WeasyPrint. Plantillas Jinja2 en `app/templates/pdf/`.
Llamar `render_pdf(template_name, context)` devuelve `bytes` con el
documento PDF listo para servir como respuesta HTTP.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import AppError

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "pdf"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _format_datetime(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return ""
    return value.strftime(fmt)


_env.filters["format_datetime"] = _format_datetime


def render_html(template_name: str, context: dict[str, Any]) -> str:
    """Renderiza una plantilla Jinja2 a HTML string."""
    tpl = _env.get_template(template_name)
    ctx = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        **context,
    }
    return tpl.render(**ctx)


def render_pdf(template_name: str, context: dict[str, Any]) -> bytes:
    """Renderiza plantilla Jinja2 → HTML → PDF (WeasyPrint)."""
    html = render_html(template_name, context)
    try:
        from weasyprint import HTML  # import tardío para evitar costo al arranque
    except Exception as exc:  # pragma: no cover - dep. ausente
        logger.exception("weasyprint missing or broken: %s", exc)
        raise AppError(
            502,
            "PDF_ENGINE_UNAVAILABLE",
            "Motor PDF no disponible",
            {"template": template_name},
        ) from exc
    try:
        return HTML(string=html, base_url=str(_TEMPLATES_DIR)).write_pdf()
    except Exception as exc:
        logger.exception("pdf render failed for %s: %s", template_name, exc)
        raise AppError(
            502,
            "PDF_RENDER_FAILED",
            "No se pudo generar el PDF",
            {"template": template_name, "error": str(exc)[:200]},
        ) from exc
