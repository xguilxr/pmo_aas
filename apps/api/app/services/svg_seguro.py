"""MCS SEG-01 · ASVS 5.2.7 — el SVG que sube un inquilino se sanea.

«Verify that the application sanitizes, disables, or sandboxes user-supplied
Scalable Vector Graphics (SVG) scriptable content, especially as they relate to
XSS resulting from inline scripts, and foreignObject.»

## Qué se admitía antes

`logo_to_data_url` aceptaba `image/svg+xml` y lo guardaba tal cual, en base64,
dentro de `tenant.logo_url`. Un SVG **no es una imagen**: es un documento XML que
admite `<script>`, manejadores `onload=`, y `<foreignObject>` con HTML dentro.

## Por qué hacía falta igual, si hoy no explota

Hoy el logo se pinta en `<img src="data:…">`, y ahí el navegador desactiva el
guion. Y `GET /branding/tenants/{id}/logo`, que sí lo serviría como documento,
sale con `Content-Security-Policy: default-src 'none'` del middleware. O sea:
dos capas, ninguna puesta a propósito para esto.

Ese es exactamente el problema. Las dos son **circunstanciales**: el día que
alguien incruste el logo como `<svg>` para poder recolorearlo con CSS —que es lo
que se pide en cuanto hay tema oscuro—, o excluya `/branding` de la CSP como ya
se excluyó `/docs`, el guion se ejecuta y nada avisa. El control pide sanear el
contenido, y sanear es lo único que no depende de dónde se pinte después.

Y hay un daño que las dos capas **no** cubren y que ya existe: WeasyPrint
renderiza el SVG al generar los PDF, y una referencia externa (`<image
href="https://…">`) le hace pedir esa URL desde dentro de la red de Railway,
cada vez que alguien exporta un informe. Es AM-01 por otra puerta.

## Cómo se sanea

Lista blanca, no negra. Una lista negra de elementos peligrosos se queda corta
con el primero que no estaba en ella —`<set attributeName="onload" …>` no lleva
«script» en el nombre—, y SVG tiene demasiados elementos para acertar por
exclusión.

Se conserva lo que dibuja, se descarta lo demás, y las referencias solo pueden
apuntar dentro del mismo documento (`#algo`) o a `data:`. El `<style>` se
conserva porque casi todo logo exportado de Illustrator o Figma lo usa para las
clases de relleno —quitarlo dejaría los logotipos en negro—, pero su texto se
revisa: `@import` y `url(…)` a cualquier sitio que no sea `data:` lo tumban.
"""
from __future__ import annotations

import logging
import re

# El análisis va por `defusedxml` —bomba de entidades, entidades externas—; la
# **serialización** por la biblioteca estándar, que es la que expone
# `register_namespace` y `tostring`. `defusedxml` no las reexporta a propósito:
# solo endurece el analizador, que es donde está el peligro. Volver a escribir
# un árbol ya saneado no lee nada de fuera.
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as DefusedET

log = logging.getLogger(__name__)

NS_SVG = "http://www.w3.org/2000/svg"
NS_XLINK = "http://www.w3.org/1999/xlink"

#: Lo que dibuja. Todo lo que no esté aquí se descarta con sus descendientes.
#: `script`, `foreignObject`, `iframe`, `embed`, `object`, `handler`, `audio`,
#: `video` y la familia `animate*`/`set` —que puede animar un atributo hacia un
#: valor ejecutable— quedan fuera por no estar.
ELEMENTOS = frozenset({
    "svg", "g", "defs", "symbol", "use", "title", "desc", "metadata", "style",
    "path", "rect", "circle", "ellipse", "line", "polyline", "polygon",
    "text", "tspan", "textPath", "image",
    "linearGradient", "radialGradient", "stop", "pattern",
    "clipPath", "mask", "marker", "switch",
    "filter", "feBlend", "feColorMatrix", "feComponentTransfer", "feComposite",
    "feConvolveMatrix", "feDiffuseLighting", "feDisplacementMap", "feDropShadow",
    "feFlood", "feFuncA", "feFuncB", "feFuncG", "feFuncR", "feGaussianBlur",
    "feImage", "feMerge", "feMergeNode", "feMorphology", "feOffset",
    "feSpecularLighting", "feTile", "feTurbulence",
})

