"""US-199 — una bajada que suelta columnas tiene que reponer sus índices.

## El fallo que este archivo existe para que no vuelva

En Postgres, `DROP COLUMN` se lleva **en silencio** todo índice que dependa de la
columna. La 0109 suelta siete columnas de BU/departamento; la 0009 había creado
cinco índices sobre ellas. Tras la subida, esos cinco índices ya no existen.

La bajada de la 0109 devolvía las columnas pero no los índices, así que la cadena
seguía hacia atrás y el `downgrade` de la 0009 moría en
`DROP INDEX ix_req_dept_id` con «index does not exist». El job
`api-migrations-postgres` fue el único que lo vio, y lo vio tarde: la suite local
corre contra SQLite, donde `drop_column` se emula recreando la tabla, y **nadie**
corre la cadena completa `upgrade → downgrade base → upgrade` fuera de CI.

## Por qué se comprueba leyendo y no ejecutando

Reproducirlo de verdad exige Postgres y la cadena entera: unos minutos por
corrida y una dependencia que la suite no tiene. Lo que hace falta comprobar no
es el motor —el comportamiento de `DROP COLUMN` está documentado— sino que
**nosotros** nos acordemos de reponer. Eso se lee del propio código de las
migraciones, en milisegundos y sin base de datos.

Es un trinquete de acordarse, no de funcionar. La verificación de que funciona la
da el job de Postgres; esta la da antes de pushear.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

VERSIONES = Path(__file__).resolve().parents[1] / "alembic" / "versions"
MIGRACION_0009 = VERSIONES / "20260420_0009_business_units_departments.py"
MIGRACION_0109 = VERSIONES / "20260819_0109_retiro_bu_depto.py"


def _fuente(ruta: Path) -> str:
    assert ruta.exists(), f"no encuentro {ruta.name}"
    return ruta.read_text(encoding="utf-8")


def _cuerpo_de(fuente: str, funcion: str) -> str:
    """El código de una función de la migración, como texto.

    Se parsea con `ast` en vez de partir por líneas: un `def` dentro de una
    cadena o de un comentario haría que el corte por texto se llevara la mitad
    del archivo, y el test pasaría midiendo otra cosa.
    """
    arbol = ast.parse(fuente)
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == funcion:
            return ast.get_source_segment(fuente, nodo) or ""
    raise AssertionError(f"la migración no declara `{funcion}()`")


def _indices_creados(cuerpo: str) -> dict[str, tuple[str, str]]:
    """`{nombre: (tabla, columna)}` de cada `op.create_index` de una sola columna."""
    patron = re.compile(
        r"""op\.create_index\(\s*["'](?P<nombre>[^"']+)["']\s*,\s*"""
        r"""["'](?P<tabla>[^"']+)["']\s*,\s*\[\s*["'](?P<columna>[^"']+)["']\s*\]""",
        re.VERBOSE,
    )
    return {
        m.group("nombre"): (m.group("tabla"), m.group("columna"))
        for m in patron.finditer(cuerpo)
    }


def _columnas_soltadas(cuerpo: str) -> set[tuple[str, str]]:
    """Los `(tabla, columna)` que suelta un `upgrade`.

    La 0109 no escribe `op.drop_column("projects", "business_unit_id")` a mano:
    itera sobre `A_SOLTAR`. Así que la lista se lee de esa constante, que es
    donde vive de verdad, y no de las llamadas.
    """
    fuente = _fuente(MIGRACION_0109)
    arbol = ast.parse(fuente)
    for nodo in arbol.body:
        if not isinstance(nodo, ast.AnnAssign):
            continue
        if not (isinstance(nodo.target, ast.Name) and nodo.target.id == "A_SOLTAR"):
            continue
        pares = ast.literal_eval(nodo.value)  # type: ignore[arg-type]
        return set(pares)
    raise AssertionError("la 0109 ya no declara `A_SOLTAR`")


def test_la_0109_repone_todo_indice_que_su_drop_column_se_lleva() -> None:
    """El test que corresponde al fallo: por cada índice que la 0009 creó sobre
    una columna que la 0109 suelta, la bajada de la 0109 tiene que recrearlo con
    el **mismo nombre**, porque es el nombre por el que la 0009 lo va a borrar.
    """
    soltadas = _columnas_soltadas(_fuente(MIGRACION_0109))
    assert soltadas, "A_SOLTAR salió vacía; el test no está midiendo nada"

    creados_por_0009 = _indices_creados(_cuerpo_de(_fuente(MIGRACION_0009), "upgrade"))
    huerfanos = {
        nombre: destino
        for nombre, destino in creados_por_0009.items()
        if destino in soltadas
    }
    assert huerfanos, (
        "la 0009 ya no crea índices sobre las columnas que la 0109 suelta. Si es "
        "un cambio deliberado, este test sobra; si no, algo se movió."
    )

    repuestos = _indices_creados(_cuerpo_de(_fuente(MIGRACION_0109), "downgrade"))

    faltan = {n: d for n, d in huerfanos.items() if n not in repuestos}
    assert not faltan, (
        "La bajada de la 0109 devuelve las columnas pero no estos índices: "
        f"{faltan}. En Postgres, `DROP COLUMN` se los llevó en la subida, así que "
        "el `downgrade` de la 0009 va a morir en `DROP INDEX <nombre>` con «index "
        "does not exist» y el job `api-migrations-postgres` sale rojo. Reponelos "
        "como `op.create_index` literales al final del `downgrade`."
    )

    # Y sobre la columna correcta: reponer `ix_req_dept_id` apuntando a otra
    # columna dejaría el `DROP INDEX` contento y el índice mal.
    for nombre, destino in huerfanos.items():
        assert repuestos[nombre] == destino, (
            f"`{nombre}` se repone sobre {repuestos[nombre]} y la 0009 lo había "
            f"creado sobre {destino}."
        )


def test_la_0109_no_repone_indices_que_nadie_va_a_borrar() -> None:
    """El error simétrico, y el más fácil de cometer al arreglar el primero:
    reponer un índice que la 0009 nunca creó deja un `CREATE INDEX` sin su
    `DROP INDEX`, y la cadena vuelve a romperse — en el otro sentido, al subir
    otra vez después de bajar.

    Es el caso de las dos columnas de `project_charters`: la 0012 las creó dentro
    de su `create_table` y solo indexó `tenant_id` y `project_id`.
    """
    creados_por_0009 = set(_indices_creados(_cuerpo_de(_fuente(MIGRACION_0009), "upgrade")))
    repuestos = set(_indices_creados(_cuerpo_de(_fuente(MIGRACION_0109), "downgrade")))
    # Los que la 0109 crea en su *subida* son suyos y se borran en su bajada; los
    # que aparecen en la bajada tienen que venir todos de la 0009.
    inventados = repuestos - creados_por_0009
    assert not inventados, (
        f"La bajada de la 0109 crea índices que la 0009 no había creado: "
        f"{sorted(inventados)}. Nadie los va a borrar hacia atrás, y al volver a "
        "subir el `CREATE INDEX` de la 0009 choca contra un nombre ya tomado."
    )


def test_toda_columna_soltada_sigue_teniendo_su_tabla_destino() -> None:
    """Comprobación de coherencia de la propia bajada: recrea las columnas con
    una clave ajena a `business_units` o `departments`, y esas dos tablas siguen
    en el esquema hasta W8. Si alguien adelanta el `drop table`, este test lo
    señala antes que un despliegue.
    """
    fuente = _fuente(MIGRACION_0109)
    assert "business_units" in fuente and "departments" in fuente
    # El `drop table` de esas dos tablas es de W8 y no puede estar aquí.
    assert "drop_table" not in _cuerpo_de(fuente, "upgrade"), (
        "la 0109 no suelta tablas, solo referencias: el `drop table` de "
        "`business_units`/`departments` es de la oleada W8."
    )
