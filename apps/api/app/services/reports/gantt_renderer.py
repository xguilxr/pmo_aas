"""US-132 — Gantt snapshot renderer para S-19 del Report Builder.

Genera un SVG estático del Gantt de un proyecto agregado a WBS-N
(nivel WBS configurable, default 1) y filtrado por ventana temporal.

Decisión pragmática v1.0: el renderer es 100% Python (no headless
browser). Pros: deploy sin nuevas dependencias en el worker, render
< 1s, contrato `image/svg+xml` válido y embebible vía `<img>` o
PDF (WeasyPrint). Cons: visualmente menos rico que el Gantt
interactivo del frontend. Cuando el worker incorpore Playwright en
una iteración futura, el endpoint puede pasar a screenshot real
sin cambiar el contrato HTTP.

Si la lista de tareas excede un threshold (200 barras), se aplica
un fallback que renderiza un placeholder con conteo agregado en
lugar de barras individuales — evita SVGs gigantes.
"""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.paleta import ACENTO, NEUTRO, NEUTRO_SUAVE, ORDINAL_CLARO, serie
from app.core.unidades import pct_a_fraccion
from app.models.project import Project
from app.models.task import Task

# Layout
ROW_HEIGHT = 18
LEFT_GUTTER = 200
RIGHT_PADDING = 20
TOP_PADDING = 30
MAX_ROWS_DETAIL = 200  # Fallback a placeholder si excede.


def _wbs_top_level(wbs_code: str | None, level: int) -> str:
    """Devuelve los primeros `level` segmentos del WBS (1, 1.2, 1.2.3...)."""
    if not wbs_code:
        return "(sin WBS)"
    parts = wbs_code.split(".")
    return ".".join(parts[:level]) if parts else wbs_code


