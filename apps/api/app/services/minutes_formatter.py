"""Formateador estandarizado de Minuta (US-040, EP014).

Convierte una MeetingMinute en el formato corporativo:

    ========
    Título - "Minuta Reunión {nombre}" — {Proyecto} — Fecha
    ========
    Sesión
    Fecha
    Duración
    Participantes
    ========
    Resumen e Hitos  (agrupado por tema, enumerado, conciso)
    ========
    RAID (tabla)
    * Acciones agrupadas por área / responsable
    ========
    Notas adicionales

Expone helpers para producir preview (context para Jinja), Markdown,
texto plano, DOCX y PDF. Los datos fuente salen del objeto JSON de la
minuta (participants, topics, agreements); cuando la minuta fue
generada por IA el prompt devuelve ya la forma esperada.
"""
from __future__ import annotations

import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.models.modules import MeetingMinute
from app.models.project import Project
from app.services.pdf_renderer import render_pdf

SEPARATOR = "========"


@dataclass
class MinuteView:
    title: str
    project_name: str | None
    project_folio: str | None
    meeting_date: str
    session_number: int | str | None
    duration: str | None
    participants: list[dict[str, Any]]
    summary_topics: list[dict[str, Any]]
    raid_groups: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    additional_notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "project_name": self.project_name,
            "project_folio": self.project_folio,
            "meeting_date": self.meeting_date,
            "session_number": self.session_number,
            "duration": self.duration,
            "participants": self.participants,
            "summary_topics": self.summary_topics,
            "raid_groups": self.raid_groups,
            "risks": self.risks,
            "issues": self.issues,
            "decisions": self.decisions,
            "additional_notes": self.additional_notes,
        }


def _format_meeting_date(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)[:25]


def _short_title_from_minute(minute: MeetingMinute) -> str:
    raw = minute.title or "Reunión"
    if len(raw) > 60:
        raw = raw[:57].rstrip() + "…"
    return f'"Minuta Reunión {raw}"'


def build_view(minute: MeetingMinute, project: Project | None = None) -> MinuteView:
    """Transforma una MeetingMinute en la vista estandarizada."""
    # Topics: [{title, notes}] o tolerar diferentes formas.
    topics_raw = minute.topics or []
    summary_topics: list[dict[str, Any]] = []
    for idx, t in enumerate(topics_raw, start=1):
        if isinstance(t, dict):
            summary_topics.append({
                "index": idx,
                "topic": t.get("title") or t.get("name") or "—",
                "notes": t.get("notes") or t.get("summary") or "",
            })
        else:
            summary_topics.append({"index": idx, "topic": str(t), "notes": ""})

    # Participants: normalizar a dict con name / role
    participants: list[dict[str, Any]] = []
    for p in (minute.participants or []):
        if isinstance(p, dict):
            participants.append({
                "name": p.get("name") or p.get("full_name") or "—",
                "role": p.get("role") or p.get("area") or "",
                "email": p.get("email"),
            })
        else:
            participants.append({"name": str(p), "role": "", "email": None})

    # RAID table desde agreements (tipo action) + si vienen risks/issues/decisions
    agreements = minute.agreements or []
    actions = []
    risks = []
    issues = []
    decisions = []
    for ag in agreements:
        if not isinstance(ag, dict):
            ag = {"description": str(ag)}
        kind = (ag.get("kind") or ag.get("type") or "action").lower()
        row = {
            "description": ag.get("description") or ag.get("title") or "—",
            "owner": ag.get("owner_name") or ag.get("owner") or ag.get("area") or "Sin responsable",
            "area": ag.get("area") or "",
            "due_date": ag.get("due_date"),
            "status": ag.get("status") or "open",
            "severity": ag.get("severity"),
        }
        if kind == "risk":
            risks.append(row)
        elif kind in ("issue", "incident"):
            issues.append(row)
        elif kind == "decision":
            decisions.append(row)
        else:
            actions.append(row)

    # Agrupar acciones por área / responsable
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in actions:
        key = a["area"] or a["owner"] or "Sin responsable"
        buckets[key].append(a)
    raid_groups = [
        {
            "owner": k,
            "rows": sorted(
                v,
                key=lambda r: (r.get("due_date") or "", r["description"]),
            ),
        }
        for k, v in sorted(buckets.items(), key=lambda kv: (kv[0] == "Sin responsable", kv[0].lower()))
    ]

    meta = {}
    # Algunos campos estándar pueden venir dentro de `topics[0]` o
    # `attachments[0]` si la IA los incrusta ahí. Mejor leer directamente
    # de la minuta. Si existen, usarlos.
    session_number = None
    duration = None

    meeting_date_str = _format_meeting_date(minute.meeting_date)
    project_name = project.name if project else None
    project_folio = project.folio if project else None

    title_line = (
        f"{_short_title_from_minute(minute)} — "
        f"{project_name or 'Proyecto'} — {meeting_date_str[:10]}"
    )

    return MinuteView(
        title=title_line,
        project_name=project_name,
        project_folio=project_folio,
        meeting_date=meeting_date_str,
        session_number=session_number,
        duration=duration,
        participants=participants,
        summary_topics=summary_topics,
        raid_groups=raid_groups,
        risks=risks,
        issues=issues,
        decisions=decisions,
        additional_notes="",
    )


# ---- Exports ----

