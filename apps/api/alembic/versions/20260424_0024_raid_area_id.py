"""raid_area_id — US-064

Revision ID: 20260424_0024
Revises: 20260424_0023
Create Date: 2026-04-24 10:00:00

Agrega `area_id` a `risks` e `issues` como FK nullable hacia
`project_areas.id` (ON DELETE SET NULL) + índice compuesto
`(tenant_id, project_id, area_id)` para el ordenamiento de las
tablas RAID.

Items legacy se quedan con `area_id = NULL`; la obligatoriedad
vive a nivel de schema Pydantic (422 en POST), no en la DB, para
no romper los registros previos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260424_0024"
down_revision: Union[str, None] = "20260424_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risks",
        sa.Column(
            "area_id",
            sa.String(length=36),
            sa.ForeignKey("project_areas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_risks_tenant_project_area",
        "risks",
        ["tenant_id", "project_id", "area_id"],
    )
    op.add_column(
        "issues",
        sa.Column(
            "area_id",
            sa.String(length=36),
            sa.ForeignKey("project_areas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_issues_tenant_project_area",
        "issues",
        ["tenant_id", "project_id", "area_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_issues_tenant_project_area", table_name="issues")
    op.drop_column("issues", "area_id")
    op.drop_index("idx_risks_tenant_project_area", table_name="risks")
    op.drop_column("risks", "area_id")
