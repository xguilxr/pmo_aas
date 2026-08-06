"""IA-02 — `audit_log.actor_type` distingue una acción del modelo de una humana.

El requisito pide que toda acción ejecutada por un componente de IA quede
registrada **y sea distinguible de una acción humana**. Lo primero ya se
cumplía; lo segundo no, y el motivo es sutil: los campos que parecían servir no
servían.

- `module="ai"` significa «el módulo de IA», no «lo hizo la IA». `report.send`
  es una persona pulsando enviar y también lo lleva.
- El prefijo `ai.` en el nombre de la acción era inconsistente:
  `ai.minute.generate` lo tenía y `report.draft` —que redacta el modelo— no.
- `user_id`, en una acción de IA, guarda **quién la pidió**. Atribuirle la
  acción a esa persona es exactamente el error que el requisito evita.

**Las filas existentes se marcan `humano`, y es la lectura correcta**, no una
comodidad: hasta hoy el producto no tenía forma de que el modelo actuara sin
que una persona lo pidiera. Lo que no se puede reconstruir a posteriori es
cuáles de esas peticiones acabaron en texto generado — por eso la distinción se
guarda desde ahora en vez de inferirse hacia atrás.

**`audit_log` es de solo anexado** (migración 0097, AM-08): hay disparadores que
rechazan `UPDATE` y `DELETE`. Esta migración añade una columna, que es DDL y no
DML, así que no los toca. El `server_default` es lo que evita tener que
reescribir las filas de historia — cosa que los disparadores impedirían.

Reversible: `downgrade` quita la columna. Se pierde la distinción de lo
registrado mientras estuvo, que es inevitable y no destruye ningún otro dato.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260806_0102"
down_revision: str | None = "20260806_0101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column(
            "actor_type",
            sa.String(16),
            nullable=False,
            # `server_default` y no `default`: el segundo lo aplica SQLAlchemy
            # al insertar y dejaría las filas existentes en NULL, que con
            # `nullable=False` ni siquiera deja crear la columna.
            server_default="humano",
        ),
    )
    # Se consulta «qué hizo el modelo» acotando por inquilino y tiempo, igual
    # que los otros tres índices de la tabla. Sin él, esa pregunta recorre el
    # registro entero — y este registro solo crece, porque no se puede borrar.
    op.create_index(
        "idx_audit_actor_type_time", "audit_log", ["actor_type", "occurred_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_audit_actor_type_time", table_name="audit_log")
    op.drop_column("audit_log", "actor_type")
