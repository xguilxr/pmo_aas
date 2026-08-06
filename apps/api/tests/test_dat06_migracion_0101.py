"""DAT-06 / migración 0101 — la migración de datos, ejercida contra el motor real.

**Por qué existe este archivo.** La 0101 se escribió primero con `sa.text` y el
diccionario ya serializado, y se reescribió a tabla tipada por miedo a la forma
de BUG-039: SQLite acepta lo que Postgres rechaza.

Ese miedo, medido, resultó infundado — la versión con `sa.text` pasa contra
Postgres 16 + psycopg3, porque el parámetro viaja como `unknown` y el motor lo
convierte a `json`. Se comprobó mutando la migración con esta suite puesta: la
mutación **sobrevivió**. La tabla tipada se queda porque es la forma correcta,
no porque la otra reventara.

Lo que sí resultó cierto vino de preguntarse qué gate lo habría cazado. El job
`api-migrations-postgres` corre `alembic upgrade head` sobre una base **limpia**,
y ninguna migración del árbol inserta filas en `tenants`. O sea que el bucle de
`_renombrar` recorre **cero filas** y la línea que falla nunca se ejecuta: el job
que parecía cubrir esto habría dado verde con la versión rota.

Un `upgrade head` sobre base vacía prueba que el esquema se construye, no que una
migración de DATOS haga lo suyo. Son dos cosas distintas y solo una estaba
cubierta.

Así que aquí se siembra el caso que la base limpia no tiene y se corren
`upgrade()` y `downgrade()` de verdad. Contra SQLite siempre —para que el gate
exista sin depender de infraestructura— y contra Postgres cuando
`DATABASE_URL_POSTGRES` apunta a uno, que es como lo invoca el job del CI.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.models.tenant import Tenant

RAIZ_API = Path(__file__).resolve().parents[1]
MIGRACION = RAIZ_API / "alembic" / "versions" / "20260806_0101_yellow_max.py"

#: El inquilino que la migración tiene que tocar, y los dos que no.
#:
#: Los negativos no son relleno: una migración de datos que reescribe filas que
#: no le incumben ensucia el `updated_at` de medio producto, y eso solo se ve si
#: hay filas que no le incumben.
SEMILLA: list[tuple[str, dict]] = [
    (
        "con-la-llave-vieja",
        {"report_builder": {"task_load_thresholds": {"green_max": 3, "amber_max": 7}}},
    ),
    (
        "ya-migrado",
        {"report_builder": {"task_load_thresholds": {"green_max": 5, "yellow_max": 10}}},
    ),
    ("sin-el-bloque", {"otra_cosa": {"algo": 1}}),
]


def _cargar_migracion() -> ModuleType:
    """Importa el módulo por ruta: `alembic/versions/` no es un paquete."""
    spec = importlib.util.spec_from_file_location("migracion_0101", MIGRACION)
    assert spec and spec.loader, f"No pude cargar {MIGRACION}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _umbrales(fila: dict | None) -> dict:
    return (fila or {}).get("report_builder", {}).get("task_load_thresholds", {})


def _leer(conexion: sa.Connection) -> dict[str, dict]:
    tabla = Tenant.__table__
    filas = conexion.execute(sa.select(tabla.c.slug, tabla.c.settings)).fetchall()
    return dict(filas)


def _ejercitar(url: str) -> None:
    """Siembra, corre `upgrade()` y `downgrade()`, y comprueba las dos direcciones.

    Se usa la tabla real del modelo, no una inventada aquí: lo que se ejerce
    depende del **tipo de la columna**, así que una tabla de mentira con el tipo
    equivocado no probaría nada. Es la lección de la 0098, que escribía en una
    tabla inexistente y pasaba porque la verificación se fabricaba su propio
    sujeto.

    Se cuentan además los `UPDATE`. Sin eso, quitar la guarda `de not in
    umbrales` sobrevive a cualquier aserción sobre el contenido: reescribe las
    filas ajenas con **exactamente lo mismo**, así que nada en los datos lo
    delata. Lo comprobé mutándolo. La 0101 promete en su encabezado que no
    ensucia el `updated_at` de quien no le incumbe, y esa promesa solo se puede
    verificar contando sentencias.
    """
    modulo = _cargar_migracion()
    tabla = Tenant.__table__
    motor = create_engine(url)
    escrituras: list[str] = []

    @sa.event.listens_for(motor, "before_cursor_execute")
    def _anotar(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("UPDATE"):
            escrituras.append(statement)

    try:
        with motor.begin() as conexion:
            tabla.drop(conexion, checkfirst=True)
            tabla.create(conexion)
            conexion.execute(
                tabla.insert(),
                [
                    {"name": slug, "slug": slug, "settings": ajustes}
                    for slug, ajustes in SEMILLA
                ],
            )

        escrituras.clear()
        with motor.begin() as conexion:
            with Operations.context(MigrationContext.configure(conexion)):
                modulo.upgrade()

        assert len(escrituras) == 1, (
            f"La migración escribió {len(escrituras)} filas y solo una le incumbe. "
            f"Reescribir inquilinos que no tienen la llave vieja les mueve el "
            f"`updated_at` sin haber cambiado nada."
        )

        with motor.connect() as conexion:
            despues = _leer(conexion)

        assert _umbrales(despues["con-la-llave-vieja"]) == {"green_max": 3, "yellow_max": 7}, (
            "La migración no renombró la llave, o perdió el valor por el camino. "
            "Si esto falla contra Postgres y pasa contra SQLite, es BUG-039 otra vez."
        )
        assert _umbrales(despues["ya-migrado"]) == {"green_max": 5, "yellow_max": 10}, (
            "Tocó a un inquilino que ya estaba migrado."
        )
        assert despues["sin-el-bloque"] == {"otra_cosa": {"algo": 1}}, (
            "Tocó a un inquilino que no tiene el bloque `report_builder`."
        )

        with motor.begin() as conexion:
            with Operations.context(MigrationContext.configure(conexion)):
                modulo.downgrade()

        with motor.connect() as conexion:
            revertido = _leer(conexion)

        assert _umbrales(revertido["con-la-llave-vieja"]) == {"green_max": 3, "amber_max": 7}, (
            "La migración no es reversible: `downgrade` no devolvió la llave vieja. "
            "El job del CI corre `downgrade base` y esto lo destaparía tarde."
        )

        with motor.begin() as conexion:
            tabla.drop(conexion, checkfirst=True)
    finally:
        motor.dispose()


def test_la_migracion_renombra_y_revierte_en_sqlite(tmp_path: Path) -> None:
    """El gate siempre existe, sin depender de que haya un Postgres a mano."""
    _ejercitar(f"sqlite:///{tmp_path / 'migracion.db'}")


def test_la_migracion_renombra_y_revierte_en_postgres() -> None:
    """El motor de producción, que es el único que cuenta para una migración.

    Se salta si no hay Postgres, porque un test que no se puede correr en local
    se vuelve un test que nadie corre. El job `api-migrations-postgres` define
    `DATABASE_URL_POSTGRES`, así que allí **no** se salta — y si alguien quita
    esa variable del workflow, el caso de abajo lo delata.
    """
    url = os.environ.get("DATABASE_URL_POSTGRES")
    if not url:
        pytest.skip("Sin `DATABASE_URL_POSTGRES`; el job del CI sí lo define.")
    _ejercitar(url)


def test_el_job_de_postgres_ejerce_la_migracion_con_datos() -> None:
    """El trinquete sobre el propio workflow.

    Sin esta comprobación, el caso de arriba se salta en silencio para siempre:
    bastaría borrar la variable del workflow para que el CI siguiera en verde
    sin ejercer nunca la migración contra Postgres. Un skip silencioso se lee
    igual que un verde.
    """
    flujo = (RAIZ_API.parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    trabajo = flujo.split("api-migrations-postgres:", 1)
    assert len(trabajo) == 2, "Desapareció el job `api-migrations-postgres` del CI."
    # Hasta el siguiente job del mismo nivel de sangría.
    cuerpo = trabajo[1].split("\n  api-tests-heavy:", 1)[0]
    assert "DATABASE_URL_POSTGRES" in cuerpo, (
        "El job de migraciones dejó de definir `DATABASE_URL_POSTGRES`, así que "
        "la migración 0101 ya no se ejerce contra Postgres: el caso se salta y "
        "el job da verde igual. Es justo el hueco que este archivo vino a tapar."
    )
    assert "test_dat06_migracion_0101.py" in cuerpo, (
        "El job ya no corre esta suite. `alembic upgrade head` sobre una base "
        "limpia no ejerce migraciones de DATOS: no hay filas que migrar."
    )
