"""Builder seeds solo nivel proyecto: +Look-ahead, -PMO/Org — BUG-063.

Revision ID: 20260525_0078
Revises: 20260525_0077
Create Date: 2026-05-25 17:00:00

Owner: el Report Builder es exclusivamente nivel proyecto. Las
plantillas seed deben ser los 3 reportes principales de proyecto:
Avance, Seguimiento y Look-ahead. Las seeds de Portafolio (L1) y
Organización/Programa (L2) NO deben aparecer en el builder.

Esta migración:
- Borra los seeds `L1-PORTAFOLIO` y `L2-ORG` (is_seed=True).
- Inserta `L3-LOOKAHEAD` (modo A, nivel 3) si no existe — idempotente.

Los reportes L1/L2 siguen disponibles vía los tabs dedicados de
`/pmo/reports` (PMO / Organizaciones / Programas), que no dependen de
estos seeds del builder.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260525_0078"
down_revision: str | None = "20260525_0077"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LOOKAHEAD_CODE = "L3-LOOKAHEAD"
_LOOKAHEAD_SECTIONS = ["S-01", "S-02", "S-18", "S-09", "S-16", "S-14"]
_REMOVE_CODES = ("L1-PORTAFOLIO", "L2-ORG")


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Borra los seeds de portafolio / organización del builder.
    bind.execute(
        sa.text(
            "DELETE FROM report_builder_templates "
            "WHERE is_seed = true AND code IN ('L1-PORTAFOLIO', 'L2-ORG')"
        )
    )

    # 2) Inserta el seed Look-ahead si no existe (idempotente).
    existing = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM report_builder_templates WHERE code = :code"
        ),
        {"code": _LOOKAHEAD_CODE},
    ).scalar()
    if existing and int(existing) > 0:
        return

    now = datetime.now(UTC)
    tbl = sa.table(
        "report_builder_templates",
        sa.column("id", sa.String),
        sa.column("tenant_id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("level", sa.Integer),
        sa.column("composition_mode", sa.String),
        sa.column("section_codes", sa.JSON),
        sa.column("default_parameters", sa.JSON),
        sa.column("is_seed", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        tbl,
        [{
            "id": str(uuid.uuid4()),
            "tenant_id": None,
            "code": _LOOKAHEAD_CODE,
            "name": "Reporte Look-ahead (Nivel 3 — Proyecto)",
            "description": "Plantilla seed v1.0 — actividades hacia adelante (modo A).",
            "level": 3,
            "composition_mode": "A",
            "section_codes": _LOOKAHEAD_SECTIONS,
            "default_parameters": {},
            "is_seed": True,
            "created_at": now,
            "updated_at": now,
        }],
    )


def downgrade() -> None:
    # Reversa: borra el Look-ahead. No re-inserta los seeds L1/L2 (la
    # migración 0071 es su dueña original).
    op.get_bind().execute(
        sa.text(
            "DELETE FROM report_builder_templates "
            "WHERE is_seed = true AND code = :code"
        ),
        {"code": _LOOKAHEAD_CODE},
    )
