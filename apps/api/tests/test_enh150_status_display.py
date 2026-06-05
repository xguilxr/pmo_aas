"""ENH-150 — etiquetas ES + color leve para status de tarea."""
from __future__ import annotations

from app.services.status_display import (
    normalize_status,
    status_badge_html,
    status_es,
)


def test_status_es_maps_canonical_enum() -> None:
    assert status_es("not_started") == "No Iniciado"
    assert status_es("in_progress") == "En Progreso"
    assert status_es("completed") == "Completado"
    assert status_es("on_hold") == "En Pausa"


def test_status_es_tolerates_legacy_done() -> None:
    assert status_es("done") == "Completado"


def test_status_es_empty_and_unknown() -> None:
    assert status_es("") == "—"
    assert status_es(None) == "—"
    # desconocido (p.ej. status RAID) → valor crudo, no rompe.
    assert status_es("Open") == "Open"


def test_normalize_status_aliases_done() -> None:
    assert normalize_status("DONE") == "completed"
    assert normalize_status(" Completed ") == "completed"
    assert normalize_status(None) == ""


def test_status_badge_html_is_safe_and_labeled() -> None:
    html = status_badge_html("completed")
    assert "Completado" in html
    assert "<span" in html
    assert "background:" in html  # coloración leve inline


def test_status_badge_html_unknown_returns_escaped_text_no_badge() -> None:
    # status desconocido no fuerza un pill engañoso.
    assert status_badge_html("Open") == "Open"
    html = status_badge_html("<script>")
    assert "<span" not in html
    assert "&lt;script&gt;" in html


def test_status_badge_html_empty() -> None:
    assert status_badge_html("") == "—"
    assert status_badge_html(None) == "—"
