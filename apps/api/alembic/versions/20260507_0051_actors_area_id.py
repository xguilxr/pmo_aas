"""actors.area_id directo (Actor sin team puede vivir bajo Área) — ENH-084 rework.

Revision ID: 20260507_0051
Revises: 20260507_0050
Create Date: 2026-05-07 19:00:00

Owner pidió que un Actor pueda asignarse a un Área directamente,
sin obligar a crear un Team intermedio. Hasta hoy, los actores
sin team caían en `orphan_actors` (root) o se promovían a PMO
por heurística `user_id IS NOT NULL`. Este cambio agrega
`actors.area_id` (nullable, FK SET NULL) para permitir asociación
explícita Actor → Área sin Team.

Backfill: por cada actor con `team_id` no nulo, copiar
`teams.area_id` a `actors.area_id` para que el campo quede
consistente con la jerarquía actual. Para actores promovidos a
PMO via user_id, dejar `area_id` apuntando al área PMO del tenant.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0051"
down_revision: str | None = "20260507_0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "actors",
        sa.Column("area_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_actors_area_id",
        "actors",
        "areas",
        ["area_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_actors_tenant_area",
        "actors",
        ["tenant_id", "area_id"],
    )

    bind = op.get_bind()
    # Backfill 1: actor con team → copia team.area_id.
    bind.execute(
        sa.text(
            "UPDATE actors SET area_id = ("
            "  SELECT t.area_id FROM teams t WHERE t.id = actors.team_id"
            ") WHERE team_id IS NOT NULL"
        )
    )
    # Backfill 2: actor con user_id (PMO sync) y sin team → área PMO
    # del tenant.
    bind.execute(
        sa.text(
            "UPDATE actors SET area_id = ("
            "  SELECT a.id FROM areas a "
            "  WHERE a.tenant_id = actors.tenant_id AND a.name = 'PMO' LIMIT 1"
            ") WHERE team_id IS NULL AND user_id IS NOT NULL AND area_id IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_actors_tenant_area", table_name="actors")
    op.drop_constraint("fk_actors_area_id", "actors", type_="foreignkey")
    op.drop_column("actors", "area_id")
