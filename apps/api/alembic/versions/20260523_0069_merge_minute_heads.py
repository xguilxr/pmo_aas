"""Merge heads 20260522_0068 (scheduled_minutes) + 20260523_0068 (minute_origin).

Sprint 26 Bloque 0 lanes ENH-107 y ENH-106 mergearon a main en paralelo,
ambos con ``down_revision='20260522_0067'``. Eso dejó dos heads abiertas
en alembic. Esta revisión los une en un único head para que
``alembic upgrade head`` no falle con "Multiple head revisions".

Sin cambios de schema — solo metadata.

Revision ID: 20260523_0069
Revises: 20260522_0068, 20260523_0068
Create Date: 2026-05-23 12:00:00
"""
from collections.abc import Sequence

revision: str = "20260523_0069"
down_revision: tuple[str, str] = ("20260522_0068", "20260523_0068")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
