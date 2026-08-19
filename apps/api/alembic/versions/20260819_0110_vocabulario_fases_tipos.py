"""US-202 / ADR-038 — las fases y los tipos del proyecto pasan al español.

`planning → preparacion`, `execution → ejecucion`, `closed → cerrado`,
`cancelled → cancelado`. `hypercare` **no se toca**: ADR-019 lo renombró hace dos
semanas (migración 0098) y no tiene una traducción que no sea peor.

Y `projects.type` deja de ser texto libre: `transformation → transformacion`,
`operation → operacion`, `innovation → innovacion`. `bau` ya estaba bien.

## Dos tablas de fases, no una — la que se olvida

`projects.phase` y `lessons.phase` comparten vocabulario: la fase de una lección
es «en qué fase se aprendió esto». La 0098 aprendió esto a golpes —su primera
versión tocaba solo `projects`— y dejó escrito que la segunda tabla es la fácil
de olvidar. Se tocan las dos.

La que **queda fuera a propósito** es la tercera: `project_participations.phase`
es texto libre —«la fase en la que este recurso consume capacidad»—, no el
vocabulario controlado. Ni la API ni la interfaz la alimentan desde el catálogo.
Renombrar ahí sería editar lo que escribió un usuario.

## Los tipos que no están en el mapa

`projects.type` era `String(50)` sin validar, así que puede tener cualquier cosa:
`BAU`, `Business as usual`, `Mejora`. Los tres nombres del enum viejo se
traducen; **lo demás se deja como está y se anota en el registro**, con sus
valores y su conteo.

No se convierte a la fuerza y no se vacía. Adivinar que «Mejora» es `operacion`
es inventarse la clasificación de un proyecto de alguien; vaciarlo es perder el
único dato que había. La columna sigue siendo texto, así que esos valores se
**leen** igual; lo que ya no se puede es volver a escribirlos, porque el enum de
la API los rechaza. Quien despliegue ve el listado y decide.

## La bajada

Exacta para las fases y los tres tipos: son renombrados uno a uno y sin colisión
—ninguno de los nombres nuevos existía antes del 2026-08-19—. Lo único que no
puede distinguir es una fila que **ya** dijera `preparacion` de una que lo diga
por esta migración; antes de hoy ese valor no estaba en el vocabulario, así que
el caso no se da con datos reales, pero conviene saberlo antes de volver a subir
tras una bajada parcial. Es literalmente la nota que dejó la 0098.

Revision ID: 20260819_0110
Revises: 20260819_0109
Create Date: 2026-08-19
"""
from __future__ import annotations

import logging

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0110"
down_revision: str | None = "20260819_0109"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.us202")

#: Viejo → nuevo. Se escribe aquí y no se importa de `dominio/proyecto.py`: una
#: migración tiene que seguir corriendo igual el día que el módulo cambie o
#: desaparezca.
FASES: tuple[tuple[str, str], ...] = (
    ("planning", "preparacion"),
    ("execution", "ejecucion"),
    ("closed", "cerrado"),
    ("cancelled", "cancelado"),
)

#: Las dos tablas que comparten el vocabulario de fases.
TABLAS_CON_FASE: tuple[str, ...] = ("projects", "lessons")

TIPOS: tuple[tuple[str, str], ...] = (
    ("transformation", "transformacion"),
    ("operation", "operacion"),
    ("innovation", "innovacion"),
)


def _renombrar(bind: sa.Connection, tabla: str, columna: str, de: str, a: str) -> None:
    """Un `UPDATE` acotado al valor viejo.

    Con la guarda `= :de` y no un `CASE` sobre todas las filas: reescribir filas
    que no le incumben les mueve el `updated_at` sin haber cambiado nada, y eso
    ensucia el rastro de medio producto. Es la lección de la 0101.
    """
    bind.execute(
        sa.text(f"UPDATE {tabla} SET {columna} = :a WHERE {columna} = :de"),
        {"a": a, "de": de},
    )


def _tipos_sin_mapear(bind: sa.Connection, conocidos: set[str]) -> dict[str, int]:
    """Los valores de `projects.type` que esta migración no sabe traducir."""
    filas = bind.execute(
        sa.text(
            "SELECT type, COUNT(*) FROM projects WHERE type IS NOT NULL GROUP BY type"
        )
    ).all()
    return {str(valor): int(n) for valor, n in filas if str(valor) not in conocidos}


def upgrade() -> None:
    bind = op.get_bind()

    for tabla in TABLAS_CON_FASE:
        for viejo, nuevo in FASES:
            _renombrar(bind, tabla, "phase", viejo, nuevo)

    for viejo, nuevo in TIPOS:
        _renombrar(bind, "projects", "type", viejo, nuevo)

    # Lo que quede fuera del enum: se anota, no se toca.
    canonicos = {nuevo for _, nuevo in TIPOS} | {"bau"}
    residuo = _tipos_sin_mapear(bind, canonicos)
    if residuo:
        log.warning(
            "US-202 — `projects.type` con valores fuera del enum (se dejan como "
            "están; el enum de la API ya no los acepta a la escritura): %s",
            residuo,
        )
    else:
        log.info("US-202 — todos los tipos quedaron dentro del enum.")


def downgrade() -> None:
    bind = op.get_bind()

    for viejo, nuevo in TIPOS:
        _renombrar(bind, "projects", "type", nuevo, viejo)

    for tabla in TABLAS_CON_FASE:
        for viejo, nuevo in FASES:
            _renombrar(bind, tabla, "phase", nuevo, viejo)
