"""LEN-02 — un mensaje de error nuevo dice qué, por qué y qué hacer.

> «Todo mensaje de error DEBE indicar qué ocurrió, por qué y qué acción tomar.»

La remediación del 2026-08-05 arregló los **cinco textos por defecto** —los de
`DEFECTOS`, que son los genéricos— y el requisito se quedó en PARCIAL con la
cifra escrita: de los mensajes con texto explícito, la mayoría seguía diciendo
solo qué pasó. Medido contra el árbol el 2026-08-06: **201 mensajes explícitos,
184 sin ninguna acción sugerida.**

## Por qué esto no se arregla de una pasada

Escribir el porqué y la acción de una regla de negocio exige saber qué regla es.
«No puedes borrar un super admin desde el panel de tenant» necesita que alguien
decida qué se le dice a quien lo intenta —¿que pida al superadministrador?, ¿que
lo haga desde el panel de plataforma?— y eso no se deduce del código. Reescribir
184 de un tirón produciría 184 textos plausibles y ninguno pensado.

El propio plan de remediación lo dice: «ya es norma; **se aplica al tocar cada
endpoint**». Lo que faltaba era el mecanismo que hace que eso ocurra de verdad
en vez de quedarse en intención.

## El mecanismo

Pasar una **cadena suelta** a un constructor de error es la regresión. Lo que se
espera es `errors.mensaje(que=…, porque=…, accion=…)`: tres argumentos con
nombre, ninguno con defecto, así que no se puede rellenar dos de tres. Un texto
corrido cumple el requisito el día que se escribe y deja de cumplirlo en la
primera edición sin que nada avise.

El pasivo vive en `apps/api/.len02-baseline`, por sitio, y **solo puede
encoger**. Igual que `.mypy-baseline` y `.pip-audit-ignore`: el gate falla si el
problema CRECE, no por el estado heredado.

## Por qué la forma y no el texto

Se comprobó primero con una heurística sobre la prosa —buscar un verbo en
imperativo— y se descartó: acierta a medias en los dos sentidos, y un gate que
discute la redacción con quien escribe se desactiva. La forma es objetiva.

Uso:

    python scripts/check_mensajes.py              # verifica
    python scripts/check_mensajes.py --regenerar  # reescribe la línea base
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = RAIZ / "apps" / "api"
LINEA_BASE = API / ".len02-baseline"

#: Los constructores de `app/core/errors.py` que aceptan texto.
CONSTRUCTORES = {
    "conflict",
    "validation_error",
    "business_rule",
    "service_unavailable",
    "forbidden",
    "unauthorized",
    "rate_limited",
}

CABECERA = """\
# Línea base de LEN-02 — mensajes de error con texto suelto
#
# NO se edita a mano: la reescribe `python scripts/check_mensajes.py --regenerar`.
#
# Cada fila es `ruta::función::texto`, sin número de línea (cambia al insertar
# cualquier cosa en el archivo). Es el pasivo del día en que se enchufó el
# control, no una lista de excepciones aprobadas: solo puede encoger.
#
# Para sacar uno de aquí: reescribilo con `errors.mensaje(que=…, porque=…,
# accion=…)` y regenerá.
#
# Generada: {fecha}
# Mensajes con texto suelto: {total}
"""


def _texto_literal(nodo: ast.Call) -> str | None:
    """El texto que el sitio pasa como `detail`, si es una cadena literal.

    Devuelve `None` cuando el valor se construye —una llamada, una variable, un
    `mensaje(...)`—, que es justo lo que se quiere fomentar.
    """
    candidatos = list(nodo.args) + [k.value for k in nodo.keywords if k.arg == "detail"]
    for arg in candidatos:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        if isinstance(arg, ast.JoinedStr):  # f-string
            return "".join(
                v.value if isinstance(v, ast.Constant) else "{}" for v in arg.values
            )
        # Cualquier otra forma (llamada, nombre, atributo) se considera
        # construida y no se juzga aquí.
        return None
    return None


def sitios() -> list[tuple[str, str, str]]:
    """`[(ruta, constructor, texto)]` de cada mensaje con texto suelto."""
    fuera = []
    for archivo in sorted((API / "app").rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)):
                continue
            if nodo.func.id not in CONSTRUCTORES:
                continue
            if (texto := _texto_literal(nodo)) is not None:
                fuera.append(
                    (archivo.relative_to(API).as_posix(), nodo.func.id, " ".join(texto.split()))
                )
    return sorted(fuera)


def _leer_linea_base() -> set[str]:
    if not LINEA_BASE.is_file():
        return set()
    return {
        linea
        for linea in LINEA_BASE.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.startswith("#")
    }


def _clave(sitio: tuple[str, str, str]) -> str:
    return "::".join(sitio)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerar", action="store_true")
    args = parser.parse_args()

    observado = {_clave(s) for s in sitios()}

    if args.regenerar:
        anterior = len(_leer_linea_base())
        LINEA_BASE.write_text(
            CABECERA.format(fecha=dt.date.today().isoformat(), total=len(observado))
            + "\n".join(sorted(observado))
            + "\n",
            encoding="utf-8",
        )
        print(f"línea base reescrita: {anterior} → {len(observado)} mensajes con texto suelto")
        if len(observado) > anterior:
            print(
                "\nOJO: la línea base CRECIÓ. El trinquete se aprieta, no se afloja.",
                file=sys.stderr,
            )
        return 0

    base = _leer_linea_base()
    nuevos = sorted(observado - base)
    arreglados = sorted(base - observado)

    if arreglados:
        print(f"{len(arreglados)} mensaje(s) de la línea base ya no están:")
        for x in arreglados[:10]:
            print(f"  - {x[:120]}")
        if len(arreglados) > 10:
            print(f"  … y {len(arreglados) - 10} más")
        print("Corré `python scripts/check_mensajes.py --regenerar` para apretar el trinquete.\n")

    if nuevos:
        print(f"LEN-02 — {len(nuevos)} mensaje(s) de error con texto suelto:\n")
        for x in nuevos:
            print(f"  {x[:140]}")
        print(
            "\nUn texto corrido cumple el requisito el día que se escribe y deja "
            "de cumplirlo en la primera edición. Usá "
            "`errors.mensaje(que=…, porque=…, accion=…)`: son tres argumentos "
            "sin defecto, así que no se pueden rellenar dos de tres."
        )
        return 1

    print(
        f"OK — sin mensajes de error nuevos con texto suelto "
        f"({len(observado)} heredados, {len(base)} tolerados)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
