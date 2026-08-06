"""CFG-04 — los mensajes de commit siguen Conventional Commits, y algo lo exige.

La auditoría del 2026-08-03 lo dejó PARCIAL: **37 de los últimos 40 commits ya
cumplían**, y no había `commitlint` ni hook. O sea, el hábito estaba y el
control no. Eso es exactamente lo que el marco distingue: `CLAUDE.md` §4
describe el formato, pero una convención descrita es una instrucción, y una
instrucción no es un control (MCA FLU-03).

Con 400 commits medidos el cumplimiento es del 97,5%, así que el gate no viene
a corregir un desastre: viene a que el 2,5% no crezca cuando nadie mire.

## Qué se exige, y qué no

Se exige la gramática de Conventional Commits —`tipo(alcance)!: descripción`—
con la lista de tipos de `CLAUDE.md` §4. **No** se exige el resto de la
convención local (el `ID —` y el `(refs #N)`), y es deliberado: el requisito del
marco dice «Conventional Commits», no «la plantilla de este repositorio», y un
gate que exige más de lo que el marco pide acaba bloqueando trabajo legítimo
—los commits de conformidad, por ejemplo, referencian `MCS SEG-05` y no un
issue— hasta que alguien lo desactiva.

Lo que sí se comprueba más allá de la gramática es lo que hace ilegible un
historial: el asunto que se va a 133 caracteres y no cabe en un `git log
--oneline`, y el cuerpo pegado al asunto sin línea en blanco, que convierte el
mensaje entero en el asunto.

## Dónde muerde

Dos sitios, y solo uno es el control:

- `.githooks/commit-msg` avisa en el momento de escribir, que es cuando el
  arreglo cuesta cero. **No es el control**: un hook local se salta con
  `--no-verify` y hay que activarlo a mano.
- El job `commits` del CI mira los commits del PR contra su base. Ese sí, y por
  eso solo se aplica al rango del PR: la historia ya integrada no se reescribe,
  y un gate que la revisara nacería rojo para siempre.

Uso:

    python scripts/check_commits.py                    # origin/main..HEAD
    python scripts/check_commits.py --rango a..b       # un rango explícito
    python scripts/check_commits.py --archivo .git/COMMIT_EDITMSG   # el hook
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: `CLAUDE.md` §4 más los tipos de la especificación que aquí no se usan pero
#: son válidos: rechazar `perf` o `revert` sería más estricto que el estándar
#: que el requisito nombra.
TIPOS = (
    "feat",
    "fix",
    "docs",
    "refactor",
    "test",
    "chore",
    "wip",
    "perf",
    "build",
    "ci",
    "style",
    "revert",
)

#: El alcance admite coma para los cambios que cruzan capas (`api,web`), que es
#: como está escrito buena parte del historial. Sin espacios ni mayúsculas: son
#: la vía por la que `api`, `Api` y `api ` acaban siendo tres alcances distintos
#: para `git log --grep`.
ASUNTO = re.compile(
    rf"^(?P<tipo>{'|'.join(TIPOS)})"
    r"(?:\((?P<alcance>[a-z0-9][a-z0-9,/-]*)\))?"
    r"(?P<ruptura>!)?"
    r": (?P<descripcion>.+)$"
)

MAX_ASUNTO = 100


def revisar(mensaje: str) -> list[str]:
    """Devuelve los motivos por los que `mensaje` no pasa. Vacío = pasa."""
    lineas = mensaje.rstrip().splitlines()
    if not lineas or not lineas[0].strip():
        return ["el mensaje está vacío"]

    asunto = lineas[0]
    problemas: list[str] = []

    if asunto.startswith(("Merge ", "Revert ")):
        return []  # los genera git, no una persona

    m = ASUNTO.match(asunto)
    if not m:
        problemas.append(
            f"el asunto no sigue `tipo(alcance): descripción`. Tipos válidos: "
            f"{', '.join(TIPOS)}"
        )
    elif not m["descripcion"].strip():
        problemas.append("la descripción está vacía")

    if len(asunto) > MAX_ASUNTO:
        problemas.append(
            f"el asunto tiene {len(asunto)} caracteres y el máximo es {MAX_ASUNTO}: "
            "no cabe en un `git log --oneline`"
        )

    if len(lineas) > 1 and lineas[1].strip():
        problemas.append(
            "falta la línea en blanco entre el asunto y el cuerpo: sin ella, git "
            "trata todo el bloque como asunto"
        )

    return problemas


def _mensajes_del_rango(rango: str) -> list[tuple[str, str]]:
    """`[(sha corto, mensaje completo)]`, sin los commits de fusión."""
    # El separador lo emite git con `%x00`, no se pone crudo en el argumento:
    # un NUL literal en la lista de `subprocess` es un `ValueError` al ejecutar.
    salida = subprocess.run(  # noqa: S603 — sin entrada del usuario en la orden
        ["git", "log", "--no-merges", "--format=%h %B%x00", rango],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    commits = []
    for bloque in salida.split("\x00"):
        bloque = bloque.strip("\n")
        if not bloque.strip():
            continue
        sha, _, mensaje = bloque.partition(" ")
        commits.append((sha, mensaje))
    return commits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rango", default=None, help="rango git, p.ej. origin/main..HEAD")
    parser.add_argument("--archivo", default=None, help="archivo con un solo mensaje (hook)")
    args = parser.parse_args()

    if args.archivo:
        mensaje = Path(args.archivo).read_text(encoding="utf-8")
        # El hook recibe el archivo con los comentarios de git dentro.
        mensaje = "\n".join(x for x in mensaje.splitlines() if not x.startswith("#"))
        entradas = [("(el que estás escribiendo)", mensaje)]
    else:
        rango = args.rango or "origin/main..HEAD"
        try:
            entradas = _mensajes_del_rango(rango)
        except subprocess.CalledProcessError:
            print(
                f"No se pudo leer el rango `{rango}`. En CI hace falta "
                "`fetch-depth: 0` y la rama base traída.",
                file=sys.stderr,
            )
            return 1
        if not entradas:
            print(f"OK — no hay commits propios en `{rango}`")
            return 0

    fallos = [(ref, revisar(mensaje)) for ref, mensaje in entradas]
    fallos = [(ref, motivos) for ref, motivos in fallos if motivos]

    if fallos:
        print(f"CFG-04 — {len(fallos)} commit(s) no siguen Conventional Commits:\n")
        for ref, motivos in fallos:
            print(f"  {ref}")
            for motivo in motivos:
                print(f"    - {motivo}")
        print(
            "\nFormato: `<tipo>(<alcance>): <descripción>`. La convención "
            "completa de este repositorio —el ID y el `(refs #N)`— está en "
            "`CLAUDE.md` §4; aquí solo se exige la gramática del estándar."
        )
        return 1

    print(f"OK — {len(entradas)} commit(s) siguen Conventional Commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
