"""Plan regenerator (ENH-080).

Regenera el archivo del Plan on-demand a partir de las tareas en DB.
DB es la fuente de verdad; el archivo se reconstruye preservando el formato
origen detectado al subir (`source_format` ∈ {mpp, xlsx, csv, template}).

- xlsx / template → openpyxl con plantilla mínima (headers + filas).
- csv             → flat export sin fórmulas.
- mpp             → MS Project binario es write-only via MPXJ writer (Java);
  no soportado en este sprint. Fallback: regenera xlsx y devuelve header
  `X-Plan-Format-Fallback: xlsx-mpp-not-supported` para que la UI muestre
  warning. Limitación documentada en US-310 CA3.
"""
from __future__ import annotations

import csv
from io import BytesIO, StringIO

from app.models.task import Task

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME = "text/csv"

PLAN_HEADERS = [
    "WBS",
    "Nombre",
    "Inicio",
    "Fin",
    "Duración (días)",
    "Avance (%)",
    "Hito",
    "Estado",
    "Criticidad",
    "Outline",
]


def _row(task: Task) -> list[object]:
    return [
        task.wbs or "",
        task.name or "",
        task.start_date.isoformat() if task.start_date else "",
        task.end_date.isoformat() if task.end_date else "",
        task.duration_days if task.duration_days is not None else "",
        task.progress if task.progress is not None else 0,
        "Sí" if task.is_milestone else "No",
        task.status or "",
        getattr(task, "criticality", None) or "",
        task.outline_level if task.outline_level is not None else "",
    ]


def regenerate_xlsx(tasks: list[Task]) -> bytes:
    """xlsx: 1 sheet "Plan" con headers + filas. Compatible con la
    plantilla de import (US-096) en el sentido de que los nombres de
    columnas coinciden, así un round-trip download → re-upload preserva
    los datos."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet("Plan")
    else:
        ws.title = "Plan"
    ws.append(PLAN_HEADERS)
    for t in tasks:
        ws.append(_row(t))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def regenerate_csv(tasks: list[Task]) -> bytes:
    """csv flat (UTF-8 sin BOM). Misma columna order que xlsx."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(PLAN_HEADERS)
    for t in tasks:
        writer.writerow(_row(t))
    return buf.getvalue().encode("utf-8")


def regenerate_for_format(
    fmt: str, tasks: list[Task]
) -> tuple[bytes, str, str, bool]:
    """Devuelve `(bytes, mime, ext, fallback_used)`.

    `fallback_used=True` cuando el formato pedido era `mpp` y se cayó a xlsx.
    """
    fmt = (fmt or "xlsx").lower()
    if fmt == "csv":
        return regenerate_csv(tasks), CSV_MIME, "csv", False
    if fmt == "mpp":
        # MPP write requiere MPXJ Pro / paquete comercial; no viable en
        # plataforma. Fallback a xlsx con warning header (US-310 CA3).
        return regenerate_xlsx(tasks), XLSX_MIME, "xlsx", True
    # xlsx | template | desconocido → xlsx default.
    return regenerate_xlsx(tasks), XLSX_MIME, "xlsx", False
