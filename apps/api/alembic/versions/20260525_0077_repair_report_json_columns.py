"""Repara columnas JSON double-encoded en report_sections / templates — BUG-063.

Revision ID: 20260525_0077
Revises: 20260524_0076
Create Date: 2026-05-25 16:00:00

Bug en producción: el endpoint `GET /report-sections` y
`GET /report-builder-templates` devolvían 500 porque las columnas JSON
(`data_shape`, `parameters_schema`, `section_codes`,
`default_parameters`) están almacenadas como **strings** en lugar de
objetos/arrays.

Causa: las migraciones de seed 0070/0071/0076 hicieron
``json.dumps(value)`` antes de `op.bulk_insert` en columnas `sa.JSON`.
SQLAlchemy serializa de nuevo al escribir → doble-encoding. En SQLite
pasó desapercibido en tests (que siembran vía ORM con dicts), pero en
PostgreSQL el valor queda como un JSON string escapado y Pydantic lo
rechaza al validar (`Input should be a valid dictionary`).

Esta migración lee cada fila vía una tabla tipada `sa.JSON` (lo que
deserializa una vez de forma consistente entre dialectos), detecta los
valores que quedaron como `str`, los parsea, y los re-escribe como
objeto/array nativo. Idempotente: las filas ya correctas no se tocan.
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260525_0077"
down_revision: str | None = "20260524_0076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (tabla, [columnas JSON a reparar])
_TARGETS: list[tuple[str, list[str]]] = [
    ("report_sections", ["data_shape", "parameters_schema"]),
    ("report_builder_templates", ["section_codes", "default_parameters"]),
]


def _repair(table_name: str, json_cols: list[str]) -> None:
    bind = op.get_bind()
    # Tabla tipada con columnas JSON: leer/escribir vía esta tabla hace
    # que SQLAlchemy deserialice/serialice de forma consistente en
    # SQLite y PostgreSQL.
    tbl = sa.table(
        table_name,
        sa.column("id", sa.String),
        *[sa.column(c, sa.JSON) for c in json_cols],
    )
    rows = bind.execute(sa.select(tbl)).mappings().all()
    for row in rows:
        updates: dict[str, object] = {}
        for col in json_cols:
            val = row[col]
            # Tras la deserialización del JSON type, una columna
            # double-encoded vuelve como `str`. Una columna sana vuelve
            # como dict/list — esas se saltan (idempotencia).
            if isinstance(val, str):
                try:
                    updates[col] = json.loads(val)
                except (ValueError, TypeError):
                    # No es JSON parseable; lo dejamos como está para no
                    # perder datos. Inspección manual si esto ocurre.
                    continue
        if updates:
            bind.execute(
                tbl.update().where(tbl.c.id == row["id"]).values(**updates)
            )


def upgrade() -> None:
    for table_name, json_cols in _TARGETS:
        # Solo intenta reparar si la tabla existe (defensivo en DBs
        # parciales).
        insp = sa.inspect(op.get_bind())
        if table_name in insp.get_table_names():
            _repair(table_name, json_cols)


def downgrade() -> None:
    # No-op: re-encodear a string sería re-introducir el bug.
    pass
