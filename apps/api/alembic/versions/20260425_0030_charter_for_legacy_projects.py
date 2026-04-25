"""charter_for_legacy_projects — US-083 (charter universal).

Revision ID: 20260425_0030
Revises: 20260425_0029
Create Date: 2026-04-25 12:00:00

Owner reportó (BUG #105): "charters viejos siguen solo con link de
abrir vacío... todo proyecto debe tener, nuevo o viejo, el charter,
editable aunque sea y con opcion de descarga (aunque esté vacío)".

Esta migración data crea una row vacía en `project_charters` para
cada `projects.id` que no tenga charter, copiando `project.name` →
`charter.project_name`. Idempotente: si la row ya existe (UQ por
project_id), no hace nada.

Después de esta migración:
- GET /projects/{id}/charter ya nunca devuelve 404 para projects
  válidos.
- Owner puede abrir el editor para todos los projects (legacy o
  nuevos).
- US-083 además agrega lazy auto-create en GET para defender contra
  projects creados después de la migración pero sin charter.
"""
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260425_0030"
down_revision: str | None = "20260425_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea charter vacío para todos los projects sin charter.

    Approach data-side (no DDL): SELECT projects sin charter, INSERT
    una fila por cada uno. Idempotente — se puede correr múltiples
    veces sin duplicar (gracias a `uq_charter_project`).

    Genera UUIDs Python-side para evitar dialect-specific SQL
    (gen_random_uuid en Postgres, randomblob en SQLite). Esto es
    seguro porque la migración corre en un único proceso al deploy.
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT p.id AS project_id,
                   p.tenant_id AS tenant_id,
                   p.name AS name,
                   p.organization_id AS organization_id
            FROM projects p
            WHERE p.deleted_at IS NULL
              AND NOT EXISTS (
                SELECT 1 FROM project_charters c WHERE c.project_id = p.id
              )
            """
        )
    ).all()
    if not rows:
        return
    insert_stmt = sa.text(
        """
        INSERT INTO project_charters (
            id, tenant_id, project_id, project_name,
            organization_id, created_at, updated_at
        )
        VALUES (
            :id, :tenant_id, :project_id, :project_name,
            :organization_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        """
    )
    for r in rows:
        bind.execute(
            insert_stmt,
            {
                "id": str(uuid4()),
                "tenant_id": r.tenant_id,
                "project_id": r.project_id,
                "project_name": r.name or "Proyecto sin nombre",
                "organization_id": r.organization_id,
            },
        )


def downgrade() -> None:
    # No hacemos downgrade — no podemos saber qué charters son los
    # auto-generados vs los editados. Si se necesita rollback, hacer
    # backup de la tabla antes y restaurar manualmente.
    pass
