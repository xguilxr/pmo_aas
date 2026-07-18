"""BUG-091 — barrido de estados RAID legacy post-0089.

El remap de la migración 0089 (US-179) corrió una sola vez, pero el
flujo de minutas IA siguió creando riesgos con ``status='identified'``
(legacy): esos riesgos quedaban ineditables (el update valida el enum
de 4 estados y respondía 422). El fix de código elimina el origen;
esta migración re-aplica el remap (idempotente) para limpiar las filas
creadas después de 0089.

Data-only: no toca schema.
"""
from __future__ import annotations

from alembic import op

revision: str = "20260718_0095"
down_revision: str | None = "20260708_0094"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    # Remap lossy e idempotente — no hay vuelta atrás (igual que 0089).
    pass
