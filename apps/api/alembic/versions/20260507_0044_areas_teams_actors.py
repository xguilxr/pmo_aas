"""areas + teams + actors (catálogo tenant) — US-097.

Revision ID: 20260507_0044
Revises: 20260506_0043
Create Date: 2026-05-07 00:00:00

Tres tablas tenant-scope para el catálogo Áreas → Equipos → Actores:

- `areas` — área organizacional (top-level del catálogo).
- `teams` — equipo dentro de un área (1:N areas → teams).
- `actors` — persona; pertenece opcionalmente a un equipo. Puede o no
  tener cuenta de usuario (`user_id` nullable).

No toca `project_areas` (US-091, scope-proyecto). Estas tablas son
catálogo maestro reutilizable a través de proyectos.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0044"
down_revision: str | None = "20260506_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_areas_tenant_name"),
    )
    op.create_index("ix_areas_tenant_active", "areas", ["tenant_id", "is_active"])

    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "area_id",
            sa.String(length=36),
            sa.ForeignKey("areas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "area_id", "name", name="uq_teams_area_name"),
    )
    op.create_index("ix_teams_tenant_area", "teams", ["tenant_id", "area_id"])

    op.create_table(
        "actors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.String(length=36),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "email", name="uq_actors_tenant_email"),
    )
    op.create_index("ix_actors_tenant_team", "actors", ["tenant_id", "team_id"])
    op.create_index("ix_actors_tenant_user", "actors", ["tenant_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_actors_tenant_user", table_name="actors")
    op.drop_index("ix_actors_tenant_team", table_name="actors")
    op.drop_table("actors")
    op.drop_index("ix_teams_tenant_area", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_areas_tenant_active", table_name="areas")
    op.drop_table("areas")
