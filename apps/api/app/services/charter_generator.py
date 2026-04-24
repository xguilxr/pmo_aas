"""BUG-028 — Generador del Project Charter en .docx.

El owner (comentario 2026-04-24) pidió que cada proyecto tenga un
archivo de charter **real** (no un URL placeholder). Este servicio
genera el .docx desde la fila `ProjectCharter` usando `python-docx` y
lo persiste vía `document_storage.save_document_bytes()`, que usa el
backend configurado (`local` en dev, `s3` / Cloudflare R2 en prod
tras US-066).

El mismo archivo se edita desde dos lugares:
1. `/admin/projects/[id]/charter` (editor existente).
2. `/admin/projects/[id]/documents` (link al editor vía frontend).

Al guardar cambios en el editor, se llama a `regenerate_charter_docx()`
que sobrescribe el archivo (misma `Document.id`, bump de `version`).
"""
from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modules import Document
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.services.document_storage import save_document_bytes
from app.services.folio import next_folio

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _render_charter_docx(charter: ProjectCharter, project: Project) -> bytes:
    """Construye el .docx del charter usando python-docx y devuelve bytes.

    Estructura (secciones 1-3 de la tabla + sección 4 derivada del
    proyecto) que refleja la vista HTML en project_charters.py.
    """
    doc = DocxDocument()

    title = doc.add_heading(f"Project Charter — {charter.project_name}", level=1)
    title_run = title.runs[0]
    title_run.font.color.rgb = RGBColor(0x18, 0x2E, 0x4E)

    subtitle = doc.add_paragraph()
    subrun = subtitle.add_run(
        f"Proyecto: {project.folio} · Generado {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    subrun.font.size = Pt(9)
    subrun.font.color.rgb = RGBColor(0x5A, 0x62, 0x77)

    def section(title_text: str, rows: list[tuple[str, object | None]]) -> None:
        doc.add_heading(title_text, level=2)
        table = doc.add_table(rows=0, cols=2)
        table.style = "Light Grid Accent 1"
        for label, value in rows:
            row = table.add_row()
            left = row.cells[0]
            right = row.cells[1]
            left.text = label
            for run in left.paragraphs[0].runs:
                run.bold = True
            right.text = "" if value is None else str(value)

    section(
        "1. Información general",
        [
            ("Nombre", charter.project_name),
            ("Descripción", charter.description),
            ("Organización", charter.organization_id),
            ("Unidad de negocio", charter.business_unit_id),
            ("Departamento", charter.department_id),
        ],
    )

    section(
        "2. Stakeholders",
        [
            ("Sponsor", charter.sponsor),
            ("Email sponsor", charter.sponsor_email),
            ("Líder de negocio", charter.business_leader),
            ("Email líder negocio", charter.business_leader_email),
            ("Líder técnico", charter.tech_leader),
            ("Email líder técnico", charter.tech_leader_email),
            ("Project Manager", charter.pm_id),
        ],
    )

    section(
        "3. Clasificación y alcance",
        [
            ("Tipo", charter.project_type),
            ("Prioridad", charter.priority),
            ("Objetivo", charter.objective),
            ("Restricciones", charter.restrictions),
            ("Riesgos (resumen)", charter.risks_summary),
            ("Alcance", charter.scope),
            ("Personas clave", charter.key_people),
            ("Beneficios", charter.benefits),
        ],
    )

    section(
        "4. Gestión del proyecto",
        [
            ("Folio", project.folio),
            ("Fase", project.phase),
            ("Salud", project.health_status),
            ("Inicio", project.start_date),
            ("Fin", project.end_date),
            ("Presupuesto", project.budget),
            ("Avance", f"{project.progress}%"),
        ],
    )

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def generate_charter_docx(
    db: AsyncSession,
    *,
    tenant_id: UUID | str,
    project: Project,
    charter: ProjectCharter,
    created_by: UUID | str | None = None,
) -> Document:
    """BUG-028 — crea/actualiza el `Document` category=charter con el
    archivo real en storage.

    Si ya existe un Document charter para el proyecto, **sobrescribe** el
    archivo (mismo Document.id) y bumpea `version`. No crea otro registro
    para evitar duplicados confusos en la vista de documentos.
    """
    tenant_id_s = str(tenant_id)
    existing = (
        await db.execute(
            select(Document).where(
                Document.project_id == str(project.id),
                Document.category == "charter",
                Document.is_current.is_(True),
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    data = _render_charter_docx(charter, project)

    if existing is None:
        folio = await next_folio(db, tenant_id=tenant_id_s, prefix="DOC")
        doc = Document(
            tenant_id=tenant_id_s,
            project_id=str(project.id),
            folio=folio,
            title=f"Project Charter — {project.name}",
            description="Documento fundacional del proyecto, generado automáticamente.",
            status="current",
            category="charter",
            mime_type=DOCX_CONTENT_TYPE,
            is_current=True,
            version=1,
            uploaded_by=str(created_by) if created_by else None,
            uploaded_at=datetime.now(UTC),
            created_by=str(created_by) if created_by else None,
        )
        db.add(doc)
        await db.flush()
    else:
        doc = existing
        doc.version = (doc.version or 1) + 1
        doc.mime_type = DOCX_CONTENT_TYPE
        doc.title = f"Project Charter — {project.name}"
        doc.uploaded_at = datetime.now(UTC)
        if created_by:
            doc.uploaded_by = str(created_by)

    file_url, _ = save_document_bytes(
        tenant_id_s,
        str(project.id),
        str(doc.id),
        data=data,
        ext="docx",
        content_type=DOCX_CONTENT_TYPE,
    )
    doc.file_url = file_url
    doc.size_bytes = len(data)
    await db.flush()
    return doc
