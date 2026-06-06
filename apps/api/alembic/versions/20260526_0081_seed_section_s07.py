"""seed report_section S-07 (curva-S) — US-161.

Revision ID: 20260526_0081
Revises: 20260526_0080
Create Date: 2026-05-26 14:00:00

US-161: la curva-S (planeado vs real acumulado) quedó habilitada al capturar
el avance planeado en `metric_snapshots.extras.avg_progress_plan` (US-151/161).
Idempotente: inserta S-07 solo si no existe.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260526_0081"
down_revision: str | None = "20260526_0080"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CODE = "S-07"


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT COUNT(*) FROM report_sections WHERE code = :c"), {"c": _CODE}
    ).scalar()
    if exists and int(exists) > 0:
        return
    now = datetime.now(UTC)
    tbl = sa.table(
        "report_sections",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("level", sa.Integer),
        sa.column("data_shape", sa.JSON),
        sa.column("parameters_schema", sa.JSON),
        sa.column("composition_mode_default", sa.String),
        sa.column("supports_ia", sa.Boolean),
        sa.column("enabled", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        tbl,
        [{
            "id": str(uuid.uuid4()),
            "code": _CODE,
            "name": "Curva-S (planeado vs real)",
            "description": "Avance planeado vs real acumulado desde metric_snapshots.",
            "category": "AVN",
            "level": 3,
            "data_shape": {"fields": ["points", "svg"]},
            "parameters_schema": {},
            "composition_mode_default": "A",
            "supports_ia": False,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
        }],
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM report_sections WHERE code = :c"), {"c": _CODE}
    )
