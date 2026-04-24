"""US-037 — Infra compartida de exportación a PDF."""
import pytest

from app.services.pdf_renderer import render_html, render_pdf

# ENH-030: este archivo ejerce weasyprint/jinja real a propósito
# (prueba del renderer). Se excluye del smoke suite y corre en el
# job `api-tests-heavy` del CI.
pytestmark = pytest.mark.heavy


def test_us037_render_html_basic():
    html = render_html("_smoke.html", {
        "title": "Hola",
        "subtitle": "Subtítulo",
        "body": "Contenido",
        "tenant_name": "Acme",
    })
    assert "<h1>Hola</h1>" in html
    assert "Subtítulo" in html
    assert "Contenido" in html
    # generated_at inyectado por render_html
    assert "UTC" in html


def test_us037_render_pdf_returns_valid_bytes():
    pdf = render_pdf("_smoke.html", {
        "title": "Reporte de prueba",
        "subtitle": "Generado por test",
        "body": "Hola mundo con acentos: áéíóú ñ.",
        "tenant_name": "Acme",
    })
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    # Cualquier PDF válido tiene %EOF al final
    assert b"%%EOF" in pdf[-64:]


def test_us037_render_pdf_unknown_template_raises():

    with pytest.raises(Exception) as excinfo:
        render_pdf("__does_not_exist__.html", {"title": "x"})
    # Podrá ser AppError(502) si weasyprint envuelve o jinja's TemplateNotFound
    assert excinfo.value is not None


def test_us037_render_pdf_handles_unicode():
    pdf = render_pdf("_smoke.html", {
        "title": "Área — Programación",
        "subtitle": "Emoji: ✅ ⚠️",
        "body": "Café, jalapeño, piñata.",
        "tenant_name": "Tenant ÑÑ",
    })
    assert pdf.startswith(b"%PDF")
