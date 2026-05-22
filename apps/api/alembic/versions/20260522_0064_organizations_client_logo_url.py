"""ENH-100 — organizations.client_logo_url (logo del cliente del tenant).

Adds a separate `client_logo_url` column to `organizations`. Semantics:
`logo_url`        = brand of this org (the tenant/PMO itself)
`client_logo_url` = brand of the *customer* of this org, used in reports
                    header (EP020 Report Builder).

Revision ID: 20260522_0064
Revises: 20260510_0062

Coordinator note (Sprint 26 Bloque 1): siblings 0063 (ENH-097) and 0065
(ENH-101) are being created in parallel. We anchor `down_revision` on
`0062` (latest on `main` at branch time) so the three migrations can be
linearized at merge time — the second/third PRs to land rebase their
`down_revision` to the previous head.

Create Date: 2026-05-22 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260522_0064"
down_revision: str | None = "20260510_0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.add_column(
            sa.Column("client_logo_url", sa.String(length=500), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.drop_column("client_logo_url")
