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
    "criticality": ["criticidad", "criticality", "prioridad criticidad"],
    # ENH-097: columna boolean explicita is_critical (Sprint 26 / EP020).
    "is_critical": ["is_critical", "es critico", "es crítico", "critico", "crítico"],
    "related_milestone": [
        "hito relacionado",
        "related milestone",
        "milestone relacionado",
    ],
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
    # US-096: criticidad + hito relacionado opcionales en plantilla.
    criticality: str | None = None
    # ENH-097: boolean explicito. None = no presente en plantilla (caller
    # debe derivarlo de criticality).
    is_critical: bool | None = None
    related_milestone_wbs: str | None = None
    predecessors_raw: str | None = None
    resources_raw: str | None = None


@dataclass
class XlsxParseResult:
    tasks: list[ParsedTask] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    columns_detected: dict[str, int] = field(default_factory=dict)
    # US-070: hojas disponibles en el workbook. Vacío para CSV/MPP;
    # solo el parser XLSX lo puebla. El wizard lo usa en el step 2
    # (sheet selector) cuando hay más de una hoja.
    sheets: list[str] = field(default_factory=list)
    # US-070: primeras N filas crudas (incluye header) para que el
    # wizard pueda renderizar el preview + re-mapeo de columnas antes
    # del confirm. Cada elemento es una lista de celdas tal como vino
    # del parser (sin coerción).
    sample_rows: list[list[object]] = field(default_factory=list)
    # US-070: nombre de la hoja efectivamente parseada. En Excel con
    # varias hojas el caller puede elegir; en CSV/MPP queda None.
    sheet_used: str | None = None


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
    return max(0, min(100, round(n)))


def _coerce_bool(v: object) -> bool:
    s = _norm(v)
    return s in {"sí", "si", "yes", "true", "1", "x", "✓"}


SAMPLE_ROW_LIMIT = 10


def parse_xlsx(
    data: bytes,
    sheet: str | None = None,
    columns_override: dict[str, int] | None = None,
    strict: bool = True,
) -> XlsxParseResult:
    """Parsea XLSX en-memoria y devuelve ParsedTask + errors.

    US-070: acepta `sheet` opcional para elegir hoja específica,
    `columns_override` para mapeo manual (reemplaza totalmente la
    auto-detección) y `strict` que controla qué pasa cuando no hay
    columna `name`:

    - `strict=True` (default): raise ValueError. Caller se rompe si
      el archivo no tiene el header esperado.
    - `strict=False`: devuelve `XlsxParseResult` con `tasks=[]` y
      `sample_rows[]` poblado. Útil para el preview del wizard donde
      el usuario va a re-mappear columnas manualmente.
    """
    from openpyxl import load_workbook

    result = XlsxParseResult()
    try:
        wb = load_workbook(BytesIO(data), data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError(f"archivo XLSX inválido: {exc}") from exc

    result.sheets = list(wb.sheetnames)
    if sheet is not None:
        if sheet not in result.sheets:
            raise ValueError(
                f"hoja '{sheet}' no existe en el workbook (disponibles: "
                f"{', '.join(result.sheets)})"
            )
        ws = wb[sheet]
    else:
        ws = wb.active
    if ws is None:
        raise ValueError("workbook sin hojas")
    result.sheet_used = ws.title

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = list(next(rows_iter))
    except StopIteration:
        return result

    # Sample para el wizard: header + hasta N data rows. Se guarda
    # antes de iterar el resto para no consumir el iterator.
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
                "Falta mapear la columna obligatoria 'Nombre'. Asegurá que la "
                "hoja tenga headers estándar en la fila 1 o enviá un mapping "
                "manual."
            )
        # Modo preview: seguimos poblando sample_rows y devolvemos el
        # result parcial para que el wizard pueda mostrarle los headers
        # al usuario y que mapee manualmente.
        for row in rows_iter:
            if row is None:
                continue
            if len(result.sample_rows) <= SAMPLE_ROW_LIMIT:
                result.sample_rows.append(list(row))
            else:
                break
        return result

    for offset, row in enumerate(rows_iter, start=2):
        if row is None:
            continue
        # US-070: acumulá sample rows hasta el límite — antes del
        # filtro por `name` para que el wizard pueda mostrar incluso
        # filas que el parser actual descarta (ej. resumenes en blanco).
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
                criticality=(_norm(row[columns["criticality"]]) or None)
                if "criticality" in columns and columns["criticality"] < len(row)
                else None,
                is_critical=_coerce_bool(row[columns["is_critical"]])
                if "is_critical" in columns and columns["is_critical"] < len(row)
                else None,
                related_milestone_wbs=(_norm(row[columns["related_milestone"]]) or None)
                if "related_milestone" in columns
                and columns["related_milestone"] < len(row)
                else None,
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
