"""BUG-081 — Import de plan lee porcentajes %-formateados como 1%.

Síntoma: una columna de avance formateada como porcentaje en Excel
(30%, 50%, 70%, 100%) se guardaba como 30/50/70/**1**. openpyxl entrega
la *fracción* de las celdas %-formateadas (1.0==100%, 0.3==30%); el
heurístico viejo solo escalaba ×100 cuando el string tenía ".", así que
100% (que openpyxl devuelve como el entero ``1``) se quedaba en 1%.

Cubre:
- TC-081.1: columna %-formateada → 0.3/0.5/0.7/1.0 escalan a 30/50/70/100.
- TC-081.2: columna numérica plana (no %) 100/30/1 se respeta tal cual.
- TC-081.3: _coerce_progress unitario (fracción, %, entero, texto).
"""
from __future__ import annotations

import io

from app.services.xlsx_task_parser import _coerce_progress, parse_xlsx


def _build_xlsx_progress(
    values: list[object], number_format: str | None = None, header: str = "Avance"
) -> bytes:
    """xlsx mínimo `Nombre | <header>` con `number_format` opcional en avance."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"
    ws.append(["Nombre", header])
    for i, v in enumerate(values, start=1):
        ws.append([f"Task {i}", v])
        if number_format:
            ws.cell(row=i + 1, column=2).number_format = number_format
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_tc081_1_percent_formatted_column_scales():
    """Celdas %-formateadas (fracción 0..1) → 0-100, incluido 100%."""
    data = _build_xlsx_progress([1.0, 0.3, 0.5, 0.7], number_format="0%")
    result = parse_xlsx(data)
    assert [t.progress for t in result.tasks] == [100, 30, 50, 70]


def test_tc081_1b_percent_format_handles_integer_one():
    """El caso crítico: 100% se almacena como el entero 1 y debía dar 100."""
    data = _build_xlsx_progress([1, 0, 0.45], number_format="0.00%")
    result = parse_xlsx(data)
    assert [t.progress for t in result.tasks] == [100, 0, 45]


def test_tc081_2_plain_integer_column_unchanged():
    """Columna numérica plana (sin formato %) se respeta: 1 == 1%, no 100%."""
    data = _build_xlsx_progress([100, 30, 1])
    result = parse_xlsx(data)
    assert [t.progress for t in result.tasks] == [100, 30, 1]


def test_tc081_3_coerce_progress_unit():
    # Fracción de celda %-formateada → ×100 siempre (incl. entero 1).
    assert _coerce_progress(1, is_percent_format=True) == 100
    assert _coerce_progress(1.0, is_percent_format=True) == 100
    assert _coerce_progress(0.3, is_percent_format=True) == 30
    assert _coerce_progress(0, is_percent_format=True) == 0
    # Sin formato %: enteros 0..100 tal cual; 1 == 1%.
    assert _coerce_progress(100) == 100
    assert _coerce_progress(1) == 1
    assert _coerce_progress(0) == 0
    # Texto con signo % o fracción literal.
    assert _coerce_progress("45%") == 45
    assert _coerce_progress("100%") == 100
    assert _coerce_progress("0.45") == 45
    # Clamp a 0..100.
    assert _coerce_progress(150) == 100
    assert _coerce_progress(-5) == 0
    assert _coerce_progress("") == 0
    assert _coerce_progress(None) == 0
