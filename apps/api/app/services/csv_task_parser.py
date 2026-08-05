"""US-070 — Parser CSV de tareas.

Detecta delimitador (`,`, `;`, `\\t`) con `csv.Sniffer`, soporta BOM
UTF-8 y UTF-16 (LE/BE), y devuelve el mismo shape `XlsxParseResult`
que el parser XLSX para que el endpoint pueda reusar el loop de
persistencia sin ramificar por formato.

No hay concepto de hojas en CSV — `result.sheets` queda vacío y
`sheet_used` queda None.
"""
from __future__ import annotations

import csv
import io
import logging

from app.services.xlsx_task_parser import (
    SAMPLE_ROW_LIMIT,
    ParsedTask,
    XlsxParseResult,
    _coerce_bool,
    _coerce_date,
    _coerce_int,
    _coerce_progress,
    _coerce_status,
    _detect_headers,
    _norm,
    _text,
    _wbs_text,
)

logger = logging.getLogger(__name__)


def _decode(data: bytes) -> str:
    """Detecta BOM y decodifica. Fallback a UTF-8 si no hay BOM."""
    if data.startswith(b"\xff\xfe"):
        return data.decode("utf-16-le").lstrip("﻿")
    if data.startswith(b"\xfe\xff"):
        return data.decode("utf-16-be").lstrip("﻿")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"archivo CSV no es UTF-8 ni UTF-16: {exc}") from exc


def _sniff_dialect(sample: str) -> csv.Dialect:
    """Detecta delimitador entre `,`, `;`, `\\t`. Fallback a `,` si Sniffer
    no logra decidir (archivos muy cortos o una sola columna).
    """
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        logger.info("csv.Sniffer no pudo detectar delimitador, fallback a ','")

        class _Fallback(csv.excel):
            delimiter = ","

        return _Fallback()


def parse_csv(
    data: bytes,
    columns_override: dict[str, int] | None = None,
    strict: bool = True,
) -> XlsxParseResult:
    """Parsea CSV en-memoria. Shape de salida = `XlsxParseResult`.

    US-070: `columns_override` permite al wizard pasar un mapeo manual.
    `strict=False` hace que la ausencia de columna `name` no dispare
    raise (devuelve result con `tasks=[]` y sample_rows poblado para
    el preview del wizard).

    Raises:
        ValueError: archivo vacío, encoding no soportado, o (si
        strict=True) sin columna obligatoria `name`.
    """
    if not data:
        raise ValueError("archivo CSV vacío")

    text = _decode(data)
    if not text.strip():
        raise ValueError("archivo CSV sin contenido")

    # Sniffer mira las primeras 4KB — suficiente para detectar el
    # delimitador real sin cargar todo el archivo dos veces.
    dialect = _sniff_dialect(text[:4096])

    result = XlsxParseResult()
    reader = csv.reader(io.StringIO(text), dialect=dialect)

    try:
        header_row = next(reader)
    except StopIteration:
        return result

    result.sample_rows.append(list(header_row))
    columns = (
        dict(columns_override)
        if columns_override is not None
        else _detect_headers(header_row)
    )
    result.columns_detected = columns
    if "name" not in columns:
        if strict:
            raise ValueError(
                "Falta mapear la columna obligatoria 'Nombre' en el CSV. "
                "Asegurá que los headers estén en la fila 1 o enviá un "
                "mapping manual."
            )
        for row in reader:
            if not row:
                continue
            if len(result.sample_rows) <= SAMPLE_ROW_LIMIT:
                result.sample_rows.append(list(row))
            else:
                break
        return result

    for offset, row in enumerate(reader, start=2):
        if not row:
            continue
        if len(result.sample_rows) <= SAMPLE_ROW_LIMIT:
            result.sample_rows.append(list(row))
        name_cell = row[columns["name"]] if columns["name"] < len(row) else None
        name = _norm(name_cell)
        if not name:
            continue
        try:
            task = ParsedTask(
                row_number=offset,
                name=str(name_cell).strip(),
                wbs_code=_wbs_text(row[columns["wbs_code"]])
                if "wbs_code" in columns and columns["wbs_code"] < len(row)
                else None,
                start_date=_coerce_date(row[columns["start_date"]])
                if "start_date" in columns and columns["start_date"] < len(row)
                else None,
                end_date=_coerce_date(row[columns["end_date"]])
                if "end_date" in columns and columns["end_date"] < len(row)
                else None,
                duration_days=_coerce_int(row[columns["duration_days"]], default=0)
                if "duration_days" in columns and columns["duration_days"] < len(row)
                else None,
                progress=_coerce_progress(row[columns["progress"]])
                if "progress" in columns and columns["progress"] < len(row)
                else 0,
                is_milestone=_coerce_bool(row[columns["is_milestone"]])
                if "is_milestone" in columns and columns["is_milestone"] < len(row)
                else False,
                # ENH-191: estado normalizado (None si no reconocido).
                status=_coerce_status(row[columns["status"]])
                if "status" in columns and columns["status"] < len(row)
                else None,
                status_raw=_text(row[columns["status"]])
                if "status" in columns and columns["status"] < len(row)
                else None,
                criticality=(_norm(row[columns["criticality"]]) or None)
                if "criticality" in columns and columns["criticality"] < len(row)
                else None,
                is_critical=_coerce_bool(row[columns["is_critical"]])
                if "is_critical" in columns and columns["is_critical"] < len(row)
                else None,
                related_milestone_wbs=_wbs_text(row[columns["related_milestone"]])
                if "related_milestone" in columns
                and columns["related_milestone"] < len(row)
                else None,
                predecessors_raw=_wbs_text(row[columns["predecessors"]])
                if "predecessors" in columns and columns["predecessors"] < len(row)
                else None,
                resources_raw=_text(row[columns["resources"]])
                if "resources" in columns and columns["resources"] < len(row)
                else None,
            )
            result.tasks.append(task)
        except Exception as exc:
            result.errors.append({"row": offset, "error": str(exc)})

    return result
