"""ASVS 4.3.1 — equipos de confianza: el código no se pide en cada entrada.

Decisión del owner (2026-08-07), ADR-035 §Ventana. Pedir el código en **cada**
inicio de sesión es lo que hace que la gente desactive el segundo factor, o que
se lo salte por otra vía. Es lo que hacen Google, GitHub y Microsoft: se
comprueba una vez por equipo y se recuerda una ventana — aquí, treinta días.

**Sigue siendo dos factores dentro de la ventana**, y esa es la parte que
importa: la cookie es un secreto de 256 bits que solo tiene ese navegador —
«algo que tienes»— y la contraseña sigue haciendo falta. Lo que cambia es el
soporte del segundo factor, no su existencia.

Se guarda **solo el resumen** del token, como los códigos y como los tokens de
recuperación. `user_id` no es decoración: la comprobación exige que el resumen
**y** la cuenta coincidan, o la cookie de un equipo de confianza de una cuenta
saltaría el segundo factor de otra.

`revocado` en vez de borrar la fila: el cambio de contraseña revoca todos los
equipos —es la acción de «creo que me han entrado»— y conviene poder ver después
cuántos había y cuándo se usaron por última vez.

Revision ID: 20260807_0107
Revises: 20260807_0106
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_0107"
down_revision: str | None = "20260807_0106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispositivos_confiables",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("descripcion", sa.String(200), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ultimo_uso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_dispositivo_usuario_vivo", "dispositivos_confiables", ["user_id", "revocado"]
    )


def downgrade() -> None:
    # Reversible: al bajar, todo el mundo vuelve a pasar por el código en su
    # siguiente entrada. Molesto y seguro, que es el lado correcto por el que
    # equivocarse en una reversión.
    op.drop_index("idx_dispositivo_usuario_vivo", table_name="dispositivos_confiables")
    op.drop_table("dispositivos_confiables")
