"""US-215 — la tarifa se congela en la participación, y declara su unidad.

`actors.fte_cost_rate` guarda la tarifa **de hoy**. Si en marzo alguien sube la
tarifa de un consultor, el costo del trabajo de enero cambiaría solo y el gasto
acumulado del proyecto se reescribiría hacia atrás. Es el mismo defecto que la
línea base resuelve para las fechas (US-212, migración 0113): la historia no se
mueve.

## Lo que añade

En `project_participations`, cuatro columnas que se congelan al asignar:

| Columna | Por qué |
|---|---|
| `cost_rate_snapshot` | La tarifa, copiada del catálogo y nunca recalculada |
| `cost_currency` | Un importe sin moneda es una unidad mentida (BUG-092) |
| `cost_rate_period` | `hora`/`dia`/`mes`. Sin la unidad de tiempo el número no significa nada |
| `cost_rate_captured_at` | Distingue la tarifa tomada al asignar de una recongelada después |

En `actors`, una: `cost_rate_period`, la unidad de `fte_cost_rate`.

## Por qué el periodo entra ahora y no era «obvio»

`fte_cost_rate` existe desde US-182 sin unidad de tiempo. Mientras nadie
calculaba nada con él, la ambigüedad no costaba: era un número que una persona
leía y sabía interpretar. Al derivar un costo se vuelve el dato más importante
del cálculo — multiplicar una tarifa mensual por los días de la asignación da un
número 21 veces mayor que el real, y **parece** correcto.

## Ninguna columna se rellena, y esa es la decisión

Sería fácil y sería un error en las dos:

- **El periodo con `mes` por defecto** inventaría la unidad de tarifas que
  alguien capturó pensando en horas. El costo saldría equivocado en un factor de
  21 o de 168, con toda la apariencia de un dato bueno.
- **La tarifa desde el catálogo** (el borrador de W4 lo proponía con la salvedad
  escrita) fecharía hoy una tarifa que quizá se pactó hace un año, y quedaría
  registrada como si fuera la del momento de asignar. Un `NULL` dice «no se
  congeló», que es la verdad y es accionable: la interfaz ofrece congelarla.

Un `NULL` en cualquiera de las cuatro significa «no hay costo calculable», no
cero (MCS DAT-12). El total de un proyecto viene acompañado de cuántas
asignaciones quedaron sin tarifa, para que no mienta por omisión.

## La bajada

Suelta las columnas y con ellas las tarifas congeladas. Es información nueva sin
sitio en el esquema anterior, así que la bajada es destructiva — lo esperable al
retirar un concepto. `actors.fte_cost_rate` no se toca: existía antes.

No hay índices que soltar aquí, así que el orden índice-antes-que-columna no
aplica; el trinquete general (`tests/test_dat_indices_antes_de_columnas.py`) lo
comprueba de todas formas.

Revision ID: 20260820_0114
Revises: 20260820_0113
Create Date: 2026-08-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0114"
down_revision: str | None = "20260820_0113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `batch_alter_table` porque SQLite no tiene ALTER en sitio y la suite corre
    # ahí; en Postgres se traduce a los ALTER normales.
    with op.batch_alter_table("project_participations") as lote:
        lote.add_column(sa.Column("cost_rate_snapshot", sa.Numeric(12, 2), nullable=True))
        lote.add_column(sa.Column("cost_currency", sa.String(length=3), nullable=True))
        lote.add_column(sa.Column("cost_rate_period", sa.String(length=8), nullable=True))
        lote.add_column(
            sa.Column(
                "cost_rate_captured_at", sa.DateTime(timezone=True), nullable=True
            )
        )

    with op.batch_alter_table("actors") as lote:
        lote.add_column(sa.Column("cost_rate_period", sa.String(length=8), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("actors") as lote:
        lote.drop_column("cost_rate_period")

    with op.batch_alter_table("project_participations") as lote:
        lote.drop_column("cost_rate_captured_at")
        lote.drop_column("cost_rate_period")
        lote.drop_column("cost_currency")
        lote.drop_column("cost_rate_snapshot")
