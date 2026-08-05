"""D-3 / ADR-020 — `tasks.wbs` pasa a llamarse `tasks.wbs_code`.

La columna guarda el **código** de la EDT (`1.2.3`), no la estructura: esa vive
en `parent_id` y `outline_level`. El propio modelo ya lo delataba —
`models/task.py` documentaba «predecessors / successors como JSON array de
**wbs_code**» mientras la columna se llamaba `wbs`—, que es la clase de
discrepancia que el glosario existe para cerrar.

**`WBS` como palabra no se retira, y eso es lo que hace este renombrado
delicado.** La estructura de desglose se sigue llamando WBS en la interfaz, en
las cabeceras del Excel que descarga el usuario, en los códigos de diagnóstico
(`WBS_MISSING`, `WBS_DUPLICATED`) y en el elemento `<WBS>` de MS Project. Lo
único que cambia es el **identificador de la columna y del campo**: el sitio
donde guardamos el código. Confundir las dos cosas rompería todas las
importaciones existentes, porque el cliente sigue escribiendo «WBS» en su hoja.

**No toca los datos, solo el nombre.** `predecessors` y `successors` son
listas JSON de códigos, no claves foráneas: su contenido no cambia ni necesita
reescritura. Lo que sí hay que revisar —y va en el mismo commit— es todo código
que cruzara esas listas contra `task.wbs`.

`batch_alter_table` y no un `ALTER TABLE … RENAME COLUMN` crudo, por la misma
razón que 0099: en SQLite, que es lo que corre la suite, el renombrado de
columna se hace recreando la tabla y Alembic solo lo sabe hacer en modo batch.

Ejercitada contra el esquema real de `Base.metadata`, no contra una tabla hecha
a mano: es la lección que dejó 0098, que escribía en una tabla inexistente y
pasaba la verificación porque la verificación se fabricaba su propio sujeto.
"""
from __future__ import annotations

from alembic import op

revision: str = "20260805_0100"
down_revision: str | None = "20260805_0099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("wbs", new_column_name="wbs_code")


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("wbs_code", new_column_name="wbs")
