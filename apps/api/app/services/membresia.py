"""US-214 / AM-16 — Quién pertenece a qué inquilino, según la base.

Cada función de este módulo consulta la tabla. Ninguna mira el JWT. Esa es toda
la razón de que exista: hasta US-214 el cambio de inquilino se autorizaba contra
el claim `tenant_ids`, y con membresía multi-inquilino eso significa que revocar
una membresía no surte efecto hasta que el token caduque.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user_tenant_membership import UserTenantMembership


async def tiene_membresia(
    db: AsyncSession, *, user_id: UUID | str, tenant_id: UUID | str
) -> bool:
    """Si el usuario tiene membresía **viva** en ese inquilino.

    Se llama en cada petición autenticada. Es una consulta por el índice
    compuesto `(user_id, tenant_id)`, y es el precio de que revocar signifique
    revocar: sin ella, una membresía retirada sigue valiendo la hora que le queda
    al token.
    """
    return (
        await db.execute(
            select(UserTenantMembership.id).where(
                UserTenantMembership.user_id == str(user_id),
                UserTenantMembership.tenant_id == str(tenant_id),
                UserTenantMembership.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none() is not None


async def inquilinos_de(
    db: AsyncSession, *, user_id: UUID | str
) -> list[tuple[str, str, str | None]]:
    """`(id, nombre, slug)` de los inquilinos vivos del usuario, por nombre.

    Alimenta el selector del encabezado. Trae el nombre porque un desplegable de
    identificadores no se puede usar, y una segunda consulta por cada uno para
    resolverlos sería N+1 en el camino de cada carga de página.
    """
    filas = (
        await db.execute(
            select(Tenant.id, Tenant.name, Tenant.slug)
            .join(
                UserTenantMembership,
                UserTenantMembership.tenant_id == Tenant.id,
            )
            .where(
                UserTenantMembership.user_id == str(user_id),
                UserTenantMembership.revoked_at.is_(None),
            )
            .order_by(Tenant.name)
        )
    ).all()
    return [(str(i), n, s) for i, n, s in filas]


async def conceder(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    tenant_id: UUID | str,
    concedida_por: UUID | str | None,
) -> UserTenantMembership:
    """Da o **reactiva** una membresía.

    Reactiva en vez de crear otra fila cuando ya existía revocada: la restricción
    de unicidad es `(user_id, tenant_id)` sin importar el estado, y a propósito —
    dos filas para la misma pareja obligarían a decidir cuál manda cada vez que
    se lee, que es una decisión que no hace falta tomar.

    Reactivar **conserva** `revoked_at` en nulo pero deja la traza en la
    auditoría: la pregunta «¿se le quitó y se le volvió a dar?» la contesta el
    registro, no esta fila.
    """
    existente = (
        await db.execute(
            select(UserTenantMembership).where(
                UserTenantMembership.user_id == str(user_id),
                UserTenantMembership.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        existente.revoked_at = None
        existente.revoked_by_user_id = None
        existente.granted_by_user_id = (
            str(concedida_por) if concedida_por else None
        )
        await db.flush()
        return existente
    nueva = UserTenantMembership(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        granted_by_user_id=str(concedida_por) if concedida_por else None,
    )
    db.add(nueva)
    await db.flush()
    return nueva


async def revocar(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    tenant_id: UUID | str,
    revocada_por: UUID | str | None,
) -> bool:
    """Marca la membresía como revocada. `False` si no había ninguna viva.

    Se **marca** y no se borra: «¿quién tuvo acceso a este cliente y cuándo se le
    quitó?» no se contesta con una fila borrada, y es exactamente la pregunta de
    una auditoría.
    """
    fila = (
        await db.execute(
            select(UserTenantMembership).where(
                UserTenantMembership.user_id == str(user_id),
                UserTenantMembership.tenant_id == str(tenant_id),
                UserTenantMembership.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if fila is None:
        return False
    fila.revoked_at = datetime.now(UTC)
    fila.revoked_by_user_id = str(revocada_por) if revocada_por else None
    await db.flush()
    return True
