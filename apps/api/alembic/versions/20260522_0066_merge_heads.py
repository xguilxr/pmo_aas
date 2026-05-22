"""Merge heads 0064 (client_logo_url) + 0065 (status_rag).

Sprint 26 Bloque 1: ENH-100 (0064) y ENH-101 (0065) mergearon a main
en paralelo, ambos con ``down_revision='20260510_0062'``. Eso dejó dos
heads abiertas en alembic. Esta revisión los une en un único head para
que la siguiente migración (ENH-097 / 0067) pueda chainear de manera
lineal y ``alembic upgrade head`` no falle con "Multiple head revisions".

Sin cambios de schema — solo metadata.

Revision ID: 20260522_0066
Revises: 20260522_0064, 20260522_0065
Create Date: 2026-05-22 00:00:00
"""
from collections.abc import Sequence

revision: str = "20260522_0066"
down_revision: tuple[str, str] = ("20260522_0064", "20260522_0065")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
