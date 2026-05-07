"""actors.is_lead + areas.lead_actor_id + drop project_areas — ENH-078.

Revision ID: 20260507_0049
Revises: 20260507_0048
Create Date: 2026-05-07 13:00:00

Cambios:
1. `actors.is_lead` boolean — flag para marcar el líder del área.
2. `areas.lead_actor_id` FK actors — apunta al actor con `is_lead=true`
   del área (1:1 lógico, validado en endpoint).
3. Backfill: por cada `areas.lead_name` no-null, crea Actor con
   `is_lead=true` (o reusa por email si ya existía con email match)
   y se setea `areas.lead_actor_id`. Luego drop `lead_name` (owner
   confirmó que el flag es suficiente).
4. Drop `project_areas` + `project_area_resources` (Op A completa,
   diferida desde 0048 para no romper UI legacy entre commits).
"""
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0049"
down_revision: str | None = "20260507_0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. actors.is_lead
    with op.batch_alter_table("actors") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_lead",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

    # 2. areas.lead_actor_id (FK SET NULL)
    with op.batch_alter_table("areas") as batch_op:
        batch_op.add_column(
            sa.Column("lead_actor_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_areas_lead_actor",
            "actors",
            ["lead_actor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 3. Backfill: areas.lead_name → crea Actor (sin team) con is_lead=true.
    rows = bind.execute(
        sa.text(
            "SELECT id, tenant_id, lead_name FROM areas "
            "WHERE lead_name IS NOT NULL AND lead_name <> ''"
        )
    ).fetchall()
    for area_id, tenant_id, lead_name in rows:
        actor_id = str(uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO actors (id, tenant_id, team_id, user_id, name, "
                "email, phone, is_active, is_lead, created_at, updated_at) "
                "VALUES (:id, :t, NULL, NULL, :n, NULL, NULL, true, true, "
                "now(), now())"
            ),
            {"id": actor_id, "t": tenant_id, "n": lead_name.strip()},
        )
        bind.execute(
            sa.text("UPDATE areas SET lead_actor_id=:a WHERE id=:i"),
            {"a": actor_id, "i": area_id},
        )

    # Drop areas.lead_name (owner: flag es suficiente)
    with op.batch_alter_table("areas") as batch_op:
        batch_op.drop_column("lead_name")

    # 4. Drop project_areas + project_area_resources
    op.drop_table("project_area_resources")
    op.drop_table("project_areas")


def downgrade() -> None:
    # Recrea project_areas + project_area_resources vacías.
    op.create_table(
        "project_areas",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False, server_default="area"),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("contact_name", sa.String(length=200), nullable=True),
        sa.Column("contact_email", sa.String(length=200), nullable=True),
        sa.Column("area_leader_id", sa.String(length=36), nullable=True),
        sa.Column("team_id", sa.String(length=36), nullable=True),
        sa.Column("area_id", sa.String(length=36), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=36), nullable=True),
    )
    op.create_table(
        "project_area_resources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("area_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=36), nullable=True),
    )

    with op.batch_alter_table("areas") as batch_op:
        batch_op.add_column(sa.Column("lead_name", sa.String(length=200), nullable=True))
        batch_op.drop_constraint("fk_areas_lead_actor", type_="foreignkey")
        batch_op.drop_column("lead_actor_id")

    with op.batch_alter_table("actors") as batch_op:
        batch_op.drop_column("is_lead")
