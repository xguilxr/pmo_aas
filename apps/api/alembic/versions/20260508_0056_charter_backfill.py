"""project_charters backfill — garantizar 1 charter por proyecto (ENH-081).

Revision ID: 20260508_0056
Revises: 20260508_0055
Create Date: 2026-05-08 19:30:00

ENH-081 CA2: cada `project` sin charter row recibe un charter stub con
`name`, `description`, `start_date`, `end_date` (cuando estén disponibles)
heredados del proyecto, y los demás campos `NULL`. El PM completa los
faltantes desde la UI del charter.

Idempotente — se omite cualquier proyecto que ya tenga charter.
Solo data migration; no toca schema.
"""
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260508_0056"
down_revision: str | None = "20260508_0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT p.id, p.tenant_id, p.name, p.description, p.organization_id
            FROM projects p
            LEFT JOIN project_charters c ON c.project_id = p.id
            WHERE c.id IS NULL
              AND p.deleted_at IS NULL
            """
        )
    ).fetchall()

    if not rows:
        return

    now = datetime.now(UTC)
    insert_stmt = sa.text(
        """
        INSERT INTO project_charters (
            id, tenant_id, project_id,
            project_name, description, organization_id,
            created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :project_id,
            :project_name, :description, :organization_id,
            :created_at, :updated_at
        )
        """
    )
    for row in rows:
        bind.execute(
            insert_stmt,
            {
                "id": str(uuid4()),
                "tenant_id": row.tenant_id,
                "project_id": row.id,
                "project_name": row.name or "Proyecto sin nombre",
                "description": row.description,
                "organization_id": row.organization_id,
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    # No-op: no podemos saber qué filas vinieron del backfill sin un flag,
    # y borrar charters destruiría data legítima editada por usuarios. El
    # downgrade de schema lo cubre la migración 0030 (creación original).
    pass
