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
from app.core.errors import forbidden, validation_error
from app.db.session import get_db
from app.services.pdf_renderer import html_to_pdf
from app.services.reports.engine import (
    ReportScope,
    ReportWindow,
    render_template,
)

router = APIRouter(prefix="/report-builder", tags=["report_builder"])


class RenderRequest(BaseModel):
    template: str = Field(
        ...,
        description="Template id (UUID) o code seed (`L3-AVANCE`, ...).",
    )
    project_id: UUID | None = None
    organization_id: UUID | None = None
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
        raise forbidden("Sin tenant activo")

    if payload.level == 3 and not payload.project_id:
        raise validation_error(
            "project_id es obligatorio para reportes Nivel 3",
            {"project_id": "required"},
        )

    scope = ReportScope(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        organization_id=payload.organization_id,
        program_id=payload.program_id,
        level=payload.level,
        area_id=payload.area_id,
    )
    window = ReportWindow(
        cut_off_date=payload.cut_off_date or date.today(),
        window_days=payload.window_days,
    )

    result = await render_template(
        db,
        payload.template,
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


class ExportRequest(BaseModel):
    """Body de POST /report-builder/templates/{template_id}/export."""

    project_id: UUID | None = None
    organization_id: UUID | None = None
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
        raise forbidden("Sin tenant activo")

    if payload.level == 3 and not payload.project_id:
        raise validation_error(
            "project_id es obligatorio para reportes Nivel 3",
            {"project_id": "required"},
        )

    scope = ReportScope(
        tenant_id=tenant_id,
        project_id=payload.project_id,
        organization_id=payload.organization_id,
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
