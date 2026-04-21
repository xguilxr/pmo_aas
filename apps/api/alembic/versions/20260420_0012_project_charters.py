"""project_charters — tabla del Charter (US-012, EP003)

Revision ID: 20260420_0012
Revises: 20260420_0011
Create Date: 2026-04-20 00:12:00

Charter estructurado con 4 secciones. Sección 4 (Gestión) se sincroniza
dinámicamente desde `projects` al consultar (ver DEC-008 y endpoint GET).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0012"
down_revision: Union[str, None] = "20260420_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_charters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("project_requests.id")),
        # Sección 1: Info General
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(5000)),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id")),
        sa.Column("business_unit_id", sa.String(36), sa.ForeignKey("business_units.id")),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id")),
        # Sección 2: Stakeholders
        sa.Column("sponsor", sa.String(200)),
        sa.Column("sponsor_email", sa.String(200)),
        sa.Column("business_leader", sa.String(200)),
        sa.Column("business_leader_email", sa.String(200)),
        sa.Column("tech_leader", sa.String(200)),
        sa.Column("tech_leader_email", sa.String(200)),
        sa.Column("pm_id", sa.String(36), sa.ForeignKey("users.id")),
        # Sección 3: Clasificación
        sa.Column("project_type", sa.String(50)),
        sa.Column("priority", sa.SmallInteger),
        sa.Column("objective", sa.String(5000)),
        sa.Column("restrictions", sa.String(5000)),
        sa.Column("risks_summary", sa.String(5000)),
        sa.Column("scope", sa.String(5000)),
        sa.Column("key_people", sa.String(5000)),
        sa.Column("benefits", sa.String(5000)),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("project_id", name="uq_charter_project"),
    )
    op.create_index("ix_charter_tenant", "project_charters", ["tenant_id"])
    op.create_index("ix_charter_project", "project_charters", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_charter_project", table_name="project_charters")
    op.drop_index("ix_charter_tenant", table_name="project_charters")
    op.drop_table("project_charters")
