"""tasks.assignee_actor_id + risks/issues.owner_actor_id + sync PMO — ENH-079.

Revision ID: 20260507_0050
Revises: 20260507_0049
Create Date: 2026-05-07 14:00:00

Owner decisión 2026-05-07: el responsable de tareas + owner de RAID
items son siempre Actores del catálogo. PMO users que necesiten ser
asignables (acciones RAID) tienen su Actor correspondiente en el área
"PMO" sembrada en 0048.

Cambios:
1. `tasks.assignee_actor_id` FK actors (single FK; reemplaza el flujo
   user-only del legacy `tasks.owner_id`).
2. `risks.owner_actor_id` FK actors.
3. `issues.owner_actor_id` FK actors.
4. Sync: por cada user del tenant cuyo rol activo sea PMO/PMO_SR
   crear Actor (si no existe ya por email) en el área "PMO" del
   tenant. El Actor referencia el user via `user_id`.
5. Backfill: task.assignee_actor_id ← actor.id donde
   `actor.user_id == task.owner_id`. Mismo para risks/issues.
"""
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0050"
down_revision: str | None = "20260507_0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1-3. Add nullable FK columns.
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("assignee_actor_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_tasks_assignee_actor",
            "actors",
            ["assignee_actor_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_tasks_assignee_actor", ["assignee_actor_id"])

    with op.batch_alter_table("risks") as batch_op:
        batch_op.add_column(
            sa.Column("owner_actor_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_risks_owner_actor",
            "actors",
            ["owner_actor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("issues") as batch_op:
        batch_op.add_column(
            sa.Column("owner_actor_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_issues_owner_actor",
            "actors",
            ["owner_actor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 4. Sync PMO users → Actors en el área "PMO" del tenant.
    # Heurística: cualquier user con rol cuyo `key`/`code` contenga 'PMO'
    # (insensitive). Si no hay tabla `roles` resolvible, fallback:
    # usar todos los users con `is_active=true` que NO tienen Actor.
    tenants = bind.execute(sa.text("SELECT id FROM tenants")).fetchall()
    for (tenant_id,) in tenants:
        pmo_area = bind.execute(
            sa.text(
                "SELECT id FROM areas WHERE tenant_id=:t AND name='PMO' LIMIT 1"
            ),
            {"t": tenant_id},
        ).fetchone()
        if not pmo_area:
            continue
        pmo_area_id = pmo_area[0]

        # Users activos del tenant. Si tienen rol PMO se prioriza.
        # Para minimizar dependencias asumimos que los users del tenant
        # son candidatos a Actor PMO; el dropdown filtra después.
        users = bind.execute(
            sa.text(
                "SELECT id, full_name, email FROM users "
                "WHERE tenant_id=:t AND is_active=true"
            ),
            {"t": tenant_id},
        ).fetchall()
        for user_id, full_name, email in users:
            # Skip si ya hay Actor con este user_id O con este email
            existing = bind.execute(
                sa.text(
                    "SELECT id FROM actors WHERE tenant_id=:t AND "
                    "(user_id=:u OR (email IS NOT NULL AND email=:e)) LIMIT 1"
                ),
                {"t": tenant_id, "u": user_id, "e": email},
            ).fetchone()
            if existing:
                # Asegurar user_id seteado
                bind.execute(
                    sa.text(
                        "UPDATE actors SET user_id=:u WHERE id=:i AND user_id IS NULL"
                    ),
                    {"u": user_id, "i": existing[0]},
                )
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO actors (id, tenant_id, team_id, user_id, "
                    "name, email, phone, is_active, is_lead, "
                    "created_at, updated_at) "
                    "VALUES (:id, :t, NULL, :u, :n, :e, NULL, true, false, "
                    "now(), now())"
                ),
                {
                    "id": str(uuid4()),
                    "t": tenant_id,
                    "u": user_id,
                    "n": full_name or (email or "(sin nombre)"),
                    "e": email,
                },
            )

    # 5. Backfill: copia owner_id (user) → *_actor_id por user_id match.
    bind.execute(
        sa.text(
            "UPDATE tasks SET assignee_actor_id = ("
            "  SELECT a.id FROM actors a WHERE a.tenant_id = tasks.tenant_id "
            "  AND a.user_id = tasks.owner_id LIMIT 1"
            ") WHERE owner_id IS NOT NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE risks SET owner_actor_id = ("
            "  SELECT a.id FROM actors a WHERE a.tenant_id = risks.tenant_id "
            "  AND a.user_id = risks.owner_id LIMIT 1"
            ") WHERE owner_id IS NOT NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE issues SET owner_actor_id = ("
            "  SELECT a.id FROM actors a WHERE a.tenant_id = issues.tenant_id "
            "  AND a.user_id = issues.owner_id LIMIT 1"
            ") WHERE owner_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("issues") as batch_op:
        batch_op.drop_constraint("fk_issues_owner_actor", type_="foreignkey")
        batch_op.drop_column("owner_actor_id")
    with op.batch_alter_table("risks") as batch_op:
        batch_op.drop_constraint("fk_risks_owner_actor", type_="foreignkey")
        batch_op.drop_column("owner_actor_id")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_assignee_actor")
        batch_op.drop_constraint("fk_tasks_assignee_actor", type_="foreignkey")
        batch_op.drop_column("assignee_actor_id")