def to_markdown(view: MinuteView) -> str:
    lines: list[str] = []
    sep = SEPARATOR

    lines.append(sep)
    lines.append(f"Título - {view.title}")
    lines.append(sep)
    lines.append(f"Sesión: {view.session_number or '—'}")
    lines.append(f"Fecha: {view.meeting_date or '—'}")
    lines.append(f"Duración: {view.duration or '—'}")
    lines.append("Participantes:")
    if view.participants:
        for p in view.participants:
            role = f" ({p['role']})" if p.get("role") else ""
            lines.append(f"  - {p['name']}{role}")
    else:
        lines.append("  - —")
    lines.append(sep)
    lines.append("Resumen e Hitos")
    if view.summary_topics:
        for t in view.summary_topics:
            lines.append(f"  {t['index']}. {t['topic']}")
            if t.get("notes"):
                lines.append(f"     {t['notes']}")
    else:
        lines.append("  —")
    lines.append(sep)
    lines.append("RAID")
    if view.risks:
        lines.append("Riesgos:")
        for r in view.risks:
            sev = f" [sev {r['severity']}]" if r.get("severity") else ""
            lines.append(f"  - {r['description']} — {r['owner']}{sev}")
    if view.raid_groups:
        lines.append("Acciones (agrupadas por responsable / área):")
        for g in view.raid_groups:
            lines.append(f"  {g['owner']}:")
            for row in g["rows"]:
                due = f" ({row['due_date']})" if row.get("due_date") else ""
                lines.append(f"    - {row['description']}{due}")
    if view.issues:
        lines.append("Incidentes:")
        for i in view.issues:
            lines.append(f"  - {i['description']} — {i['owner']}")
    if view.decisions:
        lines.append("Decisiones:")
        for d in view.decisions:
            lines.append(f"  - {d['description']} — {d['owner']}")
    if not any([view.risks, view.raid_groups, view.issues, view.decisions]):
        lines.append("  —")
    lines.append(sep)
    lines.append("Notas adicionales")
    lines.append(view.additional_notes or "—")
    return "\n".join(lines) + "\n"


def to_plain_text(view: MinuteView) -> str:
    """Mismo formato markdown pero asegurando texto plano neutro."""
    return to_markdown(view)


def to_docx(view: MinuteView) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading(view.title, level=1)

    h = doc.add_heading("Datos de la sesión", level=2)  # noqa: F841
    table = doc.add_table(rows=4, cols=2)
    table.style = "Light Grid"
    table.rows[0].cells[0].text = "Sesión"
    table.rows[0].cells[1].text = str(view.session_number or "—")
    table.rows[1].cells[0].text = "Fecha"
    table.rows[1].cells[1].text = view.meeting_date or "—"
    table.rows[2].cells[0].text = "Duración"
    table.rows[2].cells[1].text = view.duration or "—"
    parts = (
        "\n".join(
            f"- {p['name']}" + (f" ({p['role']})" if p.get("role") else "")
            for p in view.participants
        )
        or "—"
    )
    table.rows[3].cells[0].text = "Participantes"
    table.rows[3].cells[1].text = parts

    doc.add_heading("Resumen e Hitos", level=2)
    if view.summary_topics:
        for t in view.summary_topics:
            doc.add_paragraph(f"{t['index']}. {t['topic']}", style="List Number")
            if t.get("notes"):
                doc.add_paragraph(t["notes"], style="Intense Quote")
    else:
        doc.add_paragraph("—")

    doc.add_heading("RAID", level=2)

    def _raid_table(rows: list[dict[str, Any]], title: str, cols: list[str]) -> None:
        if not rows:
            return
        doc.add_heading(title, level=3)
        tbl = doc.add_table(rows=1 + len(rows), cols=len(cols))
        tbl.style = "Light Grid"
        for j, c in enumerate(cols):
            tbl.rows[0].cells[j].text = c
        for i, r in enumerate(rows, start=1):
            cells = tbl.rows[i].cells
            cells[0].text = r.get("description") or "—"
            cells[1].text = r.get("owner") or "—"
            if len(cols) >= 3:
                cells[2].text = str(r.get("due_date") or r.get("severity") or "—")

    _raid_table(view.risks, "Riesgos", ["Descripción", "Responsable", "Severidad"])
    if view.raid_groups:
        doc.add_heading("Acciones (agrupadas por responsable / área)", level=3)
        for g in view.raid_groups:
            doc.add_paragraph(g["owner"], style="Heading 4")
            tbl = doc.add_table(rows=1 + len(g["rows"]), cols=2)
            tbl.style = "Light Grid"
            tbl.rows[0].cells[0].text = "Descripción"
            tbl.rows[0].cells[1].text = "Fecha compromiso"
            for i, row in enumerate(g["rows"], start=1):
                tbl.rows[i].cells[0].text = row["description"]
                tbl.rows[i].cells[1].text = str(row.get("due_date") or "—")
    _raid_table(view.issues, "Incidentes", ["Descripción", "Responsable", "Status"])
    _raid_table(view.decisions, "Decisiones", ["Descripción", "Responsable", "Status"])

    doc.add_heading("Notas adicionales", level=2)
    doc.add_paragraph(view.additional_notes or "—")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def to_pdf(view: MinuteView, tenant_name: str | None = None) -> bytes:
    context = view.as_dict()
    context["tenant_name"] = tenant_name
    return render_pdf("minutes/minute.html", context)
