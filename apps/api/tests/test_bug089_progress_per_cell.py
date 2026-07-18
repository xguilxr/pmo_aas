"""BUG-089 — Escalado de porcentajes por CELDA (no por columna).

Dos síntomas que la detección por columna de BUG-081 no cubría:
1. Columna %-formateada con enteros tipeados (45 → Excel muestra 4500%):
   escalar ×100 daba 4500 → clamp → TODO el plan quedaba en 100%.
2. Formatos mixtos (algunas celdas %, otras planas): la columna entera
   se escalaba y los enteros planos también terminaban en 100%.
"""
from __future__ import annotations

import io

from app.services.xlsx_task_parser import _coerce_progress, parse_xlsx


def _build(values_with_fmt: list[tuple[object, str | None]]) -> bytes:
    """xlsx `Nombre | Avance` con number_format POR CELDA."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre", "Avance"])
    for i, (v, fmt) in enumerate(values_with_fmt, start=2):
        ws.append([f"T{i}", v])
        if fmt:
            ws.cell(row=i, column=2).number_format = fmt
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_percent_cells_with_typed_integers():
    """Enteros en celdas %-formateadas se interpretan como 0-100 literal."""
    data = _build([(45, "0%"), (80, "0%"), (0.5, "0%"), (1, "0%")])
    res = parse_xlsx(data)
    assert [t.progress for t in res.tasks] == [45, 80, 50, 100]
    codes = [w["code"] for w in res.warnings]
    assert "PROGRESS_PCT_AS_INTEGER" in codes
    warn = next(w for w in res.warnings if w["code"] == "PROGRESS_PCT_AS_INTEGER")
    assert warn["rows"] == [2, 3]  # 45 y 80; 0.5 y 1 son fracción legítima


def test_mixed_formats_per_cell():
    """Celdas planas en una columna con ALGUNAS celdas % no se escalan."""
    data = _build([(0.5, "0%"), (45, None), (100, None)])
    res = parse_xlsx(data)
    assert [t.progress for t in res.tasks] == [50, 45, 100]


def test_bug081_regression_fraction_column():
    """La corrección de BUG-081 se preserva: fracciones %-formateadas
    (incluido el entero 1 == 100%) escalan ×100."""
    data = _build([(1, "0.00%"), (0.3, "0%"), (0.7, "0%"), (0, "0%")])
    res = parse_xlsx(data)
    assert [t.progress for t in res.tasks] == [100, 30, 70, 0]
    assert res.warnings == []


def test_coerce_progress_literal_fallback_unit():
    # Entero en celda % → literal (45, no 4500-clamp-100).
    assert _coerce_progress(45, is_percent_format=True) == 45
    assert _coerce_progress(80.0, is_percent_format=True) == 80
    # Fracciones y el entero 1 siguen escalando (BUG-081).
    assert _coerce_progress(1, is_percent_format=True) == 100
    assert _coerce_progress(0.45, is_percent_format=True) == 45
    # Basura > 100 en celda % → clamp 100.
    assert _coerce_progress(150, is_percent_format=True) == 100