def _aggregate_by_wbs(
    tasks: list[Task], level: int, window_start: date, window_end: date
) -> list[dict]:
    """Agrupa tareas por WBS-N. Cada grupo expone fechas extremas y % avg."""
    buckets: dict[str, dict] = {}
    for t in tasks:
        if t.start_date is None or t.end_date is None:
            continue
        # Clip a la ventana.
        s = max(t.start_date, window_start)
        e = min(t.end_date, window_end)
        if e < s:
            continue
        key = _wbs_top_level(t.wbs_code, level)
        b = buckets.setdefault(
            key,
            {
                "wbs_code": key,
                "start": s,
                "end": e,
                "progress_sum": 0.0,
                "count": 0,
                "milestones": 0,
                "criticals": 0,
            },
        )
        b["start"] = min(b["start"], s)
        b["end"] = max(b["end"], e)
        b["progress_sum"] += float(t.progress or 0)
        b["count"] += 1
        if t.is_milestone:
            b["milestones"] += 1
        if getattr(t, "is_critical", False):
            b["criticals"] += 1
    out = []
    for k in sorted(buckets):
        b = buckets[k]
        b["avg_progress"] = round(b["progress_sum"] / b["count"], 1) if b["count"] else 0
        out.append(b)
    return out


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_gantt_svg(
    project: Project,
    tasks: list[Task],
    *,
    wbs_level: int = 1,
    window_start: date | None = None,
    window_end: date | None = None,
) -> str:
    """Renderiza el Gantt como SVG. Devuelve string `<svg ...>...</svg>`."""
    if window_start is None or window_end is None:
        # Default: span del proyecto si está disponible, o ±30d desde hoy.
        if project.start_date and project.end_date:
            window_start = project.start_date
            window_end = project.end_date
        else:
            today = date.today()
            window_start = today - timedelta(days=30)
            window_end = today + timedelta(days=60)
    if window_end <= window_start:
        window_end = window_start + timedelta(days=1)

    rows = _aggregate_by_wbs(tasks, wbs_level, window_start, window_end)

    if not rows:
        return _empty_svg(project, window_start, window_end)
    if len(rows) > MAX_ROWS_DETAIL:
        return _placeholder_svg(project, len(tasks), len(rows), window_start, window_end)

    total_days = max(1, (window_end - window_start).days)
    chart_width = 800
    width = LEFT_GUTTER + chart_width + RIGHT_PADDING
    height = TOP_PADDING + ROW_HEIGHT * len(rows) + 20

    def x_for(d: date) -> int:
        days = (d - window_start).days
        return LEFT_GUTTER + int(days / total_days * chart_width)

    svg_parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        # Header
        f'<text x="10" y="20" font-family="Helvetica, Nimbus Sans, Arial, sans-serif" '
        f'font-size="12" font-weight="700" fill="#111827">'
        f"Gantt — {_xml_escape(project.folio)} · {_xml_escape(project.name)[:40]}"
        f"</text>",
        # Eje temporal: barra superior
        f'<line x1="{LEFT_GUTTER}" y1="{TOP_PADDING}" x2="{LEFT_GUTTER + chart_width}" '
        f'y2="{TOP_PADDING}" stroke="#e5e7eb" stroke-width="1"/>',
        # Etiquetas inicio/fin
        f'<text x="{LEFT_GUTTER}" y="{TOP_PADDING - 4}" font-size="8" fill="{NEUTRO}">'
        f'{window_start.isoformat()}</text>',
        f'<text x="{LEFT_GUTTER + chart_width}" y="{TOP_PADDING - 4}" '
        f'font-size="8" fill="{NEUTRO}" text-anchor="end">'
        f'{window_end.isoformat()}</text>',
    ]

    # Una línea por WBS
    for i, b in enumerate(rows):
        y = TOP_PADDING + 4 + i * ROW_HEIGHT
        # Label
        svg_parts.append(
            f'<text x="6" y="{y + 11}" font-size="9" fill="#374151">'
            f'{_xml_escape(b["wbs_code"])} <tspan fill="{NEUTRO_SUAVE}">({b["count"]})</tspan>'
            f'</text>'
        )
        # Barra
        bx = x_for(b["start"])
        ex = x_for(b["end"])
        bw = max(2, ex - bx)
        # ADR-023: la ruta crítica deja el rojo. Era `#dc2626`, el mismo rojo
        # con el que el semáforo dice «proyecto en problemas» — un grupo con
        # tareas críticas no está en problemas, está en el camino largo. La
        # criticidad es **énfasis estructural**, así que se marca con borde y
        # peso, no robándole el color a un estado.
        fill = serie(0)
        if b["milestones"] > 0:
            fill = serie(2)
        critico = b["criticals"] > 0
        borde = (
            f' stroke="{ACENTO}" stroke-width="1.5"' if critico else ""
        )
        svg_parts.append(
            f'<rect x="{bx}" y="{y + 3}" width="{bw}" height="10" '
            f'fill="{fill}"{borde} rx="2"/>'
        )
        # Progreso overlay. Era verde —el del semáforo—; el avance no es un
        # estado, es la misma barra más oscura.
        pwidth = int(bw * pct_a_fraccion(b["avg_progress"]))
        if pwidth > 0:
            svg_parts.append(
                f'<rect x="{bx}" y="{y + 3}" width="{pwidth}" height="10" '
                f'fill="{ORDINAL_CLARO[-1]}" fill-opacity="0.75" rx="2"/>'
            )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def _empty_svg(project: Project, ws: date, we: date) -> str:
    msg = f"Sin tareas en la ventana {ws.isoformat()} / {we.isoformat()}"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="80">'
        '<rect width="600" height="80" fill="#fafafa"/>'
        f'<text x="20" y="30" font-size="12" fill="#374151">Gantt — {_xml_escape(project.folio)}</text>'
        f'<text x="20" y="50" font-size="10" fill="{NEUTRO}">{_xml_escape(msg)}</text>'
        "</svg>"
    )


def _placeholder_svg(
    project: Project, n_tasks: int, n_rows: int, ws: date, we: date
) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="100">'
        '<rect width="700" height="100" fill="#f0f9ff"/>'
        f'<text x="20" y="30" font-size="13" font-weight="700" fill="#0c4a6e">'
        f"Gantt — {_xml_escape(project.folio)}</text>"
        f'<text x="20" y="55" font-size="11" fill="#0c4a6e">'
        f"{n_tasks} tareas en {n_rows} grupos WBS</text>"
        f'<text x="20" y="75" font-size="9" fill="#0369a1">'
        f"Vista detallada deshabilitada (umbral 200). Ventana: "
        f"{ws.isoformat()} → {we.isoformat()}</text>"
        "</svg>"
    )


async def render_project_gantt(
    db: AsyncSession,
    tenant_id: UUID | str,
    project_id: UUID | str,
    *,
    wbs_level: int = 1,
    window_start: date | None = None,
    window_end: date | None = None,
) -> str:
    """Carga proyecto + tasks y devuelve SVG."""
    pid = str(project_id)
    project = (
        await db.execute(
            select(Project).where(
                Project.id == pid,
                Project.tenant_id == str(tenant_id),
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise not_found("Proyecto")
    tasks = (
        await db.execute(select(Task).where(Task.project_id == pid))
    ).scalars().all()
    return render_gantt_svg(
        project,
        tasks,
        wbs_level=wbs_level,
        window_start=window_start,
        window_end=window_end,
    )
