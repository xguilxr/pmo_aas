"""ASVS 8.3.3 — consentimiento del aviso de privacidad, con su versión.

El mapeo ASVS L1 dejó `8.3.3` como hueco: no había texto que dijera qué se
recoge ni forma de aceptarlo. Decisión del owner (2026-08-07): la pantalla va en
el **primer inicio de sesión** —no hay alta por autoservicio donde ponerla— y
vuelve a aparecer **si el aviso cambia**.

Dos columnas y no una. Con solo la fecha, «aceptó» responde *cuándo* y no *qué*:
el día que cambie lo que se recoge no habría manera de saber a quién hay que
volver a preguntarle sin cruzar fechas a mano contra el historial del documento.
Con la versión al lado, la pregunta se responde comparando contra
`aviso_privacidad.VERSION`.

**Nulables, y el nulo significa algo**: las cuentas que existen desde antes del
aviso no han aceptado nada. Rellenarlas con la fecha de la migración sería
fabricar un consentimiento que nadie dio — justo lo que el control quiere
impedir—. Al entrar verán la pantalla, que es lo correcto.

Revision ID: 20260807_0105
Revises: 20260807_0104
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_0105"
down_revision: str | None = "20260807_0104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("privacy_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("users", sa.Column("privacy_version", sa.String(16), nullable=True))


def downgrade() -> None:
    # Reversible, **con pérdida del consentimiento registrado**: al bajar se
    # borra quién aceptó y qué versión. Volver a subir deja a todo el mundo como
    # si nunca hubiera aceptado, así que todos verán la pantalla otra vez.
    #
    # Es molesto y es lo correcto: la alternativa —conservar el dato fuera de la
    # columna para «restaurarlo»— sería inventar un consentimiento a partir de
    # algo que el esquema ya no modela.
    op.drop_column("users", "privacy_version")
    op.drop_column("users", "privacy_accepted_at")
