"""US-132 — Endpoint del Gantt snapshot para S-19 (EP020).

`GET /projects/{id}/gantt/snapshot?wbs_level=1&window_start=...&window_end=...`
devuelve `image/svg+xml` (o `image/png` cuando llegue el renderer
headless en v1.x).

El consumidor primario es la sección S-19 del Report Builder: el
HTML de la sección embebe la URL vía `<img src="...">` y el motor
PDF (WeasyPrint) la inlinea.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, mensaje
from app.db.session import get_db
from app.services.reports.gantt_renderer import render_project_gantt

router = APIRouter(tags=["gantt_snapshot"])


@router.get("/projects/{project_id}/gantt/snapshot")
async def project_gantt_snapshot(
    project_id: UUID,
    wbs_level: int = Query(default=1, ge=1, le=5),
    window_start: date | None = Query(default=None),
    window_end: date | None = Query(default=None),
    format: str = Query(default="svg", pattern="^(svg|png)$"),
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_authenticated()),
):
    """Devuelve el Gantt agregado a WBS-N como SVG (default) o PNG.

    PNG todavía no implementado: el AC v1.0 acepta SVG como contrato
    estándar (embebible vía `<img>` y por WeasyPrint en el PDF).
    """
    tenant_id = cu.effective_tenant_id
    if tenant_id is None:
        raise forbidden(mensaje(
            que="Sin tenant activo",
            porque="La cuenta de plataforma no está mirando ninguna organización concreta y esta vista es de una.",
            accion="Elige una organización en el selector y vuelve a intentarlo.",
        ))

    svg = await render_project_gantt(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        wbs_level=wbs_level,
        window_start=window_start,
        window_end=window_end,
    )

    if format == "png":
        # Compatibilidad con el contrato — devolvemos SVG con header PNG
        # NO es correcto. Mejor: 501 explícito hasta que el renderer
        # headless llegue (no es bloqueante para v1.0).
        return Response(
            content=(
                '{"detail":"PNG no soportado en v1.0; usa format=svg"}'
            ),
            media_type="application/json",
            status_code=501,
        )

    return Response(content=svg, media_type="image/svg+xml")
