#!/usr/bin/env python3
"""MCS SEG-01 · ASVS 2.1.12 — ningún campo enmascarado sin forma de revelarlo.

«Verify that the user can choose to either temporarily view the entire masked
password, or temporarily view the last typed character of the password.»

## Por qué es un control y no una comodidad

Un campo enmascarado sin forma de comprobar lo escrito empuja justo a las dos
conductas que el control quiere evitar: elegir contraseñas cortas, fáciles de
teclear a ciegas, y pegarlas desde un sitio menos seguro para no equivocarse.
Poder mirar un segundo lo que uno acabó de escribir es lo que hace practicable
una contraseña larga.

## Por qué hace falta un barrido

El control **ya estaba** en `login` y en `reset` el día que se midió, copiado a
mano en cada uno. Faltaba en los nueve campos de `change-password`, `account` y
`superadmin/me` — es decir, en las pantallas donde se *elige* una contraseña
nueva, que es donde más falta hace. Ese resultado no sale de que a alguien se le
olvidara: sale de que cada pantalla tenía su copia y nadie sabía cuántas había.

Con `PasswordInput` hay una implementación. Este barrido es lo que impide que
vuelva a haber diez.

Uso:

    python scripts/check_password_input.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"

IGNORADOS = {"node_modules", ".next", "dist", "build", "out"}

#: El componente compartido, que es el único sitio donde `type="password"`
#: puede aparecer escrito: es quien alterna entre `password` y `text`.
COMPONENTE = WEB / "components" / "ui" / "password-input.tsx"

MASCARA = re.compile(r"""type\s*=\s*["']password["']""")


def revisar() -> list[str]:
    problemas: list[str] = []
    for ruta in sorted(WEB.rglob("*.tsx")):
        if IGNORADOS & set(ruta.relative_to(RAIZ).parts) or ruta == COMPONENTE:
            continue
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        for m in MASCARA.finditer(texto):
            linea = texto[: m.start()].count("\n") + 1
            problemas.append(f"{ruta.relative_to(RAIZ)}:{linea}")
    return problemas


def main() -> int:
    problemas = revisar()
    if problemas:
        print("FALLA — SEG-01 / ASVS 2.1.12:\n")
        for p in problemas:
            print(f"  - {p} — campo enmascarado escrito a mano")
        print(
            "\n  Un campo enmascarado sin control para revelarlo empuja a elegir\n"
            "  contraseñas cortas y a pegarlas desde donde sea. Usa\n"
            "  `<PasswordInput …/>` (components/ui/password-input.tsx), que lo\n"
            "  trae y vuelve a ocultar al perder el foco."
        )
        return 1
    print("OK — todos los campos enmascarados usan `PasswordInput`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
