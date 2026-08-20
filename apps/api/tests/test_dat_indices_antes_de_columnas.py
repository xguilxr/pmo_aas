"""En una bajada, el índice de una tabla se quita antes que sus columnas.

## El fallo que este archivo existe para que no vuelva

Es el hermano del de US-199, por el otro lado. En Postgres, soltar una columna se
lleva **en silencio** todo índice que dependa de ella. Si la bajada de una
migración suelta primero la columna y después el índice de esa **misma tabla**,
el segundo paso muere con «index does not exist»: el índice ya se fue.

US-199 lo vio al revés —una bajada que devolvía columnas sin reponer sus
índices, y la migración anterior fallaba al soltarlos—. La regla general es la
misma en las dos direcciones: índice y columna de una tabla tienen un orden, y
el único que funciona en los dos motores es índice primero.

## Por qué se compara por tabla

Una primera versión de este trinquete miraba el orden plano de las llamadas y
señalaba siete migraciones correctas. En la 0108, el `drop_index` de `programs`
va después del `drop_column` de `projects`: tablas distintas, ninguna
interacción. En la 0024, cada par índice-columna está bien ordenado y solo se
solapaban al aplanarlos.

Un trinquete que señala código correcto se desactiva, y entonces no protege
nada. La comparación es por tabla porque la dependencia es por tabla.

Queda una imprecisión conocida y deliberada: `drop_index` solo da el nombre del
índice, no sus columnas, así que no se puede saber si el índice cubre la columna
que se suelta. Se exige el orden en toda la tabla, que es más estricto de lo
necesario y no cuesta nada — ordenar dos líneas es gratis y equivocarse cuesta un
job rojo.

## Por qué se compara por bloque de ejecución

La 0054 fue el segundo falso positivo: su bajada tiene una rama para Postgres y
otra para SQLite, y el trinquete comparaba el índice de una con la columna de la
otra. Nunca corren juntas, así que no hay orden que comparar. Las ramas de un
`if` son bloques distintos; el cuerpo de un `with batch_alter_table` no lo es
—sus llamadas se ejecutan en secuencia con lo que las rodea—.

## Por qué se comprueba leyendo y no ejecutando

Reproducirlo exige Postgres y la cadena completa de migraciones: minutos por
corrida y una dependencia que la suite local no tiene —va sobre SQLite, donde
soltar una columna se emula recreando la tabla y el orden no importa—. Lo que
hace falta comprobar no es el motor, cuyo comportamiento está documentado, sino
que **nosotros** nos acordemos del orden.

Es un trinquete de acordarse, no de funcionar. La verificación de que funciona la
da el job `api-migrations-postgres`; esta la da antes de pushear.

## Alcance

Cubre **todas** las revisiones, no una lista escrita a mano: una migración nueva
que se olvide del orden falla aquí sin que nadie la añada. Es la diferencia con
el trinquete de US-199, que vigila dos archivos concretos por su historia.
"""
from __future__ import annotations

import ast
from pathlib import Path

VERSIONES = Path(__file__).resolve().parents[1] / "alembic" / "versions"

#: El nombre de la función de bajada de una revisión de Alembic.
BAJADA = "down" + "grade"

QUITA_INDICE = "drop_index"
QUITA_COLUMNA = "drop_column"
LOTE = "batch_alter_table"

#: `(línea, operación, tabla)`.
Operacion = tuple[int, str, str]


def _revisiones() -> list[Path]:
    archivos = sorted(p for p in VERSIONES.glob("*.py") if p.name != "__init__.py")
    assert archivos, f"no encontré revisiones en {VERSIONES}"
    return archivos


def _bajada(fuente: str) -> ast.FunctionDef | None:
    for nodo in ast.parse(fuente).body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name == BAJADA:
            return nodo
    return None


def _texto(nodo: ast.expr | None) -> str | None:
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else None


def _tabla_del_lote(nodo: ast.With) -> str | None:
    """La tabla de un `with op.batch_alter_table("x") as lote:`."""
    for item in nodo.items:
        llamada = item.context_expr
        if isinstance(llamada, ast.Call) and getattr(llamada.func, "attr", None) == LOTE:
            if llamada.args:
                return _texto(llamada.args[0])
            for kw in llamada.keywords:
                if kw.arg == "table_name":
                    return _texto(kw.value)
    return None


