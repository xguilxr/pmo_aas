"""US-186 — Organigramas con utilización por scope (Revamp 1.0 Fase 2).

- GET /programs/{id}/organigrama/export        — programa
- GET /organizations/{id}/organigrama/export   — organización/portafolio
- GET /capacity/organigrama/export             — tenant (organigrama global,
  para tenants en modo portafolios donde los recursos son tenant-wide)

XLSX de 2 hojas: "Organigrama" (recursos activos + %FTE en scope + %FTE
total tenant) y "Uso mensual" (Recurso × Mes, 12 meses rolling, alertas
fill amarillo ≥80% / rojo >100%). Las participaciones se SUMAN por
recurso a través de los proyectos del scope.
"""
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import forbidden, not_found
from app.db.session import get_db
from app.models.organization import Organization, Program
from app.models.tenant import Tenant
from app.services.capacity import monthly_utilization
from app.services.filename_slug import artifact_filename
from app.services.organigrama_export import XLSX_MIME, export_utilizacion_xlsx

programs_router = APIRouter(
    prefix="/programs/{program_id}/organigrama", tags=["organigrama"]
)
orgs_router = APIRouter(
    prefix="/organizations/{organization_id}/organigrama", tags=["organigrama"]
)
tenant_router = APIRouter(prefix="/capacity/organigrama", tags=["organigrama"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


def _stream(data: bytes, base_name: str) -> StreamingResponse:
    filename = artifact_filename(base_name, "organigrama", "xlsx")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
    }
    return StreamingResponse(BytesIO(data), media_type=XLSX_MIME, headers=headers)


async def _build(
    db: AsyncSession, tenant_id: UUID, scope_type: str, scope_id: str | None
) -> bytes:
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    util = await monthly_utilization(
        db, tenant, scope_type=scope_type, scope_id=scope_id
    )
    return export_utilizacion_xlsx(months=util["months"], rows=util["rows"])


@programs_router.get("/export")
async def export_program_organigrama(
    program_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    program = (
        await db.execute(
            select(Program).where(
                Program.id == str(program_id), Program.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if program is None:
        raise not_found("Programa")
    data = await _build(db, tenant_id, "program", str(program_id))
    return _stream(data, program.name)


@orgs_router.get("/export")
async def export_organization_organigrama(
    organization_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant(cu)
    org = (
        await db.execute(
            select(Organization).where(
                Organization.id == str(organization_id),
                Organization.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if org is None:
        raise not_found("Organización")
    data = await _build(db, tenant_id, "organization", str(organization_id))
    return _stream(data, org.name)


@tenant_router.get("/export")
async def export_tenant_organigrama(
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """Organigrama global del tenant (modo portafolios: recursos
    reutilizables tenant-wide)."""
    tenant_id = _tenant(cu)
    data = await _build(db, tenant_id, "tenant", None)
    return _stream(data, "global")
