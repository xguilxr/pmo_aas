"""users.role_type — US-059

Revision ID: 20260424_0026
Revises: 20260424_0025
Create Date: 2026-04-24 13:00:00

DEC-020 redefine la plataforma como "apoyo y visualización" sin
aprobaciones jerárquicas. Introduce 3 roles fijos: admin / user /
viewer. Esta migración agrega la columna `users.role_type` y asigna
valores a los usuarios existentes según sus roles legacy.

Mapeo (idempotente):
- Usuarios con rol cuyo JSON `permissions` tenga cualquier clave
  `admin.*` o el rol se llame `Administrador` → `admin`.
- Usuarios que sólo tienen roles "Viewer" (nombre o permisos ≤ read) →
  `viewer`.
- Resto (incluye usuarios sin roles) → `user`.

El sistema viejo de roles + user_roles NO se borra: se mantiene por
compat y para que un admin pueda añadir permisos extra puntuales.
`CurrentUser.has()` consulta primero `role_type` y sólo cae al JSON
legacy si es NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260424_0026"
down_revision: Union[str, None] = "20260424_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role_type", sa.String(length=16), nullable=True),
    )

    # Marca como admin a quienes tengan algún rol con permisos admin.*
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_type = 'admin'
            WHERE role_type IS NULL
              AND (
                is_superadmin = TRUE
                OR id IN (
                  SELECT ur.user_id
                  FROM user_roles ur
                  JOIN roles r ON r.id = ur.role_id
                  WHERE r.name IN ('Administrador', 'Admin', 'PMO Manager')
                     OR r.permissions::text LIKE '%"admin%'
                )
              )
            """
        )
    )

    # Viewer: usuarios cuyos únicos roles son "Viewer" o "Reportes"
    # (legacy sólo lectura de reportes).
    op.execute(
        sa.text(
            """
            UPDATE users u
            SET role_type = 'viewer'
            WHERE role_type IS NULL
              AND u.id IN (
                SELECT ur.user_id
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                GROUP BY ur.user_id
                HAVING bool_and(r.name IN ('Viewer', 'Reportes'))
              )
            """
        )
    )

    # Resto → user (incluye sin roles asignados).
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_type = 'user'
            WHERE role_type IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("users", "role_type")
