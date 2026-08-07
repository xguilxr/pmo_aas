"""Project Charter endpoints (US-012 / US-013).

GET  /projects/{id}/charter         — lee el charter con sección 4 derivada.
PATCH /projects/{id}/charter        — edita secciones 1–3.
GET  /projects/{id}/charter/pdf     — export HTML imprimible (PDF nativo
                                      queda post-MVP; el navegador puede
                                      imprimir el HTML a PDF).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.autorizacion import proyecto_autorizado
from app.core.errors import forbidden, mensaje
from app.db.session import get_db
from app.models.organization import BusinessUnit, Department
from app.models.project import Project
from app.models.project_charter import ProjectCharter
from app.schemas.project_charter import (
    CHARTER_REQUIRED_FIELDS,
    CharterCompleteness,
    CharterSection4,
    ProjectCharterRead,
    ProjectCharterUpdate,
)
from app.services.audit import write_audit
from app.services.charter_generator import generate_charter_docx

router = APIRouter(prefix="/projects", tags=["project_charters"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


async def _charter_de(
    db: AsyncSession, project_id: UUID, cu: CurrentUser
) -> tuple[Project, ProjectCharter]:
    """US-083: si el charter no existe (project legacy o pre-migración
    0030), lo crea on-the-fly con `project.name` como project_name.
    Garantiza que GET /charter nunca devuelve 404 para projects válidos.

    SEG-04 (2026-08-06): era la séptima copia del resolvedor de proyecto, y
    comprobaba solo el inquilino. El acta de constitución lleva presupuesto,
    patrocinador y alcance — o sea lo que menos conviene que lea alguien de
    otro proyecto. Ahora delega en `proyecto_autorizado`.
    """
    project = await proyecto_autorizado(db, project_id, cu)
    tenant_id = cu.effective_tenant_id
    charter = (
        await db.execute(
            select(ProjectCharter).where(ProjectCharter.project_id == project.id)
        )
    ).scalar_one_or_none()
    if charter is None:
        # Lazy auto-create: defensa contra projects sin charter (la
        # migración 0030 los cubre, pero un project creado después
        # podría faltar si el flow de creación no lo genera).
        charter = ProjectCharter(
            tenant_id=str(tenant_id),
            project_id=str(project.id),
            project_name=project.name or "Proyecto sin nombre",
            organization_id=project.organization_id,
        )
        db.add(charter)
        await db.flush()
        await db.commit()
        await db.refresh(charter)
    return project, charter


def _build_section4(project: Project) -> CharterSection4:
    """Datos de gestión sincronizados desde el proyecto (DEC-008)."""
    return CharterSection4(
        start_date=project.start_date,
        estimated_end_date=project.end_date,
        phase=project.phase,
        health_status=project.health_status,
        progress=project.progress,
        planned_progress=None,  # no existe en el modelo actual
        assigned_budget=project.budget,
        used_budget=project.actual_budget,
        assigned_hours=None,
        consumed_hours=None,
    )


def _completeness(charter: ProjectCharter) -> CharterCompleteness:
    """ENH-081 CA3: calcula campos faltantes contra `CHARTER_REQUIRED_FIELDS`.

    Un campo cuenta como "vacío" si es None o un string que tras strip queda
    en "". Otros tipos (int para priority) solo cuentan vacíos si son None.
    """
    missing: list[str] = []
    for field in CHARTER_REQUIRED_FIELDS:
        value = getattr(charter, field, None)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    return CharterCompleteness(
        is_complete=not missing,
        missing_fields=missing,
        required_fields=list(CHARTER_REQUIRED_FIELDS),
    )


def _read(charter: ProjectCharter, project: Project) -> ProjectCharterRead:
    return ProjectCharterRead(
        id=charter.id,
        project_id=charter.project_id,
        request_id=charter.request_id,
        project_name=charter.project_name,
        description=charter.description,
        organization_id=charter.organization_id,
        business_unit_id=charter.business_unit_id,
        department_id=charter.department_id,
        sponsor=charter.sponsor,
        sponsor_email=charter.sponsor_email,
        business_leader=charter.business_leader,
        business_leader_email=charter.business_leader_email,
        tech_leader=charter.tech_leader,
        tech_leader_email=charter.tech_leader_email,
        pm_id=charter.pm_id,
        project_type=charter.project_type,
        priority=charter.priority,
        objective=charter.objective,
        restrictions=charter.restrictions,
        risks_summary=charter.risks_summary,
        scope=charter.scope,
        key_people=charter.key_people,
        benefits=charter.benefits,
        section_4=_build_section4(project),
        completeness=_completeness(charter),
        created_at=charter.created_at,
        updated_at=charter.updated_at,
    )


@router.get("/{project_id}/charter", response_model=ProjectCharterRead)
async def get_charter(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    project, charter = await _charter_de(db, project_id, cu)
    return _read(charter, project)


@router.patch("/{project_id}/charter", response_model=ProjectCharterRead)
async def update_charter(
    project_id: UUID,
    body: ProjectCharterUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    project, charter = await _charter_de(db, project_id, cu)

    # Validar FKs BU/Depto si cambian
    data = body.model_dump(exclude_unset=True)
    bu_id = data.get("business_unit_id")
    dept_id = data.get("department_id")
    if bu_id is not None:
        bu = (
            await db.execute(
                select(BusinessUnit).where(
                    BusinessUnit.id == str(bu_id),
                    BusinessUnit.tenant_id == tenant_id,
                    BusinessUnit.organization_id == charter.organization_id,
                    BusinessUnit.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if bu is None:
            from app.core.errors import business_rule

            raise business_rule(mensaje(
                que="BU no pertenece a la organización del proyecto",
                porque="La unidad de negocio tiene que estar dentro de la organización del proyecto.",
                accion="Elige una unidad de esa organización.",
            ))
    if dept_id is not None:
        dept = (
            await db.execute(
                select(Department).where(
                    Department.id == str(dept_id),
                    Department.tenant_id == tenant_id,
                    Department.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if dept is None:
            from app.core.errors import business_rule

            raise business_rule(mensaje(
                que="Departamento no pertenece al tenant",
                porque="La referencia apunta fuera de tu organización y quedaría rota.",
                accion="Elige un departamento de tu tenant.",
            ))

    for field, value in data.items():
        # emails vienen como EmailStr; convertir a str para la BD
        setattr(
            charter,
            field,
            str(value) if field.endswith("_email") and value is not None else value,
        )
    await write_audit(
        db,
        action="charter.update",
        module="projects",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="charter",
        entity_id=str(charter.id),
    )
    await db.flush()
    # BUG-028: regenera el .docx y sube nueva versión al storage. Si el
    # generador falla (p. ej. R2 down), el commit del charter sigue
    # adelante — el doc se puede regenerar después por llamada explícita.
    try:
        await generate_charter_docx(
            db,
            tenant_id=tenant_id,
            project=project,
            charter=charter,
            created_by=cu.id,
        )
    except Exception as exc:  # pragma: no cover - log + no fail
        import logging

        logging.getLogger(__name__).warning(
            "charter_regen_failed project_id=%s err=%s", project.id, exc
        )
    await db.commit()
    await db.refresh(charter)
    await db.refresh(project)
    return _read(charter, project)


@router.get("/{project_id}/charter/download")
async def download_charter(
    project_id: UUID,
    format: str = "docx",
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """US-083: descarga directa del charter en .docx (default) o .pdf.

    A diferencia del flujo BUG-028 (que persiste el .docx en storage),
    este endpoint genera el archivo on-demand a partir del charter
    actual y lo devuelve como bytes inline, evitando tener que pasar
    por la lista de documentos.

    Soporta:
    - `format=docx` → genera con python-docx (mismo template de US-007).
    - `format=pdf`  → reusa la vista HTML imprimible y la rendere a
      PDF con weasyprint. Si weasyprint no está disponible (test
      env, etc.), devuelve el HTML con header
      `Content-Type: text/html` para que el browser ofrezca "Imprimir
      a PDF" como fallback.

    Funciona aunque el charter esté completamente vacío — la plantilla
    deja secciones en blanco con headers visibles.
    """
    from io import BytesIO
    from urllib.parse import quote

    from fastapi.responses import StreamingResponse

    from app.services.charter_generator import (
        DOCX_CONTENT_TYPE,
        _render_charter_docx,
        resolve_charter_logos,
    )

    fmt = (format or "docx").lower()
    if fmt not in ("docx", "pdf"):
        from app.core.errors import business_rule

        raise business_rule(
            mensaje(
                que=f"format inválido: {fmt}. Usa 'docx' o 'pdf'.",
                porque="Solo se generan esos dos formatos de acta.",
                accion="Pide el acta en `docx` o en `pdf`.",
            ),
            code="INVALID_FORMAT",
        )

    project, charter = await _charter_de(db, project_id, cu)

    # ENH-092: filename canónico `{project-slug}-charter.{ext}`.
    from app.services.filename_slug import artifact_filename

    filename = artifact_filename(
        charter.project_name or project.name, "charter", fmt,
    )
    safe_q = quote(filename)

    if fmt == "docx":
        logos = await resolve_charter_logos(db, _tenant(cu), project)
        data = _render_charter_docx(charter, project, logos)
        return StreamingResponse(
            BytesIO(data),
            media_type=DOCX_CONTENT_TYPE,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"; '
                    f"filename*=UTF-8''{safe_q}"
                ),
            },
        )

    # format=pdf: weasyprint sobre el HTML imprimible.
    from app.services.reports.branding import load_report_branding

    branding = await load_report_branding(
        db, _tenant(cu), project.organization_id
    )
    html = _build_printable_html(charter, project, branding)
    try:
        from weasyprint import HTML  # type: ignore

        pdf_bytes = HTML(string=html).write_pdf()
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"; '
                    f"filename*=UTF-8''{safe_q}"
                ),
            },
        )
    except Exception:
        # Fallback: devuelve HTML con disposición attachment renombrado
        # a .html. Better than 500.
        html_filename = filename.replace(".pdf", ".html")
        return StreamingResponse(
            BytesIO(html.encode("utf-8")),
            media_type="text/html",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{html_filename}"'
                ),
            },
        )


def _build_printable_html(
    charter: ProjectCharter,
    project: Project,
    branding: dict[str, str | None] | None = None,
) -> str:
    """Render del HTML imprimible. Extraído para reuso por
    `/charter/download?format=pdf` (US-083).

    ENH-153: si se pasa `branding` (de `load_report_branding`), pinta una
    banda de marca con logo de la PMO + logo del cliente en el header,
    igual que los reportes automatizados.
    """
    s4 = _build_section4(project)
    b = branding or {}

    def _logo(url: str | None, max_h: int, max_w: int) -> str:
        if not url:
            return ""
        return (
            f'<img src="{url}" alt="" style="max-height:{max_h}px;'
            f'max-width:{max_w}px;object-fit:contain;" />'
        )

    pmo_name = b.get("tenant_name") or ""
    brand_html = ""
    if b.get("tenant_logo_url") or b.get("client_logo_url") or pmo_name:
        name_span = (
            f'<span style="font-weight:600;font-size:14px;color:#182e4e;">'
            f"{pmo_name}</span>"
            if pmo_name
            else ""
        )
        brand_html = (
            '<div style="display:flex;align-items:center;'
            "justify-content:space-between;gap:16px;border-bottom:2px solid "
            '#182e4e;padding-bottom:10px;margin-bottom:16px;">'
            '<div style="display:flex;align-items:center;gap:10px;">'
            + _logo(b.get("tenant_logo_url"), 40, 200)
            + name_span
            + "</div>"
            + _logo(b.get("client_logo_url"), 36, 160)
            + "</div>"
        )

    def row(label: str, value) -> str:
        v = "" if value is None else str(value)
        return (
            "<tr>"
            "<th style='text-align:left;padding:6px 10px;background:#f4f6fa;"
            "font-weight:600;width:220px'>" + label + "</th>"
            "<td style='padding:6px 10px;border-bottom:1px solid #e6e8ef'>"
            + v
            + "</td></tr>"
        )

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Charter — {charter.project_name}</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; color:#1a1d29;
          max-width: 820px; margin: 32px auto; padding: 0 16px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 28px 0 8px; color:#182e4e; border-bottom:1px solid #cfd4e0; padding-bottom:4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .muted {{ color:#5a6277; font-size: 12px; }}
  @media print {{ body {{ margin: 0; }} }}
</style></head>
<body>
  <header>
    {brand_html}
    <h1>Project Charter — {charter.project_name}</h1>
    <p class="muted">Proyecto: {project.folio} · Generado on-demand</p>
  </header>

  <h2>1. Información general</h2>
  <table>
    {row("Nombre", charter.project_name)}
    {row("Descripción", charter.description)}
    {row("Organización", charter.organization_id)}
    {row("Unidad de negocio", charter.business_unit_id)}
    {row("Departamento", charter.department_id)}
  </table>

  <h2>2. Stakeholders</h2>
  <table>
    {row("Sponsor", charter.sponsor)}
    {row("Email sponsor", charter.sponsor_email)}
    {row("Líder de negocio", charter.business_leader)}
    {row("Email líder negocio", charter.business_leader_email)}
    {row("Líder técnico", charter.tech_leader)}
    {row("Email líder técnico", charter.tech_leader_email)}
    {row("Project Manager", charter.pm_id)}
  </table>

  <h2>3. Clasificación</h2>
  <table>
    {row("Tipo", charter.project_type)}
    {row("Prioridad", charter.priority)}
    {row("Objetivo", charter.objective)}
    {row("Alcance", charter.scope)}
    {row("Beneficios", charter.benefits)}
    {row("Restricciones", charter.restrictions)}
    {row("Resumen de riesgos", charter.risks_summary)}
    {row("Personas clave", charter.key_people)}
  </table>

  <h2>4. Gestión (sincronizado desde el proyecto)</h2>
  <table>
    {row("Fecha inicio", s4.start_date)}
    {row("Fecha fin estimada", s4.estimated_end_date)}
    {row("Fase", s4.phase)}
    {row("Salud", s4.health_status)}
    {row("Avance (%)", s4.progress)}
    {row("Presupuesto asignado", s4.assigned_budget)}
    {row("Presupuesto consumido", s4.used_budget)}
  </table>
</body></html>
"""


@router.get("/{project_id}/charter/pdf", response_class=HTMLResponse)
async def charter_printable(
    project_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve HTML imprimible a PDF. Un renderer PDF nativo queda como
    follow-up; el navegador puede imprimir esta vista (Ctrl+P) para
    obtener el PDF on-demand."""
    from app.services.reports.branding import load_report_branding

    project, charter = await _charter_de(db, project_id, cu)
    branding = await load_report_branding(
        db, _tenant(cu), project.organization_id
    )
    return HTMLResponse(content=_build_printable_html(charter, project, branding))
