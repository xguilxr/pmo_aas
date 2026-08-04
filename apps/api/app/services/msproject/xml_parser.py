"""Minimal MS Project XML parser.

MS Project exporta XML según schema Project2003. Esta implementación lee los
campos más relevantes. Para `.mpp` binario se requiere MPXJ (Java) en worker —
no incluido en MVP.

Auditoría MCS 2026-08-03 (B314 / INT-02): el XML lo SUBE EL USUARIO
(`endpoints/tasks.py` → `parse_ms_project_xml`), así que es entrada no confiable.
`xml.etree.ElementTree` no es seguro frente a datos maliciosos: la expansión de
entidades permite agotar memoria con un archivo de pocos kilobytes («billion
laughs»). `defusedxml` devuelve la misma API y rechaza esas construcciones.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

# NO cambiar a `xml.etree` sin leer la nota de arriba: entrada no confiable.
from xml.etree.ElementTree import ParseError

# La regla N817 exime `xml.etree.ElementTree as ET` por ser idioma estándar,
# pero no la variante de defusedxml. Se mantiene el alias `ET` para que el
# cuerpo del parser no cambie y el diff sea revisable.
from defusedxml import ElementTree as ET  # noqa: N817
from defusedxml.common import DefusedXmlException

# Namespace común en MS Project XML
_NS = {"m": "http://schemas.microsoft.com/project"}


@dataclass
class ParsedDependency:
    predecessor_external_id: str
    type: str = "FS"
    lag_days: int = 0


@dataclass
class ParsedTask:
    external_id: str
    name: str
    wbs: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    progress: int = 0
    is_milestone: bool = False
    predecessors: list[ParsedDependency] = field(default_factory=list)


_DEP_TYPE_MAP = {"0": "FF", "1": "FS", "2": "SF", "3": "SS"}


def _text(el, path: str, ns: dict[str, str] | None = None) -> str | None:
    found = el.find(path, ns) if ns else el.find(path)
    return found.text.strip() if found is not None and found.text else None


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return date.fromisoformat(raw[:10])
        except Exception:
            return None


def _duration_days_from_pt(raw: str | None) -> int | None:
    """MSP usa duraciones formato 'PT8H0M0S' o 'P1DT4H'. Heurística: horas/8 = días."""
    if not raw:
        return None
    import re

    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?", raw)
    if not m:
        return None
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    total = days + (hours // 8)
    return total or None


def parse_ms_project_xml(data: bytes) -> tuple[list[ParsedTask], list[str]]:
    """Returns (tasks, errors). Errors son mensajes no-fatal."""
    errors: list[str] = []
    try:
        root = ET.fromstring(data)
    except ParseError as exc:
        raise ValueError(f"xml_invalid: {exc}") from exc
    except DefusedXmlException as exc:
        # Un XML con entidades o DTD externa no es un archivo mal formado: es un
        # intento de agotar memoria o de leer archivos del servidor. Se rechaza
        # con el mismo 400 que cualquier archivo inválido, sin detalle que
        # confirme al remitente qué defensa saltó.
        raise ValueError("xml_invalid: estructura XML no permitida") from exc

    # Detecta si usa namespace
    ns_match = root.tag.startswith("{")
    ns = _NS if ns_match else None
    tasks_path = "m:Tasks/m:Task" if ns_match else "Tasks/Task"

    parsed_tasks: list[ParsedTask] = []
    for t in root.findall(tasks_path, ns) if ns_match else root.findall(tasks_path):
        uid = _text(t, "m:UID" if ns_match else "UID", ns)
        if uid is None or uid == "0":
            continue
        name = _text(t, "m:Name" if ns_match else "Name", ns) or f"Task-{uid}"
        wbs = _text(t, "m:WBS" if ns_match else "WBS", ns)
        start = _parse_date(_text(t, "m:Start" if ns_match else "Start", ns))
        finish = _parse_date(_text(t, "m:Finish" if ns_match else "Finish", ns))
        duration = _duration_days_from_pt(
            _text(t, "m:Duration" if ns_match else "Duration", ns)
        )
        try:
            progress_raw = _text(t, "m:PercentComplete" if ns_match else "PercentComplete", ns)
            progress = int(progress_raw or "0")
        except ValueError:
            progress = 0
        is_milestone = (_text(t, "m:Milestone" if ns_match else "Milestone", ns) == "1")

        deps: list[ParsedDependency] = []
        link_path = "m:PredecessorLink" if ns_match else "PredecessorLink"
        for link in (t.findall(link_path, ns) if ns_match else t.findall(link_path)):
            pre_uid = _text(link, "m:PredecessorUID" if ns_match else "PredecessorUID", ns)
            if not pre_uid:
                continue
            t_raw = _text(link, "m:Type" if ns_match else "Type", ns) or "1"
            type_ = _DEP_TYPE_MAP.get(t_raw, "FS")
            lag_raw = _text(link, "m:LinkLag" if ns_match else "LinkLag", ns)
            try:
                # LinkLag es en minutos de MSP; asumimos 480 min/día = 1 día
                lag = int(lag_raw or 0)
                lag_days = lag // 480 if abs(lag) >= 480 else 0
            except ValueError:
                lag_days = 0
            deps.append(ParsedDependency(
                predecessor_external_id=pre_uid, type=type_, lag_days=lag_days,
            ))

        parsed_tasks.append(ParsedTask(
            external_id=uid, name=name, wbs=wbs,
            start_date=start, end_date=finish, duration_days=duration,
            progress=progress, is_milestone=is_milestone, predecessors=deps,
        ))

    return parsed_tasks, errors