def _operacion(nodo: ast.Call, tabla_del_lote: str | None) -> Operacion | None:
    """La operación que representa una llamada, o `None` si no viene al caso."""
    operacion = getattr(nodo.func, "attr", None)
    if operacion not in (QUITA_INDICE, QUITA_COLUMNA):
        return None
    tabla: str | None = None
    if operacion == QUITA_INDICE:
        # `op.drop_index(nombre, table_name="x")` o el segundo posicional.
        for kw in nodo.keywords:
            if kw.arg == "table_name":
                tabla = _texto(kw.value)
        if tabla is None and len(nodo.args) >= 2:
            tabla = _texto(nodo.args[1])
    elif len(nodo.args) >= 2:
        # `op.drop_column("tabla", "col")`; en lote, el argumento es la columna.
        tabla = _texto(nodo.args[0])
    if tabla is None:
        tabla = tabla_del_lote
    if tabla is None:
        # Sin tabla no se puede comparar. Ocurre con un nombre calculado, y
        # señalarlo sería ruido: se deja fuera a propósito.
        return None
    return (nodo.lineno, operacion, tabla)


def _bloques(sentencias: list[ast.stmt], tabla_del_lote: str | None = None) -> list[list[Operacion]]:
    """Las operaciones agrupadas por **bloque de ejecución secuencial**.

    El primer bloque del resultado es el de `sentencias`; detrás van los de las
    ramas que contenga. Un `with` aporta sus llamadas al bloque de quien lo
    contiene —corren en secuencia— y arrastra la tabla del lote hacia dentro;
    un `if` o un `try` abren un bloque por rama, porque solo una corre.
    """
    propio: list[Operacion] = []
    aparte: list[list[Operacion]] = []

    for sentencia in sentencias:
        if isinstance(sentencia, ast.With):
            dentro = _bloques(sentencia.body, _tabla_del_lote(sentencia) or tabla_del_lote)
            propio.extend(dentro[0])
            aparte.extend(dentro[1:])
        elif isinstance(sentencia, (ast.For, ast.While)):
            # El cuerpo corre en secuencia con lo de alrededor; el `else` de un
            # bucle también, porque se ejecuta al terminarlo.
            for rama in (sentencia.body, sentencia.orelse):
                dentro = _bloques(rama, tabla_del_lote)
                propio.extend(dentro[0])
                aparte.extend(dentro[1:])
        elif isinstance(sentencia, ast.If):
            for rama in (sentencia.body, sentencia.orelse):
                aparte.extend(_bloques(rama, tabla_del_lote))
        elif isinstance(sentencia, ast.Try):
            for rama in (sentencia.body, sentencia.orelse, sentencia.finalbody):
                aparte.extend(_bloques(rama, tabla_del_lote))
            for manejador in sentencia.handlers:
                aparte.extend(_bloques(manejador.body, tabla_del_lote))
        else:
            for nodo in ast.walk(sentencia):
                if isinstance(nodo, ast.Call):
                    operacion = _operacion(nodo, tabla_del_lote)
                    if operacion is not None:
                        propio.append(operacion)

    return [sorted(propio), *aparte]


def test_el_indice_se_quita_antes_que_la_columna_de_su_tabla() -> None:
    """Por tabla y por bloque: el último `drop_index` va antes del primer `drop_column`."""
    culpables: list[str] = []
    revisadas = 0
    con_las_dos = 0

    for archivo in _revisiones():
        bajada = _bajada(archivo.read_text(encoding="utf-8"))
        if bajada is None:
            continue
        revisadas += 1
        for bloque in _bloques(bajada.body):
            for tabla in sorted({tabla for _, _, tabla in bloque}):
                indices = [ln for ln, op, t in bloque if t == tabla and op == QUITA_INDICE]
                columnas = [ln for ln, op, t in bloque if t == tabla and op == QUITA_COLUMNA]
                if not indices or not columnas:
                    continue
                con_las_dos += 1
                if max(indices) > min(columnas):
                    culpables.append(
                        f"{archivo.name}: en «{tabla}» se quita un índice "
                        f"(línea {max(indices)}) después de soltar una columna "
                        f"(línea {min(columnas)}). En Postgres el índice ya se fue "
                        "con la columna y ese paso muere con «index does not exist»."
                    )

    assert not culpables, (
        "El índice de una tabla se quita antes que sus columnas:\n  - "
        + "\n  - ".join(culpables)
    )
    # Que el trinquete esté mirando algo: si un refactor moviera las
    # migraciones, el bucle no encontraría nada y el test pasaría por vacío.
    assert revisadas > 20, f"solo {revisadas} revisiones con bajada; ¿ruta mal?"
    assert con_las_dos >= 1, (
        "ninguna revisión quita índice y columna de la misma tabla en su "
        "bajada: el trinquete no está cubriendo el caso que existe para cubrir"
    )
