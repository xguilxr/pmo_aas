"""US-183 — project_participations con FTE% y ciclo de vida de capacidad.

Agrega a `project_participations`: allocation_pct (FTE%, NULL = sin
cuantificar), assignment_type, status (tentativa|activa|cerrada|cancelada),
is_critical y phase. Backfill: status='activa' donde is_active, si no
'cerrada'. La saturación (services/capacity.py) suma allocation_pct de
participations status='activa' que intersectan la ventana temporal, contra
actors.project_capacity_pct (US-182).

Revision ID: 20260708_0093
Revises: 20260708_0092
Create Date: 2026-07-08 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260708_0093"
down_revision: str | None = "20260708_0092"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("project_participations") as batch:
        batch.add_column(sa.Column("allocation_pct", sa.Numeric(5, 2), nullable=True))
        batch.add_column(
            sa.Column(
                "assignment_type",
                sa.String(length=16),
                nullable=False,
                server_default="directa",
            )
        )
        batch.add_column(
            sa.Column(
                "status", sa.String(length=12), nullable=False, server_default="activa"
            )
        )
        batch.add_column(
            sa.Column("is_critical", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("phase", sa.String(length=32), nullable=True))
        batch.create_check_constraint(
            "ck_participations_assignment_type",
            "assignment_type IN ('directa','advisory','backup','shared_service','steerco_only')",
        )
        batch.create_check_constraint(
            "ck_participations_status",
            "status IN ('tentativa','activa','cerrada','cancelada')",
        )

    op.execute(
        "UPDATE project_participations SET status = 'cerrada' WHERE is_active = false"
        if op.get_bind().dialect.name != "sqlite"
        else "UPDATE project_participations SET status = 'cerrada' WHERE is_active = 0"
    )


def downgrade() -> None:
    with op.batch_alter_table("project_participations") as batch:
        batch.drop_constraint("ck_participations_status", type_="check")
        batch.drop_constraint("ck_participations_assignment_type", type_="check")
        batch.drop_column("phase")
        batch.drop_column("is_critical")
        batch.drop_column("status")
        batch.drop_column("assignment_type")
        batch.drop_column("allocation_pct")
