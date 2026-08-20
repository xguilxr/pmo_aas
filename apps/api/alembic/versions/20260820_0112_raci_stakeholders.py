"""US-217 — RACI y stakeholders clave sobre las participaciones del proyecto.

El artboard «Proyecto — Recursos» pide «RACI / stakeholders clave». Son dos
campos de la participación que ya existe, no una tabla nueva: una participación
dice «esta persona está en este proyecto con este rol y este % de FTE», y esto
dice **de qué tipo** es su responsabilidad y si es un interlocutor clave.

## Por qué dos columnas y no una tabla

Una tabla aparte obligaría a mantener dos listas de las mismas personas y a
decidir qué hacer cuando alguien está en una y no en la otra. Con las columnas
en la participación, el RACI no puede referirse a nadie que no esté en el
proyecto — que es el error que una tabla suelta permite.

## Las dos columnas

- `raci` — una de `A`/`R`/`C`/`I`, o nulo. **Nulo es un estado válido**: la
  mayoría de las participaciones no tienen papel RACI asignado, y forzar uno
  obligaría a inventarlo para poder guardar la participación.
- `is_key_stakeholder` — el interlocutor con el que hay que hablar. Es
  independiente del RACI: alguien informado puede ser clave (el director que
  quiere el correo) y alguien que ejecuta puede no serlo.

La unicidad de la `A` **no** se declara como restricción de base de datos. Un
índice único parcial sobre `(project_id, raci) WHERE raci = 'A'` funcionaría en
Postgres y no en SQLite, y el repositorio corre en los dos —los tests van sobre
SQLite—. Una regla que solo se cumple en producción es peor que una que se
cumple en la frontera: la validación vive en la API y hay un test que la ejerce.

Revision ID: 20260820_0112
Revises: 20260819_0111
Create Date: 2026-08-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0112"
down_revision: str | None = "20260819_0111"
branch_labels = None
depends_on = None

TABLA = "project_participations"


def upgrade() -> None:
    # `batch_alter_table` y no `add_column` directo: SQLite no sabe alterar una
    # tabla en sitio y Alembic la reconstruye. En Postgres es un `ALTER` normal.
    with op.batch_alter_table(TABLA) as lote:
        lote.add_column(sa.Column("raci", sa.String(1), nullable=True))
        lote.add_column(
            sa.Column(
                "is_key_stakeholder",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    # El índice sirve a la consulta del panel: «dame el RACI de este proyecto».
    # Sin él, con doscientas participaciones por inquilino, es un barrido.
    op.create_index(
        "ix_participations_project_raci", TABLA, ["project_id", "raci"]
    )


def downgrade() -> None:
    # Se quita el índice antes que las columnas: en Postgres, soltar una columna
    # arrastra los índices que la usan y el `drop_index` posterior fallaría con
    # «no existe». Es el fallo que la migración 0109 dejó en CI.
    op.drop_index("ix_participations_project_raci", table_name=TABLA)
    with op.batch_alter_table(TABLA) as lote:
        lote.drop_column("is_key_stakeholder")
        lote.drop_column("raci")
