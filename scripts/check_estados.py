#!/usr/bin/env python3
"""MCS DIS-03 — toda pantalla define sus cinco estados.

«Toda pantalla DEBE definir sus estados: vacío, en carga, con datos, error y
sin permiso».

## Lo que se midió, y lo que cambió al medirlo bien

La auditoría del 2026-08-04 contó «3 de 75 pantallas con los cuatro estados
detectables» y avisó de que era un proxy. Al remedirlo el 2026-08-06 por
estado, el reparto real era: 12 sin carga, 20 sin error, 31 «sin vacío» y **60
sin «sin permiso»**.

Y de esos 31 «sin vacío», al mirar QUÉ recorría cada pantalla, quedó **uno**:
los demás recorrían constantes —`PANELS`, `TAB_KEYS`, `EXPORT_FORMATS`, la
lista de reglas de una contraseña— que no pueden estar vacías. El que quedaba
—el selector de organización de `admin/areas`— ya se ocultaba con
`orgs.length > 0`; la primera versión de este barrido no lo veía porque buscaba
`.length ?` y no `.length > 0`. Es el mismo error de medida que el proxy
original, en pequeño.

## Por qué tres estados se resuelven en la frontera y uno no

El plan avisó: «hacerlo mecánicamente produciría 70 estados malos». Es cierto
del **vacío** —qué dice una lista vacía es una decisión por pantalla: «aún no
has creado ningún proyecto» invita a crear y «ningún riesgo coincide con el
filtro» invita a quitarlo— y no lo es de los otros tres. Una espera, un fallo de
red y un 403 se ven igual en las 75, y sesenta copias de la misma tarjeta
divergen en cuanto una aprende a ofrecer «reintentar».

**Definir un estado una vez para todo un segmento es definirlo.** Repetirlo
setenta veces es otra cosa.

## Lo que este control comprueba

1. Que las tres fronteras existan y sigan enganchadas.
2. Que toda pantalla que recorra una colección **traída de la API** tenga su
   propio estado vacío. Ninguna frontera puede decidir ese texto.

Uso:

    python scripts/check_estados.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"
SEGMENTO = WEB / "app" / "(app)"

#: Las tres fronteras, con lo que cada una tiene que contener para servir.
FRONTERAS: dict[str, tuple[Path, str]] = {
    "en carga": (SEGMENTO / "loading.tsx", "Cargando"),
    "error": (SEGMENTO / "error.tsx", "ErrorDeCarga"),
    "sin permiso": (SEGMENTO / "layout.tsx", "FronteraDePermiso"),
}

def trata_el_vacio(texto: str, coleccion: str) -> bool:
    """¿Trata la pantalla el caso de que `coleccion` no traiga nada?

    Se pregunta **por la colección concreta** y no por el archivo entero. La
    primera versión buscaba cualquier `.length` en el texto, y así una pantalla
    con dos listas pasaba tratando solo una — el mismo error de medida del
    proxy original. Lo destapó la verificación por mutación: quitarle la guarda
    a `admin/areas` no ponía nada en rojo.
    """
    c = re.escape(coleccion)
    return bool(
        re.search(rf"{c}\.length\s*(===?\s*0|>\s*0|\?|&&|\))", texto)
        or re.search(rf"!\s*{c}\.length", texto)
        or re.search(rf"{c}\.length\s*\?", texto)
        or re.search(rf"{c}\.length", texto)
        and re.search(rf"{c}\.length[^\n]*(\?|&&|===?|>)", texto)
    )


def colecciones_de(texto: str) -> set[str]:
    """Identificadores que la pantalla recorre **y** vienen de su estado.

    Recorrer una constante del módulo —`TAB_KEYS`, `EXPORT_FORMATS`— no exige
    estado vacío: no puede estar vacía. Lo que lo exige es recorrer algo que
    llegó de la API, y eso en este producto siempre pasa por `useState`.
    """
    estados = set(re.findall(r"const \[(\w+),\s*set\w+\] = useState", texto))
    recorridos = set(re.findall(r"\b(\w+)\s*\.map\(", texto))
    return estados & recorridos


def main() -> int:
    problemas: list[str] = []

    for estado, (archivo, marca) in FRONTERAS.items():
        if not archivo.exists():
            problemas.append(
                f"Falta la frontera del estado «{estado}»: {archivo.relative_to(WEB)} "
                f"no existe. Sin ella, las 75 pantallas se quedan sin ese estado."
            )
        # `<Marca` seguido de espacio, `/` o `>`: sin la frontera de palabra,
        # `<ErrorDeCargaX` pasaba por `<ErrorDeCarga`. Lo destapó la mutación.
        elif not re.search(
            rf"<{re.escape(marca)}[\s/>]", archivo.read_text(encoding="utf-8")
        ):
            problemas.append(
                f"{archivo.relative_to(WEB)} ya no PINTA `<{marca}>`, así que "
                f"el estado «{estado}» dejó de estar definido para el segmento. "
                f"(Se busca el elemento y no el nombre: dejar la importación y "
                f"quitar el uso pasaba la primera versión de este control.)"
            )

    sin_vacio: list[str] = []
    con_coleccion = 0
    for pagina in sorted((WEB / "app").rglob("page.tsx")):
        texto = pagina.read_text(encoding="utf-8")
        if not colecciones_de(texto):
            continue
        con_coleccion += 1
        mudas = [c for c in sorted(colecciones_de(texto)) if not trata_el_vacio(texto, c)]
        if mudas:
            sin_vacio.append(
                f"{pagina.relative_to(WEB)} recorre {mudas} y no trata el caso "
                f"de que no haya nada"
            )
    problemas.extend(sin_vacio)

    if problemas:
        print("FALLA — DIS-03:\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print(
        f"OK — las 3 fronteras (carga, error, sin permiso) cubren el segmento y "
        f"{con_coleccion} pantallas con colección tratan su estado vacío."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
