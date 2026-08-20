#!/usr/bin/env python3
"""US-203 — una vista de datos usa el ancho de la pantalla.

## Qué regla vigila

`reestructura-navegacion.md` §4.1, aprobado con los mockups del 2026-08-19:
**ancho completo por default en vistas de tabla, heatmap y gantt; `max-w` solo
en formularios y detalle de texto.**

No lleva identificador `DIS-` a propósito: los del `MCS-CORE.md` están
asignados —`DIS-05` es «operable con teclado» y `DIS-06`, los patrones
WAI-ARIA— y esto no es un control de conformidad, es una regla de producto que
salió de los mockups. Se nombra por la US que la introdujo, como
`check_moneda.py` se nombra por BUG-092.

La razón es de producto, no estética. Una tabla de dieciséis columnas dentro de
un `max-w-7xl` en un monitor de 2560 px deja media pantalla vacía y obliga a
hacer scroll horizontal para leer lo que cabía. El PMO que revisa veintitrés
proyectos lo hace en un monitor grande a propósito.

## Por qué al revés que una lista de las que hay que arreglar

El gate se declara por **excepción**: toda página es una vista de datos y va a
ancho completo, salvo las que están en `ACOTADAS`. Así una pantalla nueva nace
a ancho completo sin que nadie se acuerde, y acotarla exige escribir por qué.
La lista inversa —enumerar las que deben ser anchas— habría dejado a la
siguiente pantalla fuera del gate por omisión, que es exactamente cómo se
degradó el criterio la primera vez.

## Lo que NO mira

- `max-w-[180px]` y compañía en una celda o un badge: eso es truncado de texto,
  no el contenedor de la página. Solo se busca `mx-auto max-w-…`, que es el
  patrón del contenedor.
- Componentes bajo `components/`: los monta la página, y es la página la que
  decide su ancho.

Uso:

    python scripts/check_ancho.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAGINAS = RAIZ / "apps" / "web" / "app" / "(app)"

#: Ruta → por qué su ancho está acotado. Formularios y detalle de texto: una
#: línea de 200 caracteres no se lee, y un campo de formulario de 2000 px de
#: ancho tampoco se rellena mejor.
ACOTADAS: dict[str, str] = {
    "account": "formulario de cuenta",
    "admin/ai": "formulario de proveedor de IA",
    "admin/organizations/[id]/edit": "formulario de organización",
    "admin/organizations/new": "formulario de alta",
    "admin/tenant": "formulario de ajustes del inquilino",
    "admin/users/[id]": "detalle de usuario con sus formularios",
    "admin/users/new": "formulario de alta",
    "notifications": "hilo de texto",
    "pmo/organizations/[id]/reports": "un reporte: texto",
    "pmo/programs/[id]/reports": "un reporte: texto",
    "pmo/projects/[id]/ai-context": "texto largo (memoria del proyecto)",
    "pmo/projects/[id]/charter": "acta: texto y formulario",
    "pmo/projects/[id]/edit": "formulario de proyecto",
    "pmo/projects/[id]/minutes/[minuteId]": "minuta: texto",
    "pmo/projects/[id]/minutes/new": "formulario de minuta",
    "pmo/projects/[id]/reports/[reportId]": "un reporte: texto",
    "pmo/projects/new": "formulario de alta",
    "pmo/requests/[id]": "solicitud: texto y acta",
    "pmo/requests/new": "formulario de solicitud",
    "superadmin/ai": "formulario de proveedor de plataforma",
    "superadmin/me": "formulario de cuenta",
    "superadmin/tenants/new": "formulario de alta",
}

#: El contenedor de la página, no un truncado de celda.
CONTENEDOR = re.compile(r"mx-auto\s+(max-w-[a-z0-9\[\]%.]+)")


def ruta_de(pagina: Path) -> str:
    return str(pagina.relative_to(PAGINAS)).replace("\\", "/").removesuffix("/page.tsx")


def main() -> int:
    problemas: list[str] = []
    paginas = sorted(PAGINAS.rglob("page.tsx"))
    if not paginas:
        print(f"FALLA — no encontré páginas bajo {PAGINAS}", file=sys.stderr)
        return 1

    rutas = {ruta_de(p) for p in paginas}
    anchas = acotadas = 0

    for pagina in paginas:
        ruta = ruta_de(pagina)
        anchos = CONTENEDOR.findall(pagina.read_text(encoding="utf-8"))
        exenta = ruta in ACOTADAS

        if exenta:
            acotadas += 1
            if not anchos:
                problemas.append(
                    f"  - {ruta} está declarada acotada ({ACOTADAS[ruta]}) y no "
                    "acota nada. Si dejó de ser formulario o texto, sácala de "
                    "`ACOTADAS`; la lista tiene que decir la verdad."
                )
            continue

        anchas += 1
        if anchos:
            problemas.append(
                f"  - {ruta} es una vista de datos y se encoge a "
                f"{', '.join(sorted(set(anchos)))}. Quita el `mx-auto max-w-…` "
                "del contenedor, o declárala en `ACOTADAS` con la razón."
            )

    # Una entrada de `ACOTADAS` que ya no apunta a ninguna página: la pantalla
    # se renombró o se borró, y la excepción quedó protegiendo aire.
    for ruta, motivo in sorted(ACOTADAS.items()):
        if ruta not in rutas:
            problemas.append(
                f"  - `ACOTADAS` declara «{ruta}» ({motivo}) y esa página no "
                "existe. Quita la entrada o corrige la ruta."
            )

    if problemas:
        print(
            "FALLA — US-203 (ancho de las vistas de datos):\n", file=sys.stderr
        )
        print("\n".join(problemas), file=sys.stderr)
        print(
            "\nLa regla es de `reestructura-navegacion.md` §4.1: ancho completo "
            "en tabla/heatmap/gantt; `max-w` solo en formulario y texto.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK — {anchas} vistas de datos usan el ancho completo y {acotadas} lo "
        "acotan con su motivo escrito."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
