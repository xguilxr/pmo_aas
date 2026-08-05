"""DEV-04 — mypy en modo estricto, con trinquete sobre el pasivo heredado.

La auditoría del 2026-08-03 lo dejó PARCIAL y ALTA: `ruff` cubre el análisis
estático y `tsc --noEmit` la verificación de tipos del frontend, pero en Python
no había **ninguna** — ni mypy ni pyright. Un backend con 191 módulos y cero
verificación de tipos es el hueco más grande que dejaba DEV.

## Por qué una línea base y no «arreglarlo»

`mypy --strict` sobre `apps/api/app` devuelve **1.188 errores en 117 archivos**,
y ocho de cada diez son anotaciones que faltan (`no-untyped-def`,
`no-untyped-call`, `type-arg`). Eso no se arregla en una sesión, y enchufarlo
como gate dejaría el CI en rojo en cada PR — que es la forma conocida de que un
control se desactive en dos días. El repositorio ya resolvió este mismo dilema
dos veces, y de la misma manera: `.pip-audit-ignore` para las vulnerabilidades
heredadas y el techo de contexto de `conformidad.yaml`. La regla escrita allí
vale aquí igual:

> El techo va al valor de hoy: falla si el contexto CRECE, que es el riesgo
> real, no el estado heredado.

Así que **lo estricto se ejecuta entero** —no se elige a mano qué mitad de
`strict` aplica, que sería declarar el requisito cumplido sin cumplirlo— y lo
que se tolera es una lista nominal de errores ya existentes, cada uno con su
archivo y su mensaje. Código nuevo sin anotar no pasa.

## Qué es una huella

`ruta · código · mensaje`, **sin número de línea**. El número cambia al insertar
una línea en cualquier parte del archivo, así que una línea base que lo
incluyera se invalidaría con cada edición y acabaría regenerándose a ciegas —
que es como una línea base deja de vigilar nada.

Se guarda además **cuántas veces** aparece cada huella: sin el conteo, el
segundo `def sin anotar` del mismo archivo con el mismo mensaje entraría gratis.

## Uso

    python scripts/check_tipos.py              # verifica. exit 1 si algo creció
    python scripts/check_tipos.py --regenerar  # reescribe la línea base

`--regenerar` solo debería usarse **después de arreglar** cosas, y el diff lo
demuestra: si aparece una huella nueva, el trinquete se está aflojando y eso
necesita razón escrita, igual que subir el techo de contexto.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = RAIZ / "apps" / "api"
LINEA_BASE = API / ".mypy-baseline"

#: `ruta:linea:col: error: mensaje  [codigo]`. La columna es opcional.
ERROR = re.compile(r"^(?P<ruta>[^:]+):\d+:(?:\d+:)? error: (?P<mensaje>.*?)\s+\[(?P<codigo>[a-z-]+)\]$")

CABECERA = """\
# Línea base de `mypy --strict` — MCS DEV-04
#
# NO se edita a mano: la reescribe `python scripts/check_tipos.py --regenerar`.
#
# Cada fila es `veces · ruta · código · mensaje`, sin número de línea (cambia al
# insertar cualquier cosa en el archivo y volvería inútil la comparación).
#
# Es el pasivo heredado del día en que se enchufó la verificación de tipos, no
# una lista de excepciones aprobadas. Solo puede encoger. Que aparezca una
# huella nueva significa que se está aflojando el trinquete, y eso necesita
# razón escrita — la misma regla que el techo de contexto de `conformidad.yaml`.
#
# Generada: {fecha}
# Errores tolerados: {total} en {archivos} archivos
"""


def _ejecutar_mypy() -> list[str]:
    proceso = subprocess.run(  # noqa: S603 — orden fija, sin entrada del usuario
        [sys.executable, "-m", "mypy", "--no-error-summary", "--no-color-output"],
        cwd=API,
        capture_output=True,
        text=True,
    )
    if proceso.returncode not in (0, 1):
        print(proceso.stdout, proceso.stderr, sep="\n", file=sys.stderr)
        raise SystemExit(
            "mypy no llegó a analizar. Con código distinto de 0/1 el fallo es de "
            "configuración o de instalación, no de tipos: revisá la salida."
        )
    return proceso.stdout.splitlines()


def _huellas(lineas: list[str]) -> Counter[tuple[str, str, str]]:
    cuenta: Counter[tuple[str, str, str]] = Counter()
    for linea in lineas:
        m = ERROR.match(linea.strip())
        if m:
            cuenta[(m["ruta"].replace("\\", "/"), m["codigo"], m["mensaje"])] += 1
    return cuenta


def _leer_linea_base() -> Counter[tuple[str, str, str]]:
    if not LINEA_BASE.is_file():
        return Counter()
    cuenta: Counter[tuple[str, str, str]] = Counter()
    for linea in LINEA_BASE.read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.startswith("#"):
            continue
        veces, ruta, codigo, mensaje = linea.split("\t", 3)
        cuenta[(ruta, codigo, mensaje)] = int(veces)
    return cuenta


def _escribir_linea_base(cuenta: Counter[tuple[str, str, str]]) -> None:
    filas = [
        f"{veces}\t{ruta}\t{codigo}\t{mensaje}"
        for (ruta, codigo, mensaje), veces in sorted(cuenta.items())
    ]
    cabecera = CABECERA.format(
        fecha=dt.date.today().isoformat(),
        total=sum(cuenta.values()),
        archivos=len({ruta for ruta, _, _ in cuenta}),
    )
    LINEA_BASE.write_text(cabecera + "\n".join(filas) + "\n", encoding="utf-8")


def comparar(
    observado: Counter[tuple[str, str, str]], base: Counter[tuple[str, str, str]]
) -> tuple[list[str], list[str]]:
    """Devuelve `(regresiones, arreglados)`.

    Vive aparte de la orquestación para poder probarse sin llamar a mypy, que
    tarda diez segundos y necesita el entorno completo. Un gate que solo se
    puede probar corriéndolo entero es un gate que nadie prueba.
    """
    regresiones = []
    for huella, veces in sorted(observado.items()):
        toleradas = base.get(huella, 0)
        if veces > toleradas:
            ruta, codigo, mensaje = huella
            cuantas = f"{veces} vez" if veces == 1 else f"{veces} veces"
            regresiones.append(
                f"{ruta}: {mensaje}  [{codigo}]  ({cuantas}, toleradas {toleradas})"
            )
    arreglados = [
        f"{ruta}: {mensaje}  [{codigo}]  ({base[(ruta, codigo, mensaje)] - observado.get((ruta, codigo, mensaje), 0)} menos)"
        for (ruta, codigo, mensaje) in sorted(base)
        if observado.get((ruta, codigo, mensaje), 0) < base[(ruta, codigo, mensaje)]
    ]
    return regresiones, arreglados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--regenerar",
        action="store_true",
        help="reescribe la línea base con el estado de hoy",
    )
    args = parser.parse_args()

    observado = _huellas(_ejecutar_mypy())

    if args.regenerar:
        anterior = sum(_leer_linea_base().values())
        _escribir_linea_base(observado)
        ahora = sum(observado.values())
        print(f"línea base reescrita: {anterior} → {ahora} errores tolerados")
        if ahora > anterior:
            print(
                "\nOJO: la línea base CRECIÓ. El trinquete se aprieta, no se afloja: "
                "si esto es deliberado, escribí por qué en el commit.",
                file=sys.stderr,
            )
        return 0

    base = _leer_linea_base()
    regresiones, arreglados = comparar(observado, base)

    if arreglados:
        print(f"{len(arreglados)} huella(s) de la línea base ya no se producen:")
        for x in arreglados[:20]:
            print(f"  - {x}")
        if len(arreglados) > 20:
            print(f"  … y {len(arreglados) - 20} más")
        print("Corré `python scripts/check_tipos.py --regenerar` para apretar el trinquete.\n")

    if regresiones:
        print(f"mypy --strict: {len(regresiones)} error(es) FUERA de la línea base\n")
        for x in regresiones:
            print(f"  {x}")
        print(
            "\nEstos son nuevos. La línea base es el pasivo del día en que se "
            "enchufó la verificación de tipos, no una lista de excepciones "
            "aprobadas: código nuevo va anotado."
        )
        return 1

    print(
        f"OK — mypy --strict sin regresiones "
        f"({sum(observado.values())} errores heredados, {sum(base.values())} tolerados)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
