"""seed report_sections S-05 (tendencia) y S-15 (matriz riesgos) — US-158.

Revision ID: 20260526_0080
Revises: 20260526_0079
Create Date: 2026-05-26 13:00:00

US-158: habilita en el Report Builder las secciones derivadas de los
dashboards N1/N2. S-05 (tendencia) ahora es posible porque US-151 creó
`metric_snapshots`; S-15 (matriz PxI) se calcula en vivo desde riesgos.

Idempotente: inserta cada sección solo si su `code` no existe.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260526_0080"
down_revision: str | None = "20260526_0079"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (code, name, category, level, mode, supports_ia, description,
#  data_shape, parameters_schema)
_NEW_SECTIONS: list[tuple] = [
    (
        "S-05", "Tendencia", "AVN", 3, "A", False,
        "Serie histórica de una métrica del proyecto (metric_snapshots) con "
        "sparkline + tabla. Requiere snapshots capturados (US-151).",
        {"fields": ["metric", "points", "svg", "delta"]},
        {
            "metric": {
                "enum": [
                    "avg_progress", "open_risks", "severe_risks",
                    "open_issues", "tasks_done", "budget_actual",
                ],
                "default": "avg_progress",
            }
        },
    ),
    (
        "S-15", "Matriz de riesgos", "RAID", 3, "A", False,
        "Matriz 5x5 de riesgos abiertos por probabilidad x impacto.",
        {"fields": ["matrix", "total"]},
        {},
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
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
    for (
        code, name, category, level, mode, supports_ia,
        description, data_shape, parameters_schema,
    ) in _NEW_SECTIONS:
        exists = bind.execute(
            sa.text("SELECT COUNT(*) FROM report_sections WHERE code = :c"),
            {"c": code},
        ).scalar()
        if exists and int(exists) > 0:
            continue
        op.bulk_insert(
            tbl,
            [{
                "id": str(uuid.uuid4()),
                "code": code,
                "name": name,
                "description": description,
                "category": category,
                "level": level,
                "data_shape": data_shape,
                "parameters_schema": parameters_schema,
                "composition_mode_default": mode,
                "supports_ia": supports_ia,
                "enabled": True,
                "created_at": now,
                "updated_at": now,
            }],
        )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM report_sections WHERE code IN ('S-05', 'S-15')")
    )
