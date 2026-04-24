"""business_units + departments + FKs en programs/projects/project_requests

Revision ID: 20260420_0009
Revises: 20260101_0008
Create Date: 2026-04-20 00:00:00

US-002 (EP002): Jerarquía Org → BU → Departamento → Programa → Proyecto.

Notas:
- IDs como String(36) para portabilidad PG/MySQL (ver EP012 / DEC-002).
- RLS PG no se aplica a nivel SQL: el aislamiento por tenant se enforca en el
  ORM filtrando por tenant_id (ver TC-MT-001). Coherente con tablas existentes.
- BU y Departamento son opcionales en programs/projects para no romper datos
  actuales (organization_id sigue siendo NOT NULL).
- En project_requests se mantienen las columnas text legacy (`business_unit`,
  `department`) hasta migración de datos en US futura.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260420_0009"
down_revision: str | None = "20260101_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "organization_id", "name", name="uq_bu_tenant_org_name"
        ),
    )
    op.create_index("ix_bu_tenant_id", "business_units", ["tenant_id"])
    op.create_index("ix_bu_org_id", "business_units", ["organization_id"])

    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            sa.String(36),
            sa.ForeignKey("business_units.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "business_unit_id", "name", name="uq_dept_tenant_bu_name"
        ),
    )
    op.create_index("ix_dept_tenant_id", "departments", ["tenant_id"])
    op.create_index("ix_dept_bu_id", "departments", ["business_unit_id"])

    with op.batch_alter_table("programs") as batch:
        batch.add_column(
            sa.Column(
                "department_id",
                sa.String(36),
                sa.ForeignKey("departments.id"),
                nullable=True,
            )
        )
    op.create_index("ix_programs_dept_id", "programs", ["department_id"])

    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column(
                "business_unit_id",
                sa.String(36),
                sa.ForeignKey("business_units.id"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "department_id",
                sa.String(36),
                sa.ForeignKey("departments.id"),
                nullable=True,
            )
        )
    op.create_index("ix_projects_bu_id", "projects", ["business_unit_id"])
    op.create_index("ix_projects_dept_id", "projects", ["department_id"])

    with op.batch_alter_table("project_requests") as batch:
        batch.add_column(
            sa.Column(
                "business_unit_id",
                sa.String(36),
                sa.ForeignKey("business_units.id"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "department_id",
                sa.String(36),
                sa.ForeignKey("departments.id"),
                nullable=True,
            )
        )
    op.create_index("ix_req_bu_id", "project_requests", ["business_unit_id"])
    op.create_index("ix_req_dept_id", "project_requests", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_req_dept_id", table_name="project_requests")
    op.drop_index("ix_req_bu_id", table_name="project_requests")
    with op.batch_alter_table("project_requests") as batch:
        batch.drop_column("department_id")
        batch.drop_column("business_unit_id")

    op.drop_index("ix_projects_dept_id", table_name="projects")
    op.drop_index("ix_projects_bu_id", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("department_id")
        batch.drop_column("business_unit_id")

    op.drop_index("ix_programs_dept_id", table_name="programs")
    with op.batch_alter_table("programs") as batch:
        batch.drop_column("department_id")

    op.drop_index("ix_dept_bu_id", table_name="departments")
    op.drop_index("ix_dept_tenant_id", table_name="departments")
    op.drop_table("departments")

    op.drop_index("ix_bu_org_id", table_name="business_units")
    op.drop_index("ix_bu_tenant_id", table_name="business_units")
    op.drop_table("business_units")
