"""US-067 — Parser XLSX de tareas estilo MS Project / Excel genérico.

Auto-detecta columnas con headers en español/inglés comunes:
- Nombre: "Nombre", "Tarea", "Task Name", "Name"
- WBS: "WBS", "EDT", "Código"
- Inicio: "Inicio", "Start", "Fecha inicio", "Start Date"
- Fin: "Fin", "Finish", "Fecha fin", "Finish Date", "End Date"
- Duración: "Duración", "Duration", "Días", "Duración (días)"
- Avance: "% completado", "Progress", "%Complete", "Avance", "Avance (%)"
- Hito: "Hito", "Milestone", "Es hito"
- Predecesores: "Predecesoras", "Predecessors"
- Recursos: "Recursos", "Resources", "Responsable", "Resource Names"

Devuelve una lista de `ParsedTask` lista para persistir. Errores por fila
se acumulan en `errors` con el número de fila y el detalle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO

HEADER_ALIASES: dict[str, list[str]] = {
    "name": ["nombre", "tarea", "task name", "name", "nombre de tarea"],
    "wbs": ["wbs", "edt", "codigo", "código"],
    "start_date": ["inicio", "start", "fecha inicio", "start date", "fecha de inicio"],
    "end_date": ["fin", "finish", "fecha fin", "finish date", "end date", "fecha de fin"],
    "duration_days": [
        "duracion",
        "duración",
        "duration",
        "días",
        "dias",
        "duración (días)",
        "duracion (dias)",
    ],
    "progress": [
        "% completado",
        "%completado",
        "progress",
        "%complete",
        "avance",
        "avance (%)",
        "% avance",
    ],
    "is_milestone": ["hito", "milestone", "es hito"],
    "predecessors": ["predecesoras", "predecessors", "predecessoras"],
    "resources": [
        "recursos",
        "resources",
        "responsable",
        "resource names",
        "responsables",
    ],
}


@dataclass
class ParsedTask:
    row_number: int
    name: str
    wbs: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress: int = 0
    is_milestone: bool = False
    predecessors_raw: str | None = None
    resources_raw: str | None = None


@dataclass
class XlsxParseResult:
    tasks: list[ParsedTask] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    columns_detected: dict[str, int] = field(default_factory=dict)


def _norm(s: object) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()


def _detect_headers(header_row: list[object]) -> dict[str, int]:
    """Mapea cada header canónico → índice de columna. Columnas no
    reconocidas se ignoran."""
    detected: dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        label = _norm(cell)
        if not label:
            continue
        for canonical, aliases in HEADER_ALIASES.items():
            if label in aliases:
                detected.setdefault(canonical, idx)
                break
    return detected


def _coerce_date(v: object) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v)).date()
    except ValueError:
        return None


def _coerce_int(v: object, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(float(str(v)))
    except ValueError:
        return default


def _coerce_progress(v: object) -> int:
    """Acepta 0-100, 0-1 (float) o texto '45%'."""
    if v is None or v == "":
        return 0
    s = str(v).strip().replace("%", "")
    try:
        n = float(s)
    except ValueError:
        return 0
    if 0 <= n <= 1.0 and "." in s:
        n = n * 100
    return max(0, min(100, int(round(n))))


def _coerce_bool(v: object) -> bool:
    s = _norm(v)
    return s in {"sí", "si", "yes", "true", "1", "x", "✓"}


def parse_xlsx(data: bytes) -> XlsxParseResult:
    """Parsea XLSX en-memoria y devuelve ParsedTask + errors.

    Usa la primera hoja del workbook. La primera fila debe contener
    los headers; cualquier fila con name vacío se ignora (en vez de
    error) para tolerar filas de separador / resumen en blanco.
    """
    from openpyxl import load_workbook

    result = XlsxParseResult()
    try:
        wb = load_workbook(BytesIO(data), data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError(f"archivo XLSX inválido: {exc}") from exc

    ws = wb.active
    if ws is None:
        raise ValueError("workbook sin hojas")

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = list(next(rows_iter))
    except StopIteration:
        return result

    columns = _detect_headers(header_row)
    result.columns_detected = columns
    if "name" not in columns:
        raise ValueError(
            "No se encontró una columna 'Nombre' / 'Task Name' en la primera fila. "
            "Asegura que la hoja tenga headers estándar en la fila 1."
        )

    for offset, row in enumerate(rows_iter, start=2):
        if row is None:
            continue
        name_cell = row[columns["name"]] if columns["name"] < len(row) else None
        name = _norm(name_cell)
        if not name:
            continue
        try:
            task = ParsedTask(
                row_number=offset,
                name=str(name_cell).strip(),
                wbs=_norm(row[columns["wbs"]]) or None
                if "wbs" in columns and columns["wbs"] < len(row)
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
                predecessors_raw=_norm(row[columns["predecessors"]]) or None
                if "predecessors" in columns and columns["predecessors"] < len(row)
                else None,
                resources_raw=_norm(row[columns["resources"]]) or None
                if "resources" in columns and columns["resources"] < len(row)
                else None,
            )
            result.tasks.append(task)
        except Exception as exc:
            result.errors.append({"row": offset, "error": str(exc)})

    return result
