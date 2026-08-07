"""ASVS 4.3.1 — segundo factor por correo para las interfaces de administración.

Decisión del owner (2026-08-07), ADR-035: el segundo factor es un código de seis
dígitos enviado por correo con Resend, que es la infraestructura que ya existe.
Sin dependencia nueva y sin enrolamiento previo, a cambio de ser un factor más
débil que TOTP — el residual queda escrito en el ADR y `2.7.1` figura ACEPTADO.

Tabla propia y no columnas en `users` porque un código es un hecho con vida
corta, no un atributo de la persona: nace, caduca a los diez minutos y se
consume. Ponerlo en `users` obligaría a limpiar a mano lo que aquí caduca solo.

Se guarda el **resumen** del código, no el código. Seis dígitos no resisten una
tabla precalculada, así que el resumen no protege de eso; protege de que un
volcado de la base entregue códigos utilizables tal cual, que es el caso
realista.

`desafio` ata el código a **una** petición de inicio de sesión concreta (ASVS
2.7.3). `intentos` acota la fuerza bruta: seis dígitos son un millón de
combinaciones y eso se prueba entero en minutos.

Revision ID: 20260807_0106
Revises: 20260807_0105
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_0106"
down_revision: str | None = "20260807_0105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_otp_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("desafio", sa.String(64), nullable=False, unique=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_otp_desafio_vivo", "admin_otp_codes", ["desafio", "used_at"])


def downgrade() -> None:
    # Reversible sin pérdida de nada que importe: lo único que se tira son
    # códigos con diez minutos de vida. Los inicios de sesión a medias fallan y
    # se rehacen, que es lo que pasaría igual si caducaran.
    op.drop_index("idx_otp_desafio_vivo", table_name="admin_otp_codes")
    op.drop_table("admin_otp_codes")
