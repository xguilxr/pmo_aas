"""MCS DAT-09/DAT-12 — la instantánea puede guardar «no hay nada que promediar».

`metric_snapshots.avg_progress` era `NOT NULL DEFAULT 0`, así que el
recolector diario no tenía forma de distinguir «la cartera está al 0 %» de «no
hay proyectos activos». Escribía `0` en los dos casos.

La ficha del indicador, firmada por el owner el 2026-08-06, dice lo contrario:
«Sin proyectos → `null`, que se pinta «—». **Cero proyectos no es cero por
ciento**». El tablero en vivo se corrigió ese día; la instantánea no, porque
calculaba el mismo indicador por su cuenta — el defecto que DAT-09 describe.

Consecuencia visible: la gráfica de tendencia de los informes lee instantáneas
y **dibujaba una caída a cero** en carteras recién creadas.

Se hace nulable en vez de usar un centinela porque un centinela numérico
—`-1`— vuelve a ser un número que alguien promedia. `NULL` no se promedia por
accidente.

**No se convierten los ceros históricos.** Un `0` ya guardado puede significar
las dos cosas y no hay forma de saber cuál: reinterpretarlos hacia atrás sería
inventar. Desde esta migración, los nuevos distinguen.

Revision ID: 20260806_0103
Revises: 20260806_0102
Create Date: 2026-08-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0103"
down_revision: str | None = "20260806_0102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "metric_snapshots",
        "avg_progress",
        existing_type=sa.Numeric(5, 2),
        nullable=True,
        existing_server_default=None,
    )


def downgrade() -> None:
    # Volver a NOT NULL exige rellenar los nulos, y el único valor que la
    # columna admitía era `0` — el mismo que esta migración existe para dejar
    # de escribir. Es reversible sin perder filas, pero la reversión **sí
    # pierde la distinción**: los «no hay proyectos» vuelven a ser ceros
    # indistinguibles. Queda escrito porque el runbook de DES-02 §3.3 manda
    # leer esta función antes de bajar.
    op.execute("UPDATE metric_snapshots SET avg_progress = 0 WHERE avg_progress IS NULL")
    op.alter_column(
        "metric_snapshots",
        "avg_progress",
        existing_type=sa.Numeric(5, 2),
        nullable=False,
    )
