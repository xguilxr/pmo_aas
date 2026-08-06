"""DAT-06 / ADR-030 — `task_load_thresholds.amber_max` pasa a `yellow_max`.

Último resto de `amber` en el producto. El glosario lo veta desde D-1 y la
migración 0091 ya convirtió los **valores** de salud (`amber` → `yellow`); lo
que quedó fue esta **llave**, en el bloque `report_builder` de
`tenant.settings`, describiendo el mismo concepto con la palabra retirada.

No es cosmético: el umbral que colorea la carga de recursos usa el vocabulario
del semáforo, y tener el valor en `yellow` y su umbral en `amber_max` obliga a
traducir mentalmente cada vez que alguien lee el código de colorización — que
es exactamente cómo se cuelan los errores de asignación de color.

**Es un cambio de contrato sobre datos existentes**, no un renombrado de
columna. Vive dentro de una columna JSON de inquilinos reales, así que:

- esta migración reescribe la llave **en los datos que ya están**;
- el API sigue **aceptando** `amber_max` a la entrada durante una ventana de
  compatibilidad (`core/compatibilidad.py`), porque una pestaña abierta desde
  antes del despliegue seguiría enviándolo;
- la ventana se cierra con dato, no con corazonada: cada uso deja rastro en
  `compat.nombre_viejo` y a los dos meses se mira el contador.

Mismo molde que `wbs` → `wbs_code` (ADR-020, migración 0100), que es el
precedente que el owner aprobó para esta clase de cambio.

**Se opera sobre el JSON en Python y no con los operadores de Postgres**
(`jsonb_set`, `#>`): la suite corre sobre SQLite, y una migración que solo sabe
correr en un motor se descubre en producción. Se leen las filas, se reescribe
el diccionario y se actualiza.

Y la actualización va por una **tabla tipada de SQLAlchemy**, no por `sa.text`
con el diccionario ya serializado, para que cada dialecto adapte el valor a su
manera en vez de depender de que el motor acepte una cadena donde espera JSON.

**Corrección (2026-08-06).** Este párrafo afirmaba que la versión con `sa.text`
«habría fallado en Postgres» con «column settings is of type json but expression
is of type text». Se comprobó contra Postgres 16 + psycopg3 y **no falla**: el
parámetro viaja como `unknown` y Postgres lo convierte a `json` solito. La
mutación se corrió con la suite nueva puesta y **sobrevivió**. La tabla tipada
se queda porque es la forma correcta —no serializa a mano y aguanta que la
columna pase a `jsonb`—, pero no por el motivo que decía aquí. Se deja escrito
porque una justificación falsa en un encabezado es peor que ninguna: la
siguiente persona la cita.

Ejercitada contra el esquema real de `Base.metadata`, que es la lección que
dejó 0098 — aquella escribía en una tabla inexistente y pasaba la verificación
porque la verificación se fabricaba su propio sujeto.
"""
from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision: str = "20260806_0101"
down_revision: str | None = "20260805_0100"
branch_labels = None
depends_on = None

VIEJO = "amber_max"
NUEVO = "yellow_max"

#: Solo las dos columnas que hacen falta, declaradas aquí y no importadas del
#: modelo: una migración tiene que seguir corriendo cuando el modelo cambie.
TENANTS = sa.table(
    "tenants",
    sa.column("id", sa.String),
    sa.column("settings", sa.JSON),
)


def _renombrar(de: str, a: str) -> None:
    """Mueve la llave `de` → `a` dentro de `settings.report_builder`.

    Conserva el orden del resto del diccionario y no toca los inquilinos que no
    tienen el bloque: una migración de datos que reescribe filas que no le
    incumben es una migración que ensucia el `updated_at` de medio producto.
    """
    conexion = op.get_bind()
    filas = conexion.execute(sa.select(TENANTS.c.id, TENANTS.c.settings)).fetchall()

    for identificador, ajustes in filas:
        if not ajustes:
            continue
        # Postgres devuelve un dict ya deserializado; SQLite, según el camino,
        # puede devolver la cadena. Se aceptan los dos.
        datos = json.loads(ajustes) if isinstance(ajustes, str) else dict(ajustes)
        bloque = datos.get("report_builder")
        if not isinstance(bloque, dict):
            continue
        umbrales = bloque.get("task_load_thresholds")
        if not isinstance(umbrales, dict) or de not in umbrales:
            continue

        umbrales = {(a if k == de else k): v for k, v in umbrales.items()}
        bloque = {**bloque, "task_load_thresholds": umbrales}
        datos = {**datos, "report_builder": bloque}

        conexion.execute(
            TENANTS.update().where(TENANTS.c.id == identificador).values(settings=datos)
        )


def upgrade() -> None:
    _renombrar(VIEJO, NUEVO)


def downgrade() -> None:
    _renombrar(NUEVO, VIEJO)
