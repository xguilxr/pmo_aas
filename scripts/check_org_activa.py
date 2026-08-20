#!/usr/bin/env python3
"""US-205 — la organización activa se elige en un solo sitio.

## Qué regla vigila

`reestructura-navegacion.md` §1, aprobado con los mockups del 2026-08-19: la
organización se elige **una vez, en el header**, y todo opera dentro de ella.

Se nombra por su US y no con un identificador `DIS-`: los del `MCS-CORE.md`
están asignados y esto no es un control de conformidad, es una regla de
producto. Mismo criterio que `check_ancho.py` (US-203) y `check_moneda.py`
(BUG-092).

Antes de US-205 el contexto estaba disperso en siete pantallas, cada una con su
`listOrganizations()`, su `<Select>` y su estado. El coste no era la duplicación
de código: era que el filtro **no viajaba**. Elegir «Constructora Delta» en el
tablero y pasar a la lista de proyectos volvía a «todas», así que la persona lo
volvía a poner en cada pantalla — o leía la siguiente creyendo que seguía
filtrada, que es el fallo silencioso.

## Por qué mira los imports y no los `<Select>`

Porque un `<Select>` de organización no se distingue de otro por su forma:
buscarlo por su marcado obliga a adivinar con expresiones regulares y falla en
los dos sentidos. El import es lo inequívoco — quien no pide la lista no puede
pintarla —, y es también la línea que alguien escribe **primero** cuando va a
duplicar el filtro.

## Filtro contra campo

`listOrganizations` sigue siendo legítimo en dos casos, y por eso esto es una
lista de excepciones con su razón escrita y no una prohibición:

- **El dueño del contexto** — `organizacion-activa.tsx`, que es quien la carga.
- **Asignación de alcance** — el administrador que decide qué organizaciones ve
  un usuario necesita **todas**, no la activa. Filtrarla por el header sería
  justamente el bug.

Los formularios (`project-form`, `program-modal`, `request-form`) conservan su
`<Select>` porque ahí la organización es un **campo** de lo que se crea, no un
filtro — pero la lista la toman del contexto, así que no aparecen aquí.

Uso:

    python scripts/check_org_activa.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"

#: Ruta relativa a `apps/web` → por qué esa pantalla o componente sí carga la
#: lista completa de organizaciones.
PERMITIDOS: dict[str, str] = {
    "components/organizacion-activa.tsx": (
        "es el dueño del contexto: la carga una vez para todos"
    ),
    "components/admin/user-scope-assignment-picker.tsx": (
        "asignación de alcance: el admin elige entre todas, no entre la activa"
    ),
    "app/(app)/admin/users/new/page.tsx": (
        "alta de usuario con su alcance: necesita todas las organizaciones"
    ),
    "app/(app)/admin/users/[id]/page.tsx": (
        "detalle de usuario con su alcance: necesita todas las organizaciones"
    ),
}

#: El import, no la llamada: quien no la importa no la puede usar. Se acepta
#: tanto el import suelto como el de una lista con llaves en varias líneas.
IMPORTA = re.compile(r"\blistOrganizations\b")

#: El contrato en sí. No es una pantalla y no cuenta como consumidor.
FUENTE = "lib/api/organizations.ts"


def ruta_de(archivo: Path) -> str:
    return str(archivo.relative_to(WEB)).replace("\\", "/")


def main() -> int:
    archivos = sorted(
        p
        for carpeta in ("app", "components", "lib")
        for p in (WEB / carpeta).rglob("*.ts*")
        if p.is_file()
    )
    if not archivos:
        print(f"FALLA — no encontré fuentes bajo {WEB}", file=sys.stderr)
        return 1

    problemas: list[str] = []
    vistos: set[str] = set()

    for archivo in archivos:
        ruta = ruta_de(archivo)
        if ruta == FUENTE:
            continue
        if not IMPORTA.search(archivo.read_text(encoding="utf-8")):
            continue
        vistos.add(ruta)
        if ruta in PERMITIDOS:
            continue
        problemas.append(
            f"  - {ruta} carga su propia lista de organizaciones. Si es un "
            "filtro, lee `useOrgFiltro()` del header; si de verdad necesita "
            "todas, declárala en `PERMITIDOS` con la razón."
        )

    # Una excepción que ya no se usa: el archivo dejó de pedir la lista y la
    # entrada quedó autorizando algo que no pasa. La lista tiene que decir la
    # verdad, igual que en `check_ancho.py`.
    for ruta, motivo in sorted(PERMITIDOS.items()):
        if ruta not in vistos:
            problemas.append(
                f"  - `PERMITIDOS` autoriza «{ruta}» ({motivo}) y ese archivo "
                "ya no carga la lista. Quita la entrada."
            )

    if problemas:
        print(
            "FALLA — US-205 (la organización activa se elige en un solo sitio):\n",
            file=sys.stderr,
        )
        print("\n".join(problemas), file=sys.stderr)
        print(
            "\nLa regla es de `reestructura-navegacion.md` §1: la organización "
            "se elige en el header y todo opera dentro de ella. El contexto "
            "vive en `components/organizacion-activa.tsx`.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK — {len(vistos)} archivos cargan la lista de organizaciones y los "
        f"{len(PERMITIDOS)} tienen su razón escrita."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
