"""report_builder_templates + 4 seed plantillas (US-122, EP020).

Revision ID: 20260523_0071
Revises: 20260523_0070
Create Date: 2026-05-22 11:00:00

US-122: tabla `report_builder_templates` que persiste composiciones
declarativas de secciones del catálogo (US-120). Distinta de
`report_templates` (ENH-085, HTML tweakeado) y `ai_report_templates`
(per-project, wizard IA).

Seed (4 plantillas, `is_seed=True`, `tenant_id=NULL`):

- L3-AVANCE       modo A (by_section), nivel 3
  Secciones: S-01, S-02, S-03, S-04, S-06, S-08, S-19, S-09, S-16,
             S-17, S-18, S-14, S-11, S-13, S-12

- L3-SEGUIMIENTO  modo B (by_area), nivel 3
  Secciones: S-01, S-02, S-03, S-04, S-20, S-21, S-09, S-16, S-17,
             S-18, S-14, S-11, S-13, S-12

- L1-PORTAFOLIO   modo A, nivel 1
  Secciones: S-01, S-35, S-36, S-33, S-34

- L2-ORG          modo A, nivel 2
  Secciones: S-01, S-02, S-04, S-33, S-35, S-36, S-34
"""
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260523_0071"
down_revision: str | None = "20260523_0070"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (code, name, description, level, mode, section_codes)
SEED_TEMPLATES: list[tuple] = [
    (
        "L3-AVANCE",
        "Reporte de Avance (Nivel 3 — Proyecto)",
        "Plantilla seed v1.0 — composición por sección (Modo A).",
        3,
        "A",
        [
            "S-01", "S-02", "S-03", "S-04", "S-06", "S-08", "S-19",
            "S-09", "S-16", "S-17", "S-18",
            "S-14", "S-11", "S-13", "S-12",
        ],
    ),
    (
        "L3-SEGUIMIENTO",
        "Reporte de Seguimiento (Nivel 3 — Proyecto)",
        "Plantilla seed v1.0 — composición por área (Modo B).",
        3,
        "B",
        [
            "S-01", "S-02", "S-03", "S-04",
            "S-20", "S-21",
            "S-09", "S-16", "S-17", "S-18",
            "S-14", "S-11", "S-13", "S-12",
        ],
    ),
    (
        "L1-PORTAFOLIO",
        "Reporte de Portafolio (Nivel 1 — PMO)",
        "Plantilla seed v1.0 — agregado del portafolio interno del tenant.",
        1,
        "A",
        ["S-01", "S-35", "S-36", "S-33", "S-34"],
    ),
    (
        "L2-ORG",
        "Reporte por Organización / Programa (Nivel 2)",
        "Plantilla seed v1.0 — agregado por organización, cliente-facing.",
        2,
        "A",
        ["S-01", "S-02", "S-04", "S-33", "S-35", "S-36", "S-34"],
    ),
]


def upgrade() -> None:
    op.create_table(
        "report_builder_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column(
            "composition_mode",
            sa.String(length=1),
            nullable=False,
            server_default="A",
        ),
        sa.Column("section_codes", sa.JSON(), nullable=False),
        sa.Column("default_parameters", sa.JSON(), nullable=False),
        sa.Column(
            "is_seed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_report_builder_templates_tenant",
        "report_builder_templates",
        ["tenant_id"],
    )
    op.create_index(
        "ix_report_builder_templates_level",
        "report_builder_templates",
        ["level"],
    )
    # Uniqueness por (tenant_id, code). En Postgres NULLs no chocan
    # entre sí por default; los seeds (tenant_id NULL) coexisten con
    # custom templates de tenants.
    op.create_unique_constraint(
        "uq_report_builder_templates_tenant_code",
        "report_builder_templates",
        ["tenant_id", "code"],
    )

    now = datetime.now(UTC)
    rows = []
    for code, name, description, level, mode, section_codes in SEED_TEMPLATES:
        rows.append({
            "id": str(uuid.uuid4()),
            "tenant_id": None,
            "code": code,
            "name": name,
            "description": description,
            "level": level,
            "composition_mode": mode,
            "section_codes": json.dumps(section_codes),
            "default_parameters": json.dumps({}),
            "is_seed": True,
            "created_at": now,
            "updated_at": now,
        })

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
    op.bulk_insert(tbl, rows)


def downgrade() -> None:
    op.drop_constraint(
        "uq_report_builder_templates_tenant_code",
        "report_builder_templates",
        type_="unique",
    )
    op.drop_index(
        "ix_report_builder_templates_level",
        table_name="report_builder_templates",
    )
    op.drop_index(
        "ix_report_builder_templates_tenant",
        table_name="report_builder_templates",
    )
    op.drop_table("report_builder_templates")