#: Atributos permitidos. No se enumeran los de presentación uno a uno —son más
#: de cien— sino que se descarta por patrón: cualquier `on*` y cualquier cosa
#: que no esté en esta lista ni sea de presentación conocida.
ATRIBUTOS = frozenset({
    "id", "class", "style", "transform", "d", "points", "x", "y", "x1", "y1",
    "x2", "y2", "cx", "cy", "r", "rx", "ry", "width", "height", "viewBox",
    "preserveAspectRatio", "xmlns", "version", "fill", "fill-opacity",
    "fill-rule", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "stroke-miterlimit",
    "opacity", "color", "display", "visibility", "clip-path", "clip-rule",
    "mask", "filter", "offset", "stop-color", "stop-opacity", "gradientUnits",
    "gradientTransform", "spreadMethod", "patternUnits", "patternTransform",
    "font-family", "font-size", "font-weight", "font-style", "text-anchor",
    "letter-spacing", "dominant-baseline", "baseline-shift", "dx", "dy",
    "markerWidth", "markerHeight", "refX", "refY", "orient", "overflow",
    "in", "in2", "result", "stdDeviation", "values", "type", "mode",
    "operator", "k1", "k2", "k3", "k4", "flood-color", "flood-opacity",
    "primitiveUnits", "maskUnits", "maskContentUnits", "clipPathUnits",
    "patternContentUnits", "requiredFeatures", "systemLanguage",
})

#: Los que llevan una referencia y por tanto se revisan aparte.
REFERENCIAS = frozenset({"href", f"{{{NS_XLINK}}}href"})

_CSS_PELIGROSO = re.compile(
    r"@import|expression\s*\(|javascript\s*:|behavior\s*:|-moz-binding", re.IGNORECASE
)
_CSS_URL = re.compile(r"url\s*\(\s*['\"]?([^'\")]*)", re.IGNORECASE)


class SvgInseguroError(ValueError):
    """El SVG trae algo que no se puede sanear sin cambiar lo que dibuja."""


def _local(etiqueta: str) -> str:
    """`{http://…}path` → `path`. Los comentarios traen una función, no un str."""
    if not isinstance(etiqueta, str):
        return ""
    return etiqueta.rsplit("}", 1)[-1]


def _referencia_segura(valor: str) -> bool:
    """Solo dentro del mismo documento, o incrustada.

    Lo que se cierra aquí es que WeasyPrint pida una URL externa desde dentro de
    la red de Railway cada vez que alguien exporte un PDF.
    """
    v = valor.strip().lower()
    return v.startswith("#") or v.startswith("data:image/")


def _revisa_css(texto: str) -> None:
    if _CSS_PELIGROSO.search(texto):
        raise SvgInseguroError("el <style> del SVG usa @import, expression() o javascript:")
    for destino in _CSS_URL.findall(texto):
        if destino and not _referencia_segura(destino):
            raise SvgInseguroError(f"el <style> del SVG apunta fuera: {destino[:60]}")


def sanea(contenido: bytes) -> tuple[bytes, list[str]]:
    """Devuelve `(svg_saneado, qué_se_quitó)`.

    Lanza `SvgInseguroError` si no es un SVG, o si trae una referencia externa que no
    se puede quitar sin cambiar lo que dibuja —ahí es mejor decírselo a quien lo
    sube que devolverle un logotipo distinto del que eligió—.
    """
    try:
        raiz = DefusedET.fromstring(contenido)
    except Exception as exc:  # defusedxml lanza varias cosas distintas
        raise SvgInseguroError(f"no se pudo leer como XML: {exc}") from exc

    if _local(raiz.tag) != "svg":
        raise SvgInseguroError(f"la raíz es <{_local(raiz.tag)}> y no <svg>")

    quitado: list[str] = []
    _limpia(raiz, quitado)

    ET.register_namespace("", NS_SVG)
    ET.register_namespace("xlink", NS_XLINK)
    return ET.tostring(raiz, encoding="utf-8"), quitado


def _limpia(nodo, quitado: list[str]) -> None:
    for hijo in list(nodo):
        nombre = _local(hijo.tag)
        if nombre not in ELEMENTOS:
            # `<script>` y `<foreignObject>` caen aquí, igual que cualquier
            # elemento nuevo que la especificación añada: no están en la lista.
            nodo.remove(hijo)
            quitado.append(f"<{nombre or 'comentario'}>")
            continue
        if nombre == "style":
            _revisa_css(hijo.text or "")
        _limpia(hijo, quitado)

    for atributo in list(nodo.attrib):
        nombre = _local(atributo)
        if atributo in REFERENCIAS or nombre == "href":
            if not _referencia_segura(nodo.attrib[atributo]):
                raise SvgInseguroError(
                    f"referencia externa en {_local(nodo.tag)}: "
                    f"{nodo.attrib[atributo][:60]}"
                )
            continue
        if nombre.lower().startswith("on"):
            del nodo.attrib[atributo]
            quitado.append(f"{_local(nodo.tag)}[{nombre}]")
            continue
        if nombre == "style":
            _revisa_css(nodo.attrib[atributo])
            continue
        if nombre not in ATRIBUTOS:
            del nodo.attrib[atributo]
            quitado.append(f"{_local(nodo.tag)}[{nombre}]")
