"""Render + Export endpoints del Report Builder — US-123 + US-130 (EP020).

- `POST /report-builder/render?format=json|pdf` — toma template +
  scope + window inline (US-123).
- `POST /report-builder/templates/{template_id}/export?format=pdf` —
  shape específico del AC US-130 (PM descarga el reporte custom como
  PDF reusando el motor compartido).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, mensaje, validation_error
from app.db.session import get_db
from app.services.pdf_renderer import html_to_pdf
from app.services.reports.engine import (
    ReportScope,
    ReportWindow,
    render_template,
)

router = APIRouter(prefix="/report-builder", tags=["report_builder"])


def _resolve_template_ref(payload: RenderRequest):
    """ENH-138: si vienen `section_codes` inline, construye una plantilla
    efímera (sin persistir) para el preview en vivo del canvas; si no, usa
    `template` (id/seed code)."""
    from app.models.report_builder_template import ReportBuilderTemplate

    if payload.section_codes is not None:
        mode = (payload.composition_mode or "A").upper()
        return ReportBuilderTemplate(
            id="preview",
            code="custom",
            name=payload.name or "Reporte custom",
            level=payload.level,
            composition_mode="B" if mode == "B" else "A",
            section_codes=list(payload.section_codes),
            default_parameters=payload.params or {},
        )
    if not payload.template:
        raise validation_error(
            mensaje(
                que="Se requiere `template` o `section_codes`",
                porque="Sin plantilla ni secciones, el informe saldría vacío.",
                accion="Elige una plantilla, o indica qué secciones incluir.",
            ),
            {"template": "required"},
        )
    return payload.template


class RenderRequest(BaseModel):
    # ENH-138: `template` ahora es opcional. Si se envían `section_codes`
    # inline (canvas del builder), se renderiza una plantilla efímera sin
    # persistir; si no, se resuelve `template` por id/code seed.
    template: str | None = Field(
        default=None,
        description="Template id (UUID) o code seed (`L3-AVANCE`, ...).",
    )
    # ENH-138: composición del canvas para preview en vivo.
    section_codes: list[str] | None = None
    composition_mode: str | None = None
    # ENH-140: nombre del reporte al guardarlo en el historial.
    name: str | None = None
    project_id: UUID | None = None
    organization_id: UUID | None = None
    #: US-209 — el nivel intermedio que faltaba.
    portfolio_id: UUID | None = None
    program_id: UUID | None = None
    level: int = Field(default=3, ge=1, le=4)
    cut_off_date: date | None = None
    window_days: int = Field(default=14, ge=1, le=365)
    # BUG-063: filtro de área a nivel reporte (param transversal de la
    # barra superior del builder). None = todas las áreas.
    area_id: UUID | None = None
    params: dict[str, dict[str, Any]] | None = None


class RenderResponse(BaseModel):
    html: str
    json_data: dict[str, Any] = Field(alias="json")
    sections_meta: list[dict[str, Any]]

    class Config:
        populate_by_name = True


@router.post("/render", response_model=RenderResponse, response_model_by_alias=True)
async def render_report(
    payload: RenderRequest,
    format: str = Query(default="json", pattern="^(json|pdf)$"),
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
):
    """Renderiza una plantilla del Report Builder."""
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise forbidden(mensaje(
            que="Sin tenant activo",
            porque="La cuenta de plataforma no está mirando ninguna organización concreta y esta vista es de una.",
            accion="Elige una organización en el selector y vuelve a intentarlo.",
        ))

    if payload.level == 3 and not payload.project_id:
        raise validation_error(
            mensaje(
                que="project_id es obligatorio para reportes Nivel 3",
                porque="Un informe de nivel 3 baja al detalle de un proyecto concreto.",
                accion="Indica el proyecto, o pide un informe de nivel superior.",
            ),
            {"project_id": "required"},
        )

    scope = ReportScope(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        organization_id=payload.organization_id,
        portfolio_id=payload.portfolio_id,
        program_id=payload.program_id,
        level=payload.level,
        area_id=payload.area_id,
    )
    window = ReportWindow(
        cut_off_date=payload.cut_off_date or date.today(),
        window_days=payload.window_days,
    )

    template_ref = _resolve_template_ref(payload)

    result = await render_template(
        db,
        template_ref,
        scope,
        window,
        params_overrides=payload.params,
    )

    if format == "pdf":
        # US-130 — export PDF reusando el motor compartido.
        pdf_bytes = html_to_pdf(result.html)
        return Response(content=pdf_bytes, media_type="application/pdf")

    return RenderResponse(
        html=result.html,
        json=result.json,
        sections_meta=result.sections_meta,
    )


class SaveReportResponse(BaseModel):
    report_id: str
    title: str


@router.post("/save", response_model=SaveReportResponse)
async def save_report(
    payload: RenderRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
):
    """ENH-140: genera y persiste un snapshot del reporte en el Historial
    del proyecto (sin programar envíos). Acepta el canvas inline o un
    template guardado."""
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise forbidden(mensaje(
            que="Sin tenant activo",
            porque="La cuenta de plataforma no está mirando ninguna organización concreta y esta vista es de una.",
            accion="Elige una organización en el selector y vuelve a intentarlo.",
        ))
    if not payload.project_id:
        raise validation_error(
            mensaje(
                que="project_id es obligatorio para guardar el reporte al historial",
                porque="El historial se guarda por proyecto; sin él no habría dónde encontrarlo.",
                accion="Indica el proyecto, o genera el informe sin guardarlo.",
            ),
            {"project_id": "required"},
        )

    scope = ReportScope(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        organization_id=payload.organization_id,
        portfolio_id=payload.portfolio_id,
        program_id=payload.program_id,
        level=payload.level,
        area_id=payload.area_id,
    )
    window = ReportWindow(
        cut_off_date=payload.cut_off_date or date.today(),
        window_days=payload.window_days,
    )

    from app.services.reports.engine import _load_template
    from app.services.reports.persistence import persist_builder_export

    template_obj = await _load_template(db, _resolve_template_ref(payload))
    result = await render_template(
        db, template_obj, scope, window, params_overrides=payload.params
    )
    rep = await persist_builder_export(
        db,
        tenant_id=tenant_id,
        project_id=scope.project_id,
        template=template_obj,
        cut_off_date=window.cut_off_date,
        sections_snapshot=result.json,
        html_content=result.html,
        created_by=cu.id,
        status="draft",
    )
    await db.commit()
    return SaveReportResponse(report_id=str(rep.id), title=rep.title)


class ExportRequest(BaseModel):
    """Body de POST /report-builder/templates/{template_id}/export."""

    project_id: UUID | None = None
    organization_id: UUID | None = None
    #: US-209 — el nivel intermedio que faltaba.
    portfolio_id: UUID | None = None
    program_id: UUID | None = None
    level: int = Field(default=3, ge=1, le=4)
    cut_off_date: date | None = None
    window_days: int = Field(default=14, ge=1, le=365)
    area_id: UUID | None = None
    params: dict[str, dict[str, Any]] | None = None


@router.post("/templates/{template_id}/export")
async def export_template_pdf(
    template_id: UUID,
    payload: ExportRequest,
    format: str = Query(default="pdf", pattern="^(pdf|html)$"),
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
):
    """US-130 — descarga el reporte custom como PDF (o HTML).

    Reusa `render_template` (US-123). El footer del PDF incluye PM,
    fecha de emisión, plantilla aplicada y scope (cableado en
    `templates/pdf/builder.html`).
    """
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise forbidden(mensaje(
            que="Sin tenant activo",
            porque="La cuenta de plataforma no está mirando ninguna organización concreta y esta vista es de una.",
            accion="Elige una organización en el selector y vuelve a intentarlo.",
        ))

    if payload.level == 3 and not payload.project_id:
        raise validation_error(
            mensaje(
                que="project_id es obligatorio para reportes Nivel 3",
                porque="Un informe de nivel 3 baja al detalle de un proyecto concreto.",
                accion="Indica el proyecto, o pide un informe de nivel superior.",
            ),
            {"project_id": "required"},
        )

    scope = ReportScope(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        organization_id=payload.organization_id,
        portfolio_id=payload.portfolio_id,
        program_id=payload.program_id,
        level=payload.level,
        area_id=payload.area_id,
    )
    window = ReportWindow(
        cut_off_date=payload.cut_off_date or date.today(),
        window_days=payload.window_days,
    )
    # Cargamos el template explícitamente para tener el ORM object al
    # persistir (US-140); `render_template` lo acepta por id pero no lo
    # devuelve.
    from sqlalchemy import select as _select

    from app.models.report_builder_template import ReportBuilderTemplate

    tpl_row = (
        await db.execute(
            _select(ReportBuilderTemplate).where(
                ReportBuilderTemplate.id == str(template_id)
            )
        )
    ).scalar_one_or_none()
    if tpl_row is None:
        from app.core.errors import not_found

        raise not_found("Plantilla de reporte")

    result = await render_template(
        db,
        tpl_row,
        scope,
        window,
        params_overrides=payload.params,
    )

    # US-140 — persistir snapshot. Solo cuando hay project_id (Nivel 3/4);
    # exports L1/L2 no tienen home en `reports` (su modelo asume
    # `project_id`).
    if scope.project_id:
        from app.services.reports.persistence import persist_builder_export

        await persist_builder_export(
            db,
            tenant_id=tenant_id,
            project_id=scope.project_id,
            template=tpl_row,
            cut_off_date=window.cut_off_date,
            sections_snapshot=result.json,
            html_content=result.html,
            created_by=cu.id,
        )
        await db.commit()

    if format == "html":
        return Response(content=result.html, media_type="text/html")
    pdf_bytes = html_to_pdf(result.html)
    return Response(content=pdf_bytes, media_type="application/pdf")
