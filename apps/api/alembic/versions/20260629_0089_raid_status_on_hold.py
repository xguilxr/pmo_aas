"""US-179 — RAID estados a 4 + campos de detención (on_hold).

Simplifica los estados de Riesgos e Incidencias (acciones/incidentes/
decisiones) a 4 canónicos compartidos: ``open | in_progress | on_hold |
resolved``. Agrega los campos de detención usados cuando el estado es
``on_hold``: razón, dependencia (área + responsable) y desde cuándo está
detenido.

Mapeo de datos legacy:
- Risks:   identified→open · analyzing/mitigating→in_progress ·
           materialized/closed→resolved.
- Issues:  closed→resolved (open/in_progress ya válidos).

(Los ChangeRequests mantienen su flujo de aprobación propio y no se tocan.)

Revision ID: 20260629_0089
Revises: 20260628_0088
Create Date: 2026-06-29 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_0089"
down_revision: str | None = "20260628_0088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_on_hold_columns(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("on_hold_reason", sa.String(length=2000), nullable=True))
        batch.add_column(sa.Column("on_hold_area_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("on_hold_actor_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("on_hold_since", sa.Date(), nullable=True))


def upgrade() -> None:
    _add_on_hold_columns("risks")
    _add_on_hold_columns("issues")

    # Data migration: remap a los 4 estados canónicos.
    op.execute("UPDATE risks SET status = 'open' WHERE status = 'identified'")
    op.execute(
        "UPDATE risks SET status = 'in_progress' "
        "WHERE status IN ('analyzing', 'mitigating')"
    )
    op.execute(
        "UPDATE risks SET status = 'resolved' "
        "WHERE status IN ('materialized', 'closed')"
    )
    op.execute("UPDATE issues SET status = 'resolved' WHERE status = 'closed'")


def downgrade() -> None:
    # No revertimos el remap de estados (es lossy: materialized/closed se
    # fundieron en resolved). Solo quitamos las columnas de detención.
    for table in ("risks", "issues"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("on_hold_since")
            batch.drop_column("on_hold_actor_id")
            batch.drop_column("on_hold_area_id")
            batch.drop_column("on_hold_reason")
