#!/usr/bin/env python3
"""MCS SEG-01 · ASVS 10.3.2 — ningún subrecurso de un tercero sin integridad.

«Verify that the application employs integrity protections, such as code signing
or subresource integrity.»

## Qué pasaba

El mapeo del 2026-08-07 anotó este control como «hoy no se cargan recursos
externos, pero nada lo impide». **Era falso, y por eso existe este barrido.**
`app/layout.tsx` cargaba una hoja de estilo de `fonts.googleapis.com` sin
`integrity`, que a su vez decidía de qué URL de `fonts.gstatic.com` bajar los
tipos. Quien controlara ese origen —o el DNS del visitante— elegía qué CSS
ejecutaba el navegador en toda la aplicación.

La evidencia escrita a mano dijo «no hay» donde había tres. Un barrido lo mira
cada vez.

## Qué vigila

Un subrecurso **externo** (`<script src>` o `<link rel=stylesheet href>` con
esquema y dominio) que no traiga `integrity`. Los relativos no se tocan: salen
de nuestro propio origen y los cubre TLS.

## Qué NO vigila

Que el hash sea el correcto, ni que el recurso sea el que dice ser. Comprobar
eso exige bajarlo, y un barrido que necesita red no corre en un CI sin salida.
Lo que impide es la reincidencia silenciosa: hoy la respuesta correcta a «hace
falta un tipo de letra nuevo» es servirlo desde nuestro origen, y esto obliga a
escribir por qué si alguien decide otra cosa.

Tampoco mira `node_modules` ni la salida del build: son derivados, y lo que se
revisa es lo que una persona escribe.

Uso:

    python scripts/check_subrecursos.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Dónde se escribe HTML a mano en este repositorio.
ARBOLES = (RAIZ / "apps" / "web", RAIZ / "landing")

EXTENSIONES = {".tsx", ".ts", ".jsx", ".js", ".html", ".mjs"}

#: Directorios derivados: los genera una herramienta, no una persona.
IGNORADOS = {"node_modules", ".next", "dist", "build", "out", ".turbo"}

#: `<script …>` y `<link …>` completos, sin cerrar a mano el `>` dentro de
#: comillas. Basta para JSX y HTML escritos a mano, que es todo lo que hay.
ETIQUETA = re.compile(r"<(script|link)\b([^>]*)>", re.IGNORECASE | re.DOTALL)

#: Un `src`/`href` con esquema y dominio, o relativo al protocolo (`//cdn…`).
EXTERNO = re.compile(
    r"""(?:src|href)\s*=\s*["'{]?\s*["']?(?P<url>(?:https?:)?//[^"'\s`{}]+)""",
    re.IGNORECASE,
)


def _es_hoja_de_estilo(atributos: str) -> bool:
    return re.search(r"""rel\s*=\s*["']?stylesheet""", atributos, re.IGNORECASE) is not None


def _archivos():
    for arbol in ARBOLES:
        if not arbol.is_dir():
            continue
        for ruta in arbol.rglob("*"):
            if ruta.suffix not in EXTENSIONES or not ruta.is_file():
                continue
            if IGNORADOS & set(ruta.relative_to(RAIZ).parts):
                continue
            yield ruta


def revisar() -> list[str]:
    """Devuelve los hallazgos. Vacío = pasa."""
    problemas: list[str] = []
    for ruta in sorted(_archivos()):
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        for etiqueta, atributos in ETIQUETA.findall(texto):
            nombre = etiqueta.lower()
            # Un <link> solo carga código si es hoja de estilo. `preconnect`,
            # `icon` o `manifest` no ejecutan nada y no llevan integridad.
            if nombre == "link" and not _es_hoja_de_estilo(atributos):
                continue
            enlace = EXTERNO.search(atributos)
            if enlace is None:
                continue
            if re.search(r"\bintegrity\s*=", atributos, re.IGNORECASE):
                continue
            linea = texto[: texto.index(atributos)].count("\n") + 1
            problemas.append(
                f"{ruta.relative_to(RAIZ)}:{linea} — <{nombre}> externo sin "
                f"`integrity`: {enlace.group('url')[:90]}"
            )
    return problemas


def main() -> int:
    problemas = revisar()
    if problemas:
        print("FALLA — SEG-01 / ASVS 10.3.2:\n")
        for p in problemas:
            print(f"  - {p}")
        print(
            "\n  Un subrecurso de un tercero sin `integrity` es código que "
            "ejecuta\n  el navegador y que nadie de aquí ha fijado. Sírvelo "
            "desde nuestro\n  origen (para tipos de letra: `next/font`), o "
            "añade el hash si el\n  recurso es inmutable."
        )
        return 1
    print("OK — ningún subrecurso externo sin integridad en apps/web ni landing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
