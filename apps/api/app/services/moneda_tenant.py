"""BUG-092 — la moneda preferida del inquilino, leída donde hace falta.

El ajuste `tenant.settings.currency` deja de ser «la moneda» y pasa a ser **la
preferida**: el valor que se aplica a los proyectos que no eligieron uno propio.
Es el cambio de significado que pidió el owner, y es el que convierte un ajuste
que nadie leía en el valor inicial de una elección que sí se usa.

Vive aparte de `dominio/moneda.py` a propósito: aquello decide **qué moneda
aplica** dadas dos candidatas y no toca la base; esto va a buscar una de las
dos. Mezclarlos ataría la regla a una sesión y `app/dominio/` no puede
importar SQLAlchemy (DEV-02).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dominio.moneda import es_valida
from app.models.tenant import Tenant


async def preferida(db: AsyncSession, tenant_id: str | UUID | None) -> str | None:
    """La moneda preferida del inquilino, o `None` si no declara ninguna válida.

    Devuelve `None` y no la de por defecto: quien decide el fallback es
    `dominio.moneda.resolver`, que es el único sitio donde está escrito el
    orden. Dos sitios decidiendo lo mismo es cómo empiezan a discrepar.
    """
    if tenant_id is None:
        return None
    t = (
        await db.execute(select(Tenant.settings).where(Tenant.id == str(tenant_id)))
    ).scalar_one_or_none()
    codigo = (t or {}).get("currency")
    return str(codigo) if es_valida(codigo) else None
