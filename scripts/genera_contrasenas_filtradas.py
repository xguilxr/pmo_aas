#!/usr/bin/env python3
"""Genera el conjunto de contraseñas filtradas de ASVS 2.1.7.

«Verify that passwords submitted during account registration, login, and
password change are checked against a set of breached passwords either locally
(such as the top 1,000 or 10,000 most common passwords **which match the
system's password policy**) or using an external API.»

## El hallazgo que decide el diseño

Lo primero que se hizo fue lo obvio: bajar un corpus público de contraseñas
filtradas y filtrarlo por la política del producto. De las **59.186** de
`rockyou-75`, pasan la política —8 caracteres, mayúscula, dígito y símbolo—
exactamente **ocho**. De las 10.000 de `10k-most-common`, ninguna.

O sea: una lista de «las 10.000 contraseñas más usadas» aquí no protege de nada,
porque las reglas de composición ya las rechazan todas. Cargarla sería
conformidad de papel — un archivo grande, un control marcado, y cero contraseñas
detenidas.

Lo que sí amenaza a este producto es **lo que su propia política produce**. Es
justo el argumento de NIST 800-63b que ADR-032 dejó como residual aceptado: las
reglas de composición generan contraseñas *predecibles*, porque casi todo el
mundo satisface «mayúscula, dígito y símbolo» de la misma manera —capitaliza la
primera letra, pega un número al final y remata con `!`—. `Password1!` cumple la
política entera.

## Cómo se construye, entonces

Dos fuentes, las dos reproducibles:

1. **La intersección real.** Las entradas del corpus público que ya pasan la
   política tal cual (`P@ssw0rd`, `1qaz@WSX`…). Pocas, pero son datos de una
   filtración de verdad.
2. **Las mutaciones que la política obliga a hacer.** Se toman las N bases más
   frecuentes del mismo corpus y se les aplican las transformaciones
   predecibles: capitalizar, sufijos numéricos habituales, símbolo final, y
   sustituciones «leet» (`a→@`, `o→0`, `e→3`, `i→1`, `s→$`). Se conserva lo que
   pase la política.

El corpus de partida se versiona en `docs/conformidad/marco/` por el mismo
motivo que el catálogo ASVS: para que el conjunto se pueda regenerar sin red y
para que un cambio de fuente sea visible en `git log`.

Uso:

    python scripts/genera_contrasenas_filtradas.py

Escribe `apps/api/app/core/datos/contrasenas-filtradas.txt`. El resultado se
versiona: el API tiene que arrancar sin red y sin paso de generación.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CORPUS = RAIZ / "docs" / "conformidad" / "marco" / "corpus-contrasenas.txt"
SALIDA = RAIZ / "apps" / "api" / "app" / "core" / "datos" / "contrasenas-filtradas.txt"

#: Cuántas bases del corpus se mutan. Ordenado por frecuencia, así que son las
#: N más usadas.
#:
#: La primera versión de este script usaba 400 bases y una rejilla de mutaciones
#: mucho más ancha: salieron **779.911** contraseñas y 9 MB de archivo. Eso ya
#: no es «el conjunto de contraseñas filtradas que además pasan la política»,
#: es un diccionario de fuerza bruta metido en el repositorio — y empieza a
#: rechazar contraseñas que nadie ha filtrado nunca.
#:
#: Lo que explotaba era la **rejilla** de mutaciones, no el número de bases, así
#: que al estrecharla las bases pueden subir: con 250 se quedaba fuera
#: `welcome` —que está en el puesto 326 y produce `Welcome1!`, de las más
#: predecibles que existen—. Con 400 entra, y el conjunto sigue en el orden de
#: magnitud que el propio control nombra («top 1,000 or 10,000»), una vez que
#: cada base produce varias entradas.
BASES = 400

#: Lo que la gente pega al final para cumplir «un dígito». Salen de mirar la
#: cola de los propios corpus: año en curso y los alrededores, secuencias
#: cortas, y el par de números que todo el mundo usa.
SUFIJOS_NUM = ["", "1", "12", "123", "1234", "01", "11", "007", "2025", "2026"]

#: Y lo que se pega para cumplir «un símbolo». `!` es la mayoría absoluta.
SIMBOLOS = ["!", "@", "#", "$", "*", "."]

#: Sustituciones «leet». Producen `P@ssw0rd` a partir de `password`, que es la
#: contraseña que aparece en los corpus reales cuando hay reglas de composición.
LEET = {"a": "@", "o": "0", "e": "3", "i": "1", "s": "$"}

_SIMBOLOS_POLITICA = set("!@#$%^&*()-_=+[]{};:,.<>/?|`~'\"\\")


def pasa_la_politica(p: str) -> bool:
    """Misma regla que `app.core.security.validate_password_policy`.

    Se duplica a propósito y en cuatro líneas: este script se ejecuta a mano y
    fuera del entorno del API, e importar `app` desde `scripts/` obligaría a
    montar la configuración entera para generar un archivo de texto.
    `tests/test_seg01_asvs217_filtradas.py` comprueba que las dos reglas
    coinciden, que es lo que impide que se separen.
    """
    return (
        8 <= len(p) <= 128
        and any(c.isupper() for c in p)
        and any(c.isdigit() for c in p)
        and any(c in _SIMBOLOS_POLITICA for c in p)
    )


def _leet(palabra: str) -> str:
    return "".join(LEET.get(c, c) for c in palabra)


def genera(lineas: list[str]) -> set[str]:
    conjunto: set[str] = set()

    # 1 — Lo que ya pasa la política tal cual: filtración real, sin tocar.
    for p in lineas:
        if pasa_la_politica(p):
            conjunto.add(p)

    # 2 — Las mutaciones que la política obliga a hacer sobre las bases más
    #     frecuentes. Solo bases alfabéticas: mutar «123456» no produce nada
    #     que una persona vaya a escribir.
    bases = [p for p in lineas if p.isalpha() and len(p) >= 3][:BASES]
    for base in bases:
        # `Password123!` y no `Password!123`: el número antes del símbolo es
        # el orden dominante con diferencia. Y sin `.upper()`, que produce
        # `PASSWORD123!` — mucho menos frecuente y multiplicaría por 1,5.
        for raiz in {base.capitalize(), _leet(base).capitalize()}:
            for num in SUFIJOS_NUM:
                for sim in SIMBOLOS:
                    candidata = f"{raiz}{num}{sim}"
                    if pasa_la_politica(candidata):
                        conjunto.add(candidata)
    return conjunto


def main() -> int:
    if not CORPUS.is_file():
        print(f"FALTA el corpus: {CORPUS}", file=sys.stderr)
        return 1

    lineas = [
        linea.rstrip("\n")
        for linea in CORPUS.read_text(encoding="utf-8", errors="replace").splitlines()
        if linea.strip() and not linea.startswith("#")
    ]
    conjunto = genera(lineas)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        "# ASVS 2.1.7 — contraseñas filtradas que además pasan la política.\n"
        "# GENERADO por scripts/genera_contrasenas_filtradas.py. No editar a mano.\n"
        f"# Corpus: docs/conformidad/marco/corpus-contrasenas.txt ({len(lineas)} entradas).\n"
        "# Comparación en minúsculas: ver app/core/contrasenas_filtradas.py.\n"
        + "\n".join(sorted(conjunto))
        + "\n",
        encoding="utf-8",
    )
    print(f"OK — {len(conjunto)} contraseñas escritas en {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
