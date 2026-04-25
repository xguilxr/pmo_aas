"""Normaliza users.role_type: viewer → user + backfill NULL → user.

Revision ID: 20260425_0028
Revises: 20260424_0027
Create Date: 2026-04-25 00:00:00

US-076 + DEC-024 — eliminar `viewer` del vocabulario de role_type.
Post-DEC-024 solo existen `admin` y `user`. Cualquier registro con
`role_type='viewer'` se migra a `'user'` (en la práctica ganan CRUD
libre en los recursos de negocio; pierden nada concreto porque
viewer era read-only de todo y ahora user también puede hacer todo
salvo las 5 capabilities admin).

Backfill adicional: cualquier `role_type IS NULL` restante (users
pre-migración 0026 que quedaron afuera) se normaliza a `'user'`
para que el gate nuevo tenga un default consistente.

No toca tablas `roles` ni `user_roles` — borrado físico difiere a
Sprint 7 (US-081).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260425_0028"
down_revision: str | None = "20260424_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Normaliza viewer → user (DEC-024 elimina viewer).
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_type = 'user'
            WHERE role_type = 'viewer'
            """
        )
    )
    # Backfill de NULL restantes → user.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_type = 'user'
            WHERE role_type IS NULL
            """
        )
    )


def downgrade() -> None:
    # Sin downgrade real — no se puede reconstruir quién era viewer.
    # No-op intencional.
    pass
