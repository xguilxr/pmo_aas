"""D-2 / ADR-019 — la fase `support` pasa a llamarse `hypercare`.

La revisión del glosario confirmó que la fase es legítima —acompañamiento
acotado tras la puesta en marcha, y una forma de cierre— y que el problema era
el nombre: `support` se lee como «mesa de ayuda», que es una función permanente,
no una fase de proyecto con principio y fin.

Toca dos tablas, y la segunda es fácil de olvidar: `projects.phase` y
`lessons.phase`, que comparte vocabulario (`LessonPhase` en el frontend).

**La tabla se llama `lessons`, no `lessons_learned`.** La primera versión de
esta migración usó el nombre del concepto de dominio —«lecciones aprendidas»— en
lugar del que tiene el esquema, y falló en `api-migrations-postgres` con
`relation "lessons_learned" does not exist`. No lo detectó antes porque el SQL
se había ejercitado contra tablas creadas a mano para la ocasión: reproducían la
columna, no el nombre. Ejercitar SQL de migración exige el esquema real.

**Hay una tercera columna `phase` que queda fuera a propósito:**
`project_participations.phase` es texto libre —«la fase en la que este recurso
consume capacidad»—, no el vocabulario controlado; ni la API ni la UI la
alimentan desde `ProjectPhase`. Renombrar ahí sería editar lo que escribió un
usuario.

**No hay `CHECK` ni enum que migrar.** Las dos columnas son `String(32)`, así
que esto es una migración de datos y nada más — es la razón por la que ADR-019
la clasificó de coste medio y no alto.

**La bajada es exacta solo porque `hypercare` no existía antes.** Ejercitada
contra Postgres 16: sube `support` → `hypercare` sin tocar el resto ni los
nulos, y baja al revés. Lo que la bajada **no** puede distinguir es una fila que
ya fuera `hypercare` de una que lo sea por esta migración — antes del 2026-08-05
ese valor no estaba en el vocabulario, así que el caso no se da con datos
reales, pero conviene saberlo antes de volver a subir tras una bajada parcial.

**La ventana de compatibilidad no vive aquí, vive en el esquema Pydantic**
(`schemas/project.py`), que acepta `support` a la entrada y lo normaliza. Eso
cubre al cliente que aún no se ha actualizado; esta migración cubre lo que ya
está guardado. Hacen falta las dos: una sin la otra deja mitad del producto
hablando el idioma viejo.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260805_0098"
down_revision: str | None = "20260805_0097"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Escritas una por una, sin bucle ni f-string: el nombre de tabla mal puesto
    # que rompió esto era invisible dentro de una interpolación.
    op.execute(sa.text("UPDATE projects SET phase = 'hypercare' WHERE phase = 'support'"))
    op.execute(sa.text("UPDATE lessons SET phase = 'hypercare' WHERE phase = 'support'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE projects SET phase = 'support' WHERE phase = 'hypercare'"))
    op.execute(sa.text("UPDATE lessons SET phase = 'support' WHERE phase = 'hypercare'"))
