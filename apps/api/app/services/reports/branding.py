"""ENH-146 — branding compartido para reportes (logo PMO + logo cliente).

Todos los stacks de reporte (PDF Jinja/WeasyPrint, builder, scope-status,
HTML inline) consumen el mismo contrato para pintar la banda de marca:

    {
        "tenant_name":     str | None,   # nombre de la PMO (lado izquierdo)
        "tenant_logo_url": str | None,   # logo de la PMO (data-URL o URL)
        "client_logo_url": str | None,   # logo del cliente de la organización
    }

Los logos viven como TEXT/data-URL en `tenants.logo_url`,
`organizations.client_logo_url` y, como fallback, `organizations.logo_url`.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.tenant import Tenant


async def load_report_branding(
    db: AsyncSession,
    tenant_id: UUID | str,
    organization_id: UUID | str | None = None,
) -> dict[str, str | None]:
    """Devuelve el branding para inyectar en cualquier contexto de reporte.

    `client_logo_url` usa `organizations.client_logo_url` y cae a
    `organizations.logo_url` cuando el primero está vacío. Si no hay
    organización en scope (ej. reporte de portafolio), queda en None.
    """
    row = (
        await db.execute(
            select(Tenant.name, Tenant.logo_url).where(Tenant.id == str(tenant_id))
        )
    ).first()
    tenant_name = row[0] if row else None
    tenant_logo_url = row[1] if row else None

    client_logo_url: str | None = None
    if organization_id is not None:
        orow = (
            await db.execute(
                select(
                    Organization.client_logo_url, Organization.logo_url
                ).where(Organization.id == str(organization_id))
            )
        ).first()
        if orow:
            client_logo_url = orow[0] or orow[1]

    return {
        "tenant_name": tenant_name,
        "tenant_logo_url": tenant_logo_url,
        "client_logo_url": client_logo_url,
    }
