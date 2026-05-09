"""HTML interactive report renderer — US-111.

Server-renderiza un HTML standalone para reportes (y minutas, CA6) con:
- header + KPI cards
- secciones colapsables (`<details>`)
- tablas con filtros vanilla JS embebidos
- estilos inline (CA4 — funciona offline)

El HTML resultante es self-contained: data inyectada server-side (CA5),
sin endpoints en runtime, los filtros operan client-side sobre el DOM.

El template default sigue la estructura de `docs/archive/Reporte de
Seguimiento.html`: KPI cards arriba, tabla de actividades abajo,
secciones colapsables en el medio.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any


def _esc(value: Any) -> str:
    """HTML-escape preservando tipos no-string."""
    if value is None:
        return ""
    return html.escape(str(value))


def _kpi_card(label: str, value: str, tone: str = "neutral", filter_key: str | None = None) -> str:
    """KPI card clicable (CA3): si tiene `filter_key`, emite atributo
    `data-filter` que el JS embebido usa para filtrar la tabla asociada.
    """
    tones = {
        "danger": "background:#fbe1dc;border-color:#e89486;color:#b3331e;",
        "warning": "background:#fcefcf;border-color:#d9b14a;color:#806022;",
        "info": "background:#dbe6fb;border-color:#7aa3e6;color:#3a5fa8;",
        "success": "background:#d6efdb;border-color:#7ec18a;color:#2c6e3f;",
        "neutral": "background:#fff;border-color:#d8d3c8;color:#2a2622;",
    }
    style = tones.get(tone, tones["neutral"])
    cursor = "cursor:pointer;" if filter_key else ""
    data_attr = (
        f' data-filter="{_esc(filter_key)}" role="button" tabindex="0"'
        if filter_key
        else ""
    )
    return (
        f'<div class="kpi-card" style="border:2px solid;border-radius:18px;'
        f'padding:20px 24px;{style}{cursor}min-width:180px;flex:1;"{data_attr}>'
        f'<div style="font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.06em;opacity:0.7;font-weight:600;">{_esc(label)}</div>'
        f'<div style="font-size:48px;font-weight:700;margin-top:6px;'
        f'line-height:1;">{_esc(value)}</div></div>'
    )


def _details(title: str, body_html: str, *, open_default: bool = True) -> str:
    """Sección colapsable con `<details>` nativo (CA1)."""
    open_attr = " open" if open_default else ""
    return (
        f'<details{open_attr} style="background:#fff;border:1px solid '
        f'#e8e2d5;border-radius:14px;margin-bottom:16px;overflow:hidden;">'
        f'<summary style="padding:14px 18px;cursor:pointer;font-size:14px;'
        f'font-weight:600;color:#2a2622;background:#faf7f0;">{_esc(title)}'
        f"</summary>"
        f'<div style="padding:14px 18px;">{body_html}</div></details>'
    )


def _filter_table(
    table_id: str, columns: list[str], rows: list[list[Any]]
) -> str:
    """Tabla con input de filtro `<input>` que el JS embebido aplica
    sobre las filas (CA2 — filtros client-side)."""
    head = "".join(
        f'<th style="text-align:left;padding:8px 10px;font-size:11px;'
        f'text-transform:uppercase;letter-spacing:0.04em;color:#806b50;'
        f'border-bottom:1px solid #e8e2d5;">{_esc(c)}</th>'
        for c in columns
    )
    body_rows = "".join(
        '<tr data-row="1">'
        + "".join(
            f'<td style="padding:8px 10px;font-size:13px;color:#2a2622;'
            f'border-bottom:1px solid #f3eede;">{_esc(cell)}</td>'
            for cell in r
        )
        + "</tr>"
        for r in rows
    )
    if not rows:
        body_rows = (
            f'<tr><td colspan="{len(columns)}" style="padding:14px;'
            f'color:#999;font-style:italic;text-align:center;">Sin registros</td></tr>'
        )
    return (
        f'<div style="margin-bottom:8px;">'
        f'<input type="search" placeholder="Filtrar…" '
        f'data-filter-target="{_esc(table_id)}" '
        f'style="width:100%;max-width:280px;padding:6px 10px;font-size:12px;'
        f'border:1px solid #d8d3c8;border-radius:6px;"/>'
        f"</div>"
        f'<div style="overflow-x:auto;"><table id="{_esc(table_id)}" '
        f'style="width:100%;border-collapse:collapse;font-family:inherit;">'
        f"<thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>"
    )


_INLINE_JS = """
<script>
(function(){
  // Filtros simples client-side (CA2): cada <input data-filter-target=ID>
  // filtra las filas <tr data-row="1"> de la tabla cuyo id coincide.
  document.querySelectorAll('input[data-filter-target]').forEach(function(inp){
    inp.addEventListener('input', function(){
      var tableId = inp.getAttribute('data-filter-target');
      var t = document.getElementById(tableId);
      if (!t) return;
      var q = (inp.value || '').toLowerCase().trim();
      t.querySelectorAll('tbody tr[data-row="1"]').forEach(function(row){
        var match = !q || row.textContent.toLowerCase().indexOf(q) >= 0;
        row.style.display = match ? '' : 'none';
      });
    });
  });
  // KPIs clicables (CA3): un click sobre una KPI card con data-filter="<value>"
  // rellena el primer input de filtro y dispara su evento input para
  // que la tabla principal se filtre. Re-click limpia el filtro.
  document.querySelectorAll('.kpi-card[data-filter]').forEach(function(card){
    card.addEventListener('click', function(){
      var value = card.getAttribute('data-filter');
      var input = document.querySelector('input[data-filter-target]');
      if (!input) return;
      var current = (input.value || '').trim();
      input.value = current === value ? '' : value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      // Visual feedback
      document.querySelectorAll('.kpi-card[data-filter]').forEach(function(c){
        c.style.outline = '';
      });
      if (input.value) card.style.outline = '3px solid rgba(58,95,168,0.4)';
    });
    card.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
    });
  });
})();
</script>
"""


def render_report_html(
    *,
    title: str,
    project_name: str,
    project_folio: str,
    generated_at: datetime,
    kpis: dict[str, Any],
    tasks: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    summary_html: str = "",
) -> str:
    """Renderiza un reporte HTML interactivo standalone.

    `kpis` espera dict con claves opcionales:
        progress, on_time_pct, delayed_count, milestones_pending,
        risks_high, period
    `tasks` lista de dicts con keys: name, owner, status, end_date, progress.
    `risks/issues/changes` lista de dicts con keys: title, owner, severity, status.
    """
    kpi_progress = kpis.get("progress", "—")
    kpi_on_time = kpis.get("on_time_pct", "—")
    kpi_delayed = kpis.get("delayed_count", 0)
    kpi_risks = kpis.get("risks_high", 0)
    kpi_milestones = kpis.get("milestones_pending", 0)
    kpis_row = "".join(
        [
            _kpi_card("Avance %", f"{kpi_progress}%", "info"),
            _kpi_card("On-time %", f"{kpi_on_time}%", "success"),
            _kpi_card("Retrasadas", str(kpi_delayed), "danger", filter_key="retrasada"),
            _kpi_card("Riesgos alta", str(kpi_risks), "warning", filter_key="alta"),
            _kpi_card("Hitos pendientes", str(kpi_milestones), "neutral"),
        ]
    )

    tasks_table = _filter_table(
        "tbl-tasks",
        ["Tarea", "Responsable", "Estado", "Fin", "Avance"],
        [
            [
                t.get("name") or "",
                t.get("owner") or "—",
                t.get("status") or "",
                t.get("end_date") or "—",
                f"{t.get('progress', 0)}%",
            ]
            for t in tasks
        ],
    )

    risks_table = _filter_table(
        "tbl-risks",
        ["Título", "Responsable", "Severidad", "Estado"],
        [
            [
                r.get("title") or "",
                r.get("owner") or "—",
                r.get("severity") or "—",
                r.get("status") or "",
            ]
            for r in risks
        ],
    )

    issues_table = _filter_table(
        "tbl-issues",
        ["Título", "Responsable", "Prioridad", "Estado"],
        [
            [
                i.get("title") or "",
                i.get("owner") or "—",
                i.get("priority") or "—",
                i.get("status") or "",
            ]
            for i in issues
        ],
    )

    changes_table = _filter_table(
        "tbl-changes",
        ["Título", "Tipo", "Estado", "Solicitante"],
        [
            [
                c.get("title") or "",
                c.get("type") or "—",
                c.get("status") or "",
                c.get("requester") or "—",
            ]
            for c in changes
        ],
    )

    report_meta = json.dumps(
        {
            "title": title,
            "project": {"name": project_name, "folio": project_folio},
            "generated_at": generated_at.isoformat(),
        },
        ensure_ascii=False,
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{_esc(title)} — {_esc(project_folio)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fbfaf7;color:#2a2622;line-height:1.45;padding:32px;}}
    .container{{max-width:1200px;margin:0 auto;}}
    h1{{font-size:32px;font-weight:700;letter-spacing:-0.02em;}}
    .meta{{font-size:12px;color:#806b50;margin-top:6px;}}
    .kpi-row{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0 32px;}}
    @media print {{ body {{ background: white; padding: 12px; }} input[type=search] {{ display: none; }} details {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{_esc(title)}</h1>
      <p class="meta">{_esc(project_name)} · <strong>{_esc(project_folio)}</strong> · {_esc(generated_at.strftime('%Y-%m-%d %H:%M'))}</p>
    </header>
    <div class="kpi-row" role="group" aria-label="Indicadores">
      {kpis_row}
    </div>
    {(_details("Resumen ejecutivo", summary_html) if summary_html else "")}
    {_details("Actividades", tasks_table)}
    {_details("Riesgos", risks_table, open_default=False)}
    {_details("Issues", issues_table, open_default=False)}
    {_details("Cambios", changes_table, open_default=False)}
  </div>
  <script type="application/json" id="report-meta">{_esc(report_meta)}</script>
  {_INLINE_JS}
</body>
</html>"""


