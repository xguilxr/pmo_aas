"""D-8 / ADR-021 — `actors.portfolio_function` pasa a `actors.discipline`.

El glosario veta «portafolio» para un área (**brecha B-6**): un portafolio es un
conjunto de proyectos y programas agrupados para gestión estratégica, y esa
entidad no existe en el producto. Lo que la columna guarda es el rol normalizado
para saturación por capacidad —`pm`, `pmo`, `arquitectura`, `datos`,
`seguridad`, `testing`…—, o sea una **disciplina**.

`discipline` y no `capacity_function` ni `role_type` porque en este producto
«función» y «rol» ya significan otras cosas: `by_function` era una agregación de
capacidad y «rol» es el de permisos (`roles`, `user_roles`). Confundir el
segundo en un modelo multiinquilino sale caro.

**Renombrado de columna, no de datos.** Los valores no cambian; `String(24)` sin
`CHECK`, así que no hay tipo que migrar. Ejercitado contra Postgres 16: sube,
baja y los datos quedan intactos en los dos sentidos.

**La ventana de compatibilidad vive en el esquema Pydantic y en el endpoint**
(`schemas/area.py`, `endpoints/areas.py`), que siguen aceptando
`portfolio_function` a la entrada porque es un **parámetro público de consulta**.
La salida es siempre `discipline`.

`batch_alter_table` y no un `ALTER TABLE … RENAME COLUMN` crudo: en SQLite
—donde corre la suite— el renombrado se hace recreando la tabla, y Alembic sabe
hacerlo; en PostgreSQL emite el `ALTER` directo.
"""
from __future__ import annotations

from alembic import op

revision: str = "20260805_0099"
down_revision: str | None = "20260805_0098"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("actors") as batch:
        batch.alter_column("portfolio_function", new_column_name="discipline")


def downgrade() -> None:
    with op.batch_alter_table("actors") as batch:
        batch.alter_column("discipline", new_column_name="portfolio_function")
