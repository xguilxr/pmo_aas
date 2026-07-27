"""US-191 — tabla `project_health_evaluations`.

Evaluación periódica de salud del PM: 5 dimensiones (cronograma,
presupuesto, riesgos, decisiones, recursos) + overall (la "sexta",
salud del proyecto como un todo) con fecha de evaluación. Cada guardado
es un registro histórico para ver la evolución en el tiempo.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0096"
down_revision: str | None = "20260718_0095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_health_evaluations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.Date(), nullable=False),
        sa.Column("schedule", sa.String(8)),
        sa.Column("budget", sa.String(8)),
        sa.Column("risks", sa.String(8)),
        sa.Column("decisions", sa.String(8)),
        sa.Column("resources", sa.String(8)),
        sa.Column("overall", sa.String(8), nullable=False),
        sa.Column("note", sa.String(2000)),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_health_evals_project_date",
        "project_health_evaluations",
        ["project_id", "evaluated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_health_evals_project_date", table_name="project_health_evaluations")
    op.drop_table("project_health_evaluations")
