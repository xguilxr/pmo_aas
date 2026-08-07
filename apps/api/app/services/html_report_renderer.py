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

from app.core.observabilidad import medido


def _esc(value: Any) -> str:
    """HTML-escape preservando tipos no-string."""
    if value is None:
        return ""
    return html.escape(str(value))


# ENH-146 — branding on-brand para el HTML interactivo (paleta de marca de
# globals.css). Se comparte entre reporte y minuta para que el PDF (vía
# WeasyPrint) y el navegador rendericen idéntico.
#
# ENH-202 + AM-12 (2026-08-05): aquí había un `<link>` a `fonts.googleapis.com`
# para traer DM Sans. Se retira. Con Helvetica —que la imagen sí instala, vía
# `fonts-urw-base35`— no hacía falta, y era lo que ataba generar un PDF a que
# Google respondiera. El modelo de amenazas pedía exactamente esto: «empotrar
# las tipografías. Se cruza con ENH-202».

_BRAND_CSS = """
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:Helvetica,'Nimbus Sans',Arial,sans-serif;
      background:#F4F6FA;color:#1F1D17;line-height:1.5;padding:32px;
      -webkit-font-smoothing:antialiased;}
    .container{max-width:1100px;margin:0 auto;}
    .brand-header{display:flex;align-items:center;justify-content:space-between;
      gap:16px;padding-bottom:16px;margin-bottom:20px;border-bottom:2px solid #182e4e;}
    .brand-header .brand-pmo{display:flex;align-items:center;gap:10px;}
    .brand-header img.brand-logo{max-height:42px;max-width:200px;object-fit:contain;}
    .brand-header img.brand-client{max-height:38px;max-width:170px;object-fit:contain;}
    .brand-header .brand-name{font-weight:600;font-size:15px;color:#182e4e;}
    h1{font-size:30px;font-weight:700;letter-spacing:-0.02em;color:#182e4e;}
    .meta{font-size:12px;color:#756F60;margin-top:6px;}
    .kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0 30px;}
    @media print{body{background:white;padding:12px;}
      input[type=search]{display:none;} details{break-inside:avoid;}}
"""


def _brand_header_html(
    tenant_name: str | None = None,
    tenant_logo_url: str | None = None,
    client_logo_url: str | None = None,
) -> str:
    """Banda de marca: logo PMO (izq) + nombre, logo cliente (der). "" si
    no hay branding (no se pinta un header vacío)."""
    if not (tenant_name or tenant_logo_url or client_logo_url):
        return ""
    left = ""
    if tenant_logo_url:
        left += f'<img class="brand-logo" src="{_esc(tenant_logo_url)}" alt="{_esc(tenant_name or "PMO")}">'
    if tenant_name:
        left += f'<span class="brand-name">{_esc(tenant_name)}</span>'
    right = (
        f'<img class="brand-client" src="{_esc(client_logo_url)}" alt="Logo del cliente">'
        if client_logo_url
        else ""
    )
    return (
        f'<header class="brand-header"><div class="brand-pmo">{left}</div>{right}</header>'
    )


def _kpi_card(label: str, value: str, tone: str = "neutral", filter_key: str | None = None) -> str:
    """KPI card clicable (CA3): si tiene `filter_key`, emite atributo
    `data-filter` que el JS embebido usa para filtrar la tabla asociada.
    """
    # ENH-146 — tonos alineados a la paleta semántica de marca (globals.css).
    # DIS-02 (2026-08-05): los tres primeros planos se oscurecieron para
    # alcanzar WCAG 2.2 AA. Sobre estos fondos quedan en 4.67, 4.80 y 4.87:1.
    tones = {
        "danger": "background:#FBEAE7;border-color:#E4B7B0;color:#BD3528;",
        "warning": "background:#FBF1DD;border-color:#E7CE97;color:#9F5900;",
        "info": "background:#E8EDF8;border-color:#B6C4E6;color:#2A4DA0;",
        "success": "background:#E3F2E9;border-color:#A9D7BC;color:#007A4C;",
        "neutral": "background:#fff;border-color:#e8e3d7;color:#1F1D17;",
    }
    style = tones.get(tone, tones["neutral"])
    cursor = "cursor:pointer;" if filter_key else ""
    data_attr = (
        f' data-filter="{_esc(filter_key)}" role="button" tabindex="0"'
        if filter_key
        else ""
    )
    return (
        f'<div class="kpi-card" style="border:1px solid;border-radius:12px;'
        f'padding:16px 18px;{style}{cursor}min-width:150px;flex:1;"{data_attr}>'
        f'<div style="font-size:10px;text-transform:uppercase;'
        f'letter-spacing:0.06em;opacity:0.72;font-weight:600;">{_esc(label)}</div>'
        f'<div style="font-size:34px;font-weight:700;margin-top:4px;'
        f'line-height:1.05;font-variant-numeric:tabular-nums;">{_esc(value)}</div></div>'
    )


def _details(title: str, body_html: str, *, open_default: bool = True) -> str:
    """Sección colapsable con `<details>` nativo (CA1)."""
    open_attr = " open" if open_default else ""
    return (
        f'<details{open_attr} style="background:#fff;border:1px solid '
        f'#e8e3d7;border-radius:12px;margin-bottom:14px;overflow:hidden;">'
        f'<summary style="padding:13px 18px;cursor:pointer;font-size:13.5px;'
        f'font-weight:600;color:#182e4e;background:#F8FAFD;">{_esc(title)}'
        f"</summary>"
        f'<div style="padding:14px 18px;">{body_html}</div></details>'
    )


def _filter_table(
    table_id: str, columns: list[str], rows: list[list[Any]],
    raw_cols: set[int] | None = None,
) -> str:
    """Tabla con input de filtro `<input>` que el JS embebido aplica
    sobre las filas (CA2 — filtros client-side).

    `raw_cols` (ENH-150): índices de columna cuyo contenido ya es HTML
    seguro y no debe escaparse (p.ej. el badge de status).
    """
    raw = raw_cols or set()
    head = "".join(
        f'<th style="text-align:left;padding:8px 10px;font-size:10.5px;'
        f'text-transform:uppercase;letter-spacing:0.04em;color:#756F60;'
        f'border-bottom:1px solid #e8e3d7;">{_esc(c)}</th>'
        for c in columns
    )
    body_rows = "".join(
        '<tr data-row="1">'
        + "".join(
            f'<td style="padding:8px 10px;font-size:13px;color:#1F1D17;'
            f'border-bottom:1px solid #EEF1F6;">'
            f'{cell if i in raw else _esc(cell)}</td>'
            for i, cell in enumerate(r)
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
        f'border:1px solid #e8e3d7;border-radius:8px;background:#fff;"/>'
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


@medido("informe.html", tipo="proyecto")
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
    tenant_name: str | None = None,
    tenant_logo_url: str | None = None,
    client_logo_url: str | None = None,
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
            _kpi_card("Atrasadas", str(kpi_delayed), "danger", filter_key="atrasada"),
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
        raw_cols={2},  # ENH-150 — la columna Estado trae badge HTML
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
  <style>{_BRAND_CSS}</style>
</head>
<body>
  <div class="container">
    {_brand_header_html(tenant_name, tenant_logo_url, client_logo_url)}
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


@medido("informe.minuta_html")
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
    tenant_name: str | None = None,
    tenant_logo_url: str | None = None,
    client_logo_url: str | None = None,
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
  <style>{_BRAND_CSS}</style>
</head>
<body>
  <div class="container">
    {_brand_header_html(tenant_name, tenant_logo_url, client_logo_url)}
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
