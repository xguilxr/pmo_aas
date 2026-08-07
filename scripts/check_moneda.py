#!/usr/bin/env python3
"""BUG-092 — ningún importe se rotula con una moneda escrita a mano.

El defecto: `tenant.settings.currency` ofrecía MXN, USD y EUR y **el formulario
que la guardaba era el único sitio que la leía**. Diez superficies traían
`currency: "MXN"` en el código, así que un inquilino en dólares —el propio
sembrado crea uno— veía sus importes rotulados en pesos. El número no estaba
mal; la unidad era mentira, que en un importe es lo mismo.

Decisión del owner (2026-08-07): la moneda va **sobre el proyecto**, con una
preferida por inquilino como valor inicial.

Este barrido impide la recaída. Persigue **el literal en el sitio donde se
formatea**, no la palabra: `MXN` aparece legítimamente en la lista de códigos
admitidos, en un comentario que explica el bug y en el valor por defecto, y
prohibirla ahí obligaría a no poder nombrar el problema.

Uso:

    python scripts/check_moneda.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"
API = RAIZ / "apps" / "api" / "app"

#: Un código de moneda pegado a la propiedad que decide el rótulo. Es la forma
#: exacta que tenían los diez sitios, y la que reaparece si alguien copia una
#: llamada a `Intl.NumberFormat` de otro archivo.
FORMATEO_CON_LITERAL = re.compile(r'currency:\s*"[A-Z]{3}"')

#: Los dos módulos que SÍ pueden nombrar códigos: uno es la lista admitida y el
#: otro el valor por defecto. Sin esta excepción el control se prohibiría a sí
#: mismo declarar el vocabulario.
FRONTERAS = {
    "apps/web/lib/moneda.ts",
    "apps/web/lib/moneda-tenant.ts",
    "apps/api/app/dominio/moneda.py",
}


def main() -> int:
    problemas: list[str] = []

    for base, patron in ((WEB, "*.ts"), (WEB, "*.tsx"), (API, "*.py")):
        for archivo in sorted(base.rglob(patron)):
            if "node_modules" in archivo.parts or "__pycache__" in archivo.parts:
                continue
            rel = archivo.relative_to(RAIZ).as_posix()
            if rel in FRONTERAS:
                continue
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            for numero, linea in enumerate(texto.splitlines(), 1):
                # Los comentarios pueden citar el defecto: es la única forma de
                # explicarlo. Se descuentan antes de buscar, que es lo que le
                # faltó a cinco controles anteriores de este repositorio.
                desnuda = linea.lstrip()
                if desnuda.startswith(("//", "*", "#")):
                    continue
                if FORMATEO_CON_LITERAL.search(linea):
                    problemas.append(
                        f"{rel}:{numero} rotula un importe con una moneda escrita "
                        f"a mano: {linea.strip()[:70]}"
                    )

    # La frontera tiene que existir y seguir exigiendo la moneda.
    frontera = WEB / "lib" / "moneda.ts"
    if not frontera.exists():
        problemas.append("Falta `apps/web/lib/moneda.ts`, la frontera de formateo.")
    else:
        fuente = frontera.read_text(encoding="utf-8")
        # `moneda: string` **seguido de coma o cierre**: sin eso,
        # `moneda: string = "MXN"` pasaba el control, que es exactamente el bug
        # escondido un nivel más adentro. Lo destapó la mutación.
        if not re.search(
            r"export function formatearImporte\(\s*valor[^)]*moneda: string\s*[,)]",
            fuente,
            re.S,
        ):
            problemas.append(
                "`formatearImporte` dejó de exigir la moneda, o le pusieron un "
                "valor por defecto. Un parámetro con defecto es un parámetro "
                "que nadie rellena: sería el mismo bug, más escondido."
            )

    if problemas:
        print("FALLA — BUG-092:\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print("OK — ningún importe se rotula con una moneda escrita a mano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
