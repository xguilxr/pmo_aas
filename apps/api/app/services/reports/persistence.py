"""US-140 — Persistencia de reportes generados desde el Report Builder (EP020).

Reusa la tabla legacy `reports` (modelo `app.models.ai.Report`) con
`generator='builder'` para evitar una tabla nueva. Persiste un snapshot
JSON (`sections`) + el HTML emitido por el motor para poder regenerar
el PDF on-demand sin guardar el binario.

Consumidores:
- `apps/api/app/api/v1/endpoints/report_builder_render.py` →
  `export_template_pdf` llama `persist_builder_export` antes de
  devolver el blob.
- `apps/api/app/workers/tasks/scheduled_reports.py` → rama `custom`
  usa el mismo helper para que el listado por proyecto unifique
  exports manuales y suscripciones.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import Report
from app.models.report_builder_template import ReportBuilderTemplate


async def persist_builder_export(
    db: AsyncSession,
    *,
    tenant_id: UUID | str,
    project_id: UUID | str | None,
    template: ReportBuilderTemplate,
    cut_off_date: date,
    sections_snapshot: dict[str, Any],
    html_content: str,
    created_by: UUID | str | None = None,
    recipients: list[str] | None = None,
    status: str = "draft",
) -> Report:
    """Inserta una row en `reports` representando un export del builder.

    Args:
        sections_snapshot: el `result.json` que devuelve el engine
            (estructura completa de template/scope/window/sections).
        html_content: HTML emitido por el motor (lo guardamos para
            poder re-renderizar PDF sin re-correr el motor).
        status: `'draft'` para exports manuales, `'sent'` para los
            que ya salieron por correo (suscripciones).

    Returns:
        La fila `Report` creada (con `id` poblado).
    """
    folio = (
        None  # se calcula a partir del template ctx si está en el snapshot
    )
    if isinstance(sections_snapshot.get("template"), dict):
        folio = sections_snapshot["template"].get("code")
    title_parts = [template.name]
    if folio:
        title_parts.append(folio)
    title_parts.append(cut_off_date.isoformat())
    title = " — ".join(title_parts)

    rep = Report(
        tenant_id=str(tenant_id),
        project_id=str(project_id) if project_id else "",
        title=title[:200],
        sections=sections_snapshot,
        recipients=list(recipients or []),
        status=status,
        sent_at=(datetime.now(UTC) if status == "sent" else None),
        generated_by_ai=False,
        generator="builder",
        cut_off_date=cut_off_date,
        created_by=str(created_by) if created_by else None,
        html_content=html_content or "",
    )
    db.add(rep)
    await db.flush()
    return rep
