"""Infra compartida para render HTML → PDF (US-037).

Motor oficial: WeasyPrint. Plantillas Jinja2 en `app/templates/pdf/`.
Llamar `render_pdf(template_name, context)` devuelve `bytes` con el
documento PDF listo para servir como respuesta HTTP.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from app.core.errors import AppError
from app.services.status_display import status_badge_html, status_es

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
# ENH-150 — status de tarea en ES con color leve.
_env.filters["status_es"] = status_es
_env.filters["status_badge"] = lambda value: Markup(status_badge_html(value))


def render_html(template_name: str, context: dict[str, Any]) -> str:
    """Renderiza una plantilla Jinja2 a HTML string."""
    tpl = _env.get_template(template_name)
    ctx = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
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


def html_to_pdf(html_content: str) -> bytes:
    """ENH-089: convierte un HTML standalone (con estilos inline) en PDF
    via WeasyPrint. Usa la versión print-friendly del HTML implícitamente
    a través del media query `@media print` que ya hemos añadido en el
    template (oculta inputs de filtro en print).
    """
    try:
        from weasyprint import HTML
    except Exception as exc:  # pragma: no cover - dep. ausente
        logger.exception("weasyprint missing or broken: %s", exc)
        raise AppError(
            502,
            "PDF_ENGINE_UNAVAILABLE",
            "Motor PDF no disponible",
            {},
        ) from exc
    try:
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("html_to_pdf failed: %s", exc)
        raise AppError(
            502,
            "PDF_RENDER_FAILED",
            "No se pudo generar el PDF",
            {"error": str(exc)[:200]},
        ) from exc


def html_to_text(html_content: str) -> str:
    """ENH-089 CA3: flatten HTML → texto plano simple. Útil para
    minutas/reportes que se pegan en email. Implementación intencionalmente
    simple (regex) para no traer una dependencia más; preserva listas y
    saltos de párrafo.
    """
    import re

    s = html_content
    # Normaliza saltos antes de etiquetas de bloque.
    s = re.sub(
        r"</(?:p|div|li|tr|h[1-6]|details|section|header|footer)>",
        "\n",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<li[^>]*>", "  • ", s, flags=re.IGNORECASE)
    s = re.sub(r"<th[^>]*>|<td[^>]*>", "  ", s, flags=re.IGNORECASE)
    s = re.sub(r"</(?:th|td)>", "  |", s, flags=re.IGNORECASE)
    s = re.sub(r"</tr>", "\n", s, flags=re.IGNORECASE)
    # Escapa el resto.
    s = re.sub(r"<[^>]+>", "", s)
    # Decode HTML entities básicas.
    import html as _htmllib
    s = _htmllib.unescape(s)
    # Compacta espacios y deja máximo 2 saltos seguidos.
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s
