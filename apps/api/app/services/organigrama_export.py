"""US-150 — Organigrama export (4 sheets) con openpyxl.

Genera un Excel con la estructura organizacional visible para el proyecto:
Áreas, Equipos, Roles y Recursos (actores). Mismo estilo que
`raid_export.py`: header bold con fondo del DS, freeze pane en fila 2 y
autosize best-effort. Los nombres (área/equipo/manager) se resuelven a
texto en el endpoint y se pasan ya formateados.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _autosize(ws, ncols: int) -> None:
    from openpyxl.utils import get_column_letter

    for idx in range(1, ncols + 1):
        col_letter = get_column_letter(idx)
        max_len = 0
        for cell in ws[col_letter]:
            try:
                v = "" if cell.value is None else str(cell.value)
                max_len = max(max_len, len(v))
            except Exception:
                continue
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 60)


def _write_sheet(wb, title: str, headers: list[str], rows: list[list[Any]]) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    ws = wb.create_sheet(title=title)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_align = Alignment(vertical="center")

    ws.append(headers)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    for row in rows:
        ws.append(["" if v is None else v for v in row])

    ws.freeze_panes = "A2"
    _autosize(ws, len(headers))


def export_organigrama_xlsx(
    *,
    areas_rows: list[list[Any]],
    teams_rows: list[list[Any]],
    roles_rows: list[list[Any]],
    recursos_rows: list[list[Any]],
) -> bytes:
    """Devuelve bytes XLSX con 4 sheets (Áreas/Equipos/Roles/Recursos).

    Cada `*_rows` es una lista de filas ya formateadas (nombres resueltos),
    en el orden de las columnas declaradas abajo. Sheets vacíos se incluyen
    igual con sólo el header.
    """
    from openpyxl import Workbook

    wb = Workbook()
    default_ws = wb.active
    if default_ws is not None:
        wb.remove(default_ws)

    _write_sheet(
        wb, "Áreas",
        ["ID", "Nombre", "Descripción", "Líder", "Activa"],
        areas_rows,
    )
    _write_sheet(
        wb, "Equipos",
        ["ID", "Área", "Nombre", "Descripción", "Activo"],
        teams_rows,
    )
    _write_sheet(
        wb, "Roles",
        ["ID", "Nombre", "Descripción", "Activo"],
        roles_rows,
    )
    _write_sheet(
        wb, "Recursos",
        [
            "ID", "Nombre", "Equipo", "Área", "Puesto", "Empresa",
            "Email", "Teléfono", "Manager", "Activo",
        ],
        recursos_rows,
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
