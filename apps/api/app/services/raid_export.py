"""RAID export 4 sheets (ENH-082).

Genera un Excel con 4 sheets dedicados (Risks / Issues / Lessons / Changes),
header row en negrita con fondo del DS, freeze pane en fila 2 y autosize
column width best-effort. Sheets vacíos se incluyen igual con header (CA5).

Reusa los mismos modelos de `app.models.modules`. Sin cambio de schema.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

from app.models.modules import ChangeRequest, Issue, Lesson, Risk

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Column definitions: (header_label, attribute_name) — orden = orden en sheet.
RISK_COLS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Folio", "folio"),
    ("Título", "title"),
    ("Descripción", "description"),
    ("Categoría", "category"),
    ("Probabilidad", "probability"),
    ("Impacto", "impact"),
    ("Severidad", "severity"),
    ("Estrategia de mitigación", "mitigation_strategy"),
    ("Owner ID", "owner_id"),
    ("Actor responsable", "owner_actor_id"),
    ("Área", "area_id"),
    ("Identificado", "identified_at"),
    ("Vencimiento", "due_date"),
    ("Status", "status"),
    ("Nota de cierre", "closure_note"),
    ("Creado", "created_at"),
    ("Actualizado", "updated_at"),
]

ISSUE_COLS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Folio", "folio"),
    ("Tipo", "type"),
    ("Título", "title"),
    ("Descripción", "description"),
    ("Prioridad", "priority"),
    ("Reportado", "reported_at"),
    ("Compromiso", "committed_date"),
    ("Resolución", "resolution"),
    ("Owner ID", "owner_id"),
    ("Actor responsable", "owner_actor_id"),
    ("Área", "area_id"),
    ("Status", "status"),
    ("Creado", "created_at"),
    ("Actualizado", "updated_at"),
]

LESSON_COLS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Folio", "folio"),
    ("Categoría", "category"),
    ("Fase", "phase"),
    ("Título", "title"),
    ("Descripción", "description"),
    ("Recomendación", "recommendation"),
    ("Tags", "tags"),
    ("Status", "status"),
    ("Creado", "created_at"),
    ("Actualizado", "updated_at"),
]

CHANGE_COLS: list[tuple[str, str]] = [
    ("ID", "id"),
    ("Folio", "folio"),
    ("Tipo", "type"),
    ("Título", "title"),
    ("Descripción", "description"),
    ("Impacto", "impact"),
    ("Solicitado por", "requested_by"),
    ("Solicitado", "requested_at"),
    ("Aprobado por", "approved_by"),
    ("Aprobado", "approved_at"),
    ("Status", "status"),
    ("Creado", "created_at"),
    ("Actualizado", "updated_at"),
]


def _cell_value(value: Any) -> Any:
    """Convierte tipos no-Excel-friendly. tz-aware datetimes → naive (Excel
    no acepta tz). Listas/dicts → JSON-ish string."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return value
    if isinstance(value, (list, dict)):
        return ", ".join(str(x) for x in value) if isinstance(value, list) else str(value)
    return value


def _autosize(ws, cols: list[tuple[str, str]]) -> None:
    """Best-effort: ancho = max(longitud header, longitud max valor en col),
    cap a 60. Suficiente para vista presentable; usuario puede ajustar."""
    from openpyxl.utils import get_column_letter

    for idx, (header, _) in enumerate(cols, start=1):
        max_len = len(str(header))
        col_letter = get_column_letter(idx)
        for cell in ws[col_letter]:
            try:
                v = "" if cell.value is None else str(cell.value)
                if len(v) > max_len:
                    max_len = len(v)
            except Exception:
                continue
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)


def _write_sheet(wb, title: str, cols: list[tuple[str, str]], rows: list[Any]) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    ws = wb.create_sheet(title=title)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_align = Alignment(vertical="center")

    headers = [h for h, _ in cols]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    for item in rows:
        ws.append([_cell_value(getattr(item, attr, None)) for _, attr in cols])

    # Freeze pane: fila 2 (header sticky).
    ws.freeze_panes = "A2"
    _autosize(ws, cols)


def export_raid_xlsx(
    *,
    risks: list[Risk],
    issues: list[Issue],
    lessons: list[Lesson],
    changes: list[ChangeRequest],
) -> bytes:
    """Devuelve bytes XLSX con 4 sheets (CA1). Sheets vacíos se incluyen
    igual con sólo header row (CA5)."""
    from openpyxl import Workbook

    wb = Workbook()
    # Workbook trae 1 sheet default; lo eliminamos para tener orden controlado.
    default_ws = wb.active
    if default_ws is not None:
        wb.remove(default_ws)

    _write_sheet(wb, "Risks", RISK_COLS, risks)
    _write_sheet(wb, "Issues", ISSUE_COLS, issues)
    _write_sheet(wb, "Lessons", LESSON_COLS, lessons)
    _write_sheet(wb, "Changes", CHANGE_COLS, changes)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
