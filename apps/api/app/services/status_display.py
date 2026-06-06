"""ENH-150 — Etiquetas en español + color leve para el status de tarea.

Fuente única de verdad para renderizar ``Task.status`` en todos los
reportes (templates Jinja PDF vía filtros, y el renderer HTML inline).
El enum canónico es ``not_started | in_progress | completed | on_hold``
(ver ``app/models/task.py``). ``done`` se tolera como alias legacy →
``completed``; ``cancelled`` se incluye por compatibilidad.

Los badges usan estilos inline (no clases CSS) para ser self-contained:
funcionan igual en el HTML standalone del renderer inline y en el PDF
de WeasyPrint, sin depender de ningún ``<style>`` externo.
"""
from __future__ import annotations

import html as _html

_LABELS: dict[str, str] = {
    "not_started": "No Iniciado",
    "in_progress": "En Progreso",
    "completed": "Completado",
    "on_hold": "En Pausa",
    "cancelled": "Cancelado",
}

# (background, color) — coloración leve, legible en claro.
_STYLES: dict[str, str] = {
    "not_started": "background:#f3f4f6;color:#374151;",
    "in_progress": "background:#dbeafe;color:#1e40af;",
    "completed": "background:#dcfce7;color:#166534;",
    "on_hold": "background:#fef9c3;color:#854d0e;",
    "cancelled": "background:#fee2e2;color:#991b1b;",
}
_DEFAULT_STYLE = "background:#f3f4f6;color:#374151;"


def normalize_status(value: object) -> str:
    """Lower-case + alias legacy ``done`` → ``completed``."""
    key = str(value or "").strip().lower()
    return "completed" if key == "done" else key


def status_es(value: object) -> str:
    """Etiqueta ES de un status de tarea; el valor crudo si es desconocido."""
    key = normalize_status(value)
    if not key:
        return "—"
    return _LABELS.get(key, str(value))


def status_badge_html(value: object) -> str:
    """``<span>`` con etiqueta ES + color leve, con estilos inline.

    HTML seguro: la etiqueta se escapa. Si el status es desconocido se
    devuelve el texto crudo (escapado) sin badge, para no forzar un pill
    engañoso sobre, p.ej., estados de items RAID.
    """
    key = normalize_status(value)
    if not key:
        return "—"
    label = _LABELS.get(key)
    if label is None:
        return _html.escape(str(value))
    style = _STYLES.get(key, _DEFAULT_STYLE)
    return (
        '<span style="display:inline-block;padding:1px 8px;border-radius:10px;'
        f'font-size:0.85em;font-weight:600;{style}">{_html.escape(label)}</span>'
    )
