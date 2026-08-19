"""US-199 / ADR-037 — se sueltan las columnas de BU/departamento, con sus lectores.

La 0108 creó lo nuevo y no tocó lo viejo a propósito: soltar una columna
mientras su lector sigue vivo deja la API devolviendo 500 entre dos commits.
Esta migración va con el commit que retira esos lectores —los sub-routers de
unidades de negocio y departamentos, y los campos BU/departamento de los
payloads de solicitudes y actas—, así que aquí sí se sueltan.

## Qué se va, qué llega y qué se queda

**Se va** (siete columnas, todas verificadas vacías antes de soltarlas):
`programs.department_id`, `projects.business_unit_id`, `projects.department_id`,
`project_requests.{business_unit_id, department_id}` y
`project_charters.{business_unit_id, department_id}`.

**Llega**: `project_requests.{portfolio_id, program_id}` y
`project_charters.{portfolio_id, program_id}`. La solicitud se clasifica antes
de que el proyecto exista, así que sin estas columnas el proyecto aprobado
nacería sin clasificación y alguien tendría que volver a ponerla a mano.

**Se queda**: las tablas `business_units` y `departments`. Un `drop table` es
irreversible y va en W8, cuando el contador de compat confirme que nadie las
lee (`reestructura-modelo-datos.md` §8). Lo que esta oleada quita son las
referencias, no las tablas.

## La verificación de vacío no es ceremonia

El owner confirmó que BU/departamentos nunca se usaron en producción, pero
«nunca se usaron» es una afirmación sobre **una** instalación. Esta migración
mira antes de soltar, y si encuentra filas **para**, con el conteo por columna
en el mensaje. No las borra ni las convierte: una migración que descarta datos
que no esperaba es peor que una que se niega a correr.

El residuo, si aparece, se vuelca a `audit_log` antes de parar —con la acción
`us199.residuo_bu_depto`— para que quede el rastro de qué había, y quien
despliegue decida. Si `audit_log` tampoco existiera (base a medio construir),
el volcado se salta y el mensaje de error sigue siendo el mismo.

## Por qué la clave ajena lleva una rama por motor

SQLite no sabe añadir una restricción a una tabla existente, y Alembic solo lo
emula recreándola. Es la misma rama que la 0108, por el mismo motivo: el esquema
de las pruebas nace de `create_all`, donde las cuatro columnas ya llegan con su
clave ajena puesta. Lo que la rama se salta en SQLite es lo que en SQLite ya
está.

## La bajada

Devuelve las siete columnas y quita las cuatro nuevas. **No devuelve los
valores**: los que había —ninguno, si la subida corrió— no se guardan en
ningún sitio intermedio. Es lo mismo que hace cualquier `downgrade` que retira
una columna, y la razón por la que la subida se niega a correr con datos:
después de soltarla, ya no hay a dónde volver.

Revision ID: 20260819_0109
Revises: 20260819_0108
Create Date: 2026-08-19
"""
from __future__ import annotations

import json
import logging

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0109"
down_revision: str | None = "20260819_0108"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.us199")

#: Las columnas que se sueltan, en el orden en que se sueltan. Tabla, columna y
#: el nombre de la restricción de clave ajena tal como la nombró la migración
#: que la creó — Postgres autogenera `<tabla>_<columna>_fkey`, y `drop_column`
#: se la lleva con la columna, así que no hace falta soltarla aparte.
A_SOLTAR: tuple[tuple[str, str], ...] = (
    ("programs", "department_id"),
    ("projects", "business_unit_id"),
    ("projects", "department_id"),
    ("project_requests", "business_unit_id"),
    ("project_requests", "department_id"),
    ("project_charters", "business_unit_id"),
    ("project_charters", "department_id"),
)

#: Las que llegan: la clasificación de la jerarquía nueva donde antes estaba la
#: vieja. Nullable, porque quien solicita no siempre sabe en qué portafolio cae.
A_CREAR: tuple[tuple[str, str, str], ...] = (
    ("project_requests", "portfolio_id", "portfolios"),
    ("project_requests", "program_id", "programs"),
    ("project_charters", "portfolio_id", "portfolios"),
    ("project_charters", "program_id", "programs"),
)


def _con_datos(bind: sa.Connection) -> dict[str, int]:
    """Cuántas filas tienen valor en cada columna a soltar. Vacío = todo listo."""
    resultado: dict[str, int] = {}
    for tabla, columna in A_SOLTAR:
        n = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {tabla} WHERE {columna} IS NOT NULL")
        ).scalar()
        if n:
            resultado[f"{tabla}.{columna}"] = int(n)
    return resultado


def _dejar_rastro(bind: sa.Connection, residuo: dict[str, int]) -> None:
    """Anota el residuo en `audit_log` antes de negarse a soltar nada.

    En una tabla que solo anexa (0097): el rastro de qué había cuando la
    migración se paró es lo que permite decidir después sin adivinar.
    """
    try:
        bind.execute(
            sa.text(
                "INSERT INTO audit_log (action, module, entity_type, details, occurred_at) "
                "VALUES (:a, :m, :e, :d, CURRENT_TIMESTAMP)"
            ),
            {
                "a": "us199.residuo_bu_depto",
                "m": "organizations",
                "e": "migration",
                "d": json.dumps(residuo),
            },
        )
    except Exception:
        # El rastro es un extra: si `audit_log` tiene otra forma o no existe, el
        # error de abajo sigue diciendo lo mismo. Tragarse esto es correcto —
        # fallar al *anotar* no debe cambiar el motivo por el que se falla.
        log.warning("US-199 — no pude anotar el residuo en audit_log: %s", residuo)


def upgrade() -> None:
    bind = op.get_bind()

    residuo = _con_datos(bind)
    if residuo:
        _dejar_rastro(bind, residuo)
        raise RuntimeError(
            "US-199 no suelta columnas con datos. Referencias BU/departamento "
            f"vivas: {residuo}. Reasigna esas filas a portafolio/programa "
            "(los datos quedaron anotados en audit_log como "
            "`us199.residuo_bu_depto`) y vuelve a intentarlo."
        )
    log.info("US-199 — las siete columnas BU/departamento están vacías, como se esperaba.")

    con_fk = bind.dialect.name != "sqlite"
    for tabla, columna, destino in A_CREAR:
        referencia = (sa.ForeignKey(f"{destino}.id"),) if con_fk else ()
        op.add_column(tabla, sa.Column(columna, sa.String(36), *referencia, nullable=True))
    op.create_index("ix_requests_portfolio_id", "project_requests", ["portfolio_id"])
    op.create_index("ix_requests_program_id", "project_requests", ["program_id"])

    for tabla, columna in A_SOLTAR:
        op.drop_column(tabla, columna)


def downgrade() -> None:
    bind = op.get_bind()
    con_fk = bind.dialect.name != "sqlite"

    op.drop_index("ix_requests_program_id", table_name="project_requests")
    op.drop_index("ix_requests_portfolio_id", table_name="project_requests")
    for tabla, columna, _ in A_CREAR:
        op.drop_column(tabla, columna)

    # De vuelta, en el orden inverso, apuntando a las tablas que siguen ahí.
    destino = {"business_unit_id": "business_units", "department_id": "departments"}
    for tabla, columna in reversed(A_SOLTAR):
        referencia = (sa.ForeignKey(f"{destino[columna]}.id"),) if con_fk else ()
        op.add_column(tabla, sa.Column(columna, sa.String(36), *referencia, nullable=True))