def render_minute_html(
    *,
    title: str,
    project_name: str,
    project_folio: str,
    meeting_date: datetime,
    summary: str,
    participants: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    agreements: list[dict[str, Any]],
    raid_suggestions: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    """ENH-090 + US-111 CA6: render HTML para minutas con la misma base
    visual (KPI cards + tablas con filtros + secciones colapsables)."""
    raid_suggestions = raid_suggestions or {
        "risks": [], "issues": [], "lessons": [], "changes": [],
    }
    summary_html = (
        f'<p style="white-space:pre-wrap;">{_esc(summary)}</p>'
        if summary
        else '<p style="font-style:italic;color:#999;">Sin resumen.</p>'
    )

    participants_html = "".join(
        f'<span style="display:inline-block;padding:4px 10px;background:#f3eede;'
        f'border-radius:16px;font-size:12px;margin:2px;">{_esc(p.get("name") or "")}</span>'
        for p in participants
    ) or '<p style="font-style:italic;color:#999;">Sin participantes.</p>'

    topics_html = (
        "".join(
            f'<div style="padding:10px 12px;background:#faf7f0;border-radius:8px;margin-bottom:8px;">'
            f'<strong style="font-size:13px;">{_esc(t.get("title") or "")}</strong>'
            f'<p style="font-size:12px;color:#5a5044;margin-top:4px;white-space:pre-wrap;">{_esc(t.get("notes") or "")}</p>'
            "</div>"
            for t in topics
        )
        or '<p style="font-style:italic;color:#999;">Sin temas.</p>'
    )

    agreements_html = _filter_table(
        "tbl-agreements",
        ["Acuerdo", "Owner", "Fecha"],
        [
            [a.get("description") or "", a.get("owner") or "—", a.get("due_date") or "—"]
            for a in agreements
        ],
    )

    raid_total = sum(len(raid_suggestions.get(k, [])) for k in ("risks", "issues", "lessons", "changes"))
    kpis_row = "".join(
        [
            _kpi_card("Participantes", str(len(participants)), "info"),
            _kpi_card("Temas", str(len(topics)), "neutral"),
            _kpi_card("Acuerdos", str(len(agreements)), "success"),
            _kpi_card("RAIDs sugeridos", str(raid_total), "warning"),
        ]
    )

    raid_blocks = []
    for kind in ("risks", "issues", "lessons", "changes"):
        items = raid_suggestions.get(kind, [])
        if not items:
            continue
        rows = [
            [
                it.get("short_desc") or "",
                it.get("suggested_owner_name") or "—",
                it.get("suggested_priority") or "—",
                it.get("status") or "pending",
            ]
            for it in items
        ]
        raid_blocks.append(
            _details(
                f"RAID — {kind.capitalize()} ({len(items)})",
                _filter_table(
                    f"tbl-raid-{kind}",
                    ["Descripción", "Owner sugerido", "Prioridad", "Estado"],
                    rows,
                ),
                open_default=kind == "risks",
            )
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{_esc(title)} — {_esc(project_folio)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fbfaf7;color:#2a2622;line-height:1.45;padding:32px;}}
    .container{{max-width:1100px;margin:0 auto;}}
    h1{{font-size:30px;font-weight:700;letter-spacing:-0.02em;}}
    .meta{{font-size:12px;color:#806b50;margin-top:6px;}}
    .kpi-row{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0 32px;}}
    @media print {{ body {{ background: white; padding: 12px; }} input[type=search] {{ display: none; }} details {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{_esc(title)}</h1>
      <p class="meta">{_esc(project_name)} · <strong>{_esc(project_folio)}</strong> · {_esc(meeting_date.strftime('%Y-%m-%d %H:%M'))}</p>
    </header>
    <div class="kpi-row">{kpis_row}</div>
    {_details("Resumen", summary_html)}
    {_details("Participantes", participants_html, open_default=False)}
    {_details("Temas", topics_html)}
    {_details("Acuerdos", agreements_html)}
    {''.join(raid_blocks)}
  </div>
  {_INLINE_JS}
</body>
</html>"""
