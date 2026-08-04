"""US-037 — Infra compartida de exportación a PDF."""
import pytest

from app.services.pdf_renderer import html_to_pdf, render_html, render_pdf

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


# ENH-089 / auditoría MCA 2026-08-03 (FLU-01): `html_to_pdf` es el otro
# símbolo que carga WeasyPrint, y hasta ahora ningún test heavy lo
# ejercía. Lo cubrían de rebote los tests de US-140, que el conftest
# ahora stubea junto con `render_pdf`. Sin estos casos, el render real
# de `html_to_pdf` quedaría sin cobertura en ninguna suite.
def test_us037_html_to_pdf_returns_valid_bytes():
    pdf = html_to_pdf(
        "<html><body><h1>Informe</h1><p>Contenido de prueba.</p></body></html>"
    )
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert b"%%EOF" in pdf[-64:]


def test_us037_html_to_pdf_handles_unicode():
    pdf = html_to_pdf(
        "<html><body><p>Área — Café, jalapeño, piñata. ✅</p></body></html>"
    )
    assert pdf.startswith(b"%PDF")
