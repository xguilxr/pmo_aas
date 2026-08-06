"""DIS-01 y CFG-14 — los valores visuales se expresan como tokens, y se verifica.

> «Los valores visuales DEBEN expresarse como tokens. NO DEBEN existir valores
> literales de color ni de espaciado en el código de componentes.»

La auditoría contó **25 literales `#rrggbb`** en `apps/web/components` y
`apps/web/app`, y `CFG-14` repitió la cifra. `globals.css` ya centralizaba los
tokens; lo que faltaba era que nada impidiera escribir el color a mano al lado.

## Las tres cosas que vigila, y por qué la tercera es la que valía la pena

**1. Literales de color.** Un `#rrggbb` en un componente no tiene tema: se ve
igual en claro y en oscuro, y es como divergen dos paletas del mismo concepto —
que es exactamente lo que `DAT-05` encontró con la salud del proyecto.

**2. Literales de espaciado.** `px-[18px]` produce el mismo píxel que `px-4.5`
y sale de la escala. El siguiente ajuste de densidad mueve la escala y deja
atrás los que se escribieron a mano.

**3. Tokens citados que no existen.** Este es el hallazgo. `var(--token, #hex)`
parece defensivo y es lo contrario: si el token no existe, **el respaldo es lo
que se renderiza**, y nadie se entera porque se ve bien. Al enchufar esta
comprobación aparecieron cuatro citas a tokens inexistentes
—`--color-warning-soft`, `--color-warning`, `--color-danger`,
`--color-danger-soft`— en la página de documentos del proyecto: en tema oscuro
llevaba meses pintando ámbar y rojo de tema claro.

Por eso el respaldo se prohíbe además del literal. No es purismo: el respaldo es
lo que convierte un token roto en un fallo invisible.

## Qué queda fuera, y por qué

`apps/web/lib/marca.ts` — el color de marca por defecto de un inquilino.
`<input type="color">` exige un `#rrggbb` concreto y no acepta `var(--token)`,
porque su valor es un dato que viaja al servidor, no un estilo. Es una frontera
real, y se trata como el marco pide tratarlas: **explícita y nombrada**.

Uso:

    python scripts/check_tokens.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"
GLOBALS_CSS = WEB / "app" / "globals.css"

#: Dónde vive el código de componentes. `lib` y `hooks` entran aunque el
#: requisito diga «componentes»: si solo se mirara `components/`, mover el
#: literal un directorio más allá lo haría desaparecer del radar sin quitarlo
#: del producto.
AMBITOS = ("components", "app", "lib", "hooks")

#: Fronteras declaradas. Una entrada aquí es una decisión con razón escrita, no
#: una excepción de conveniencia — el mismo trato que `.pip-audit-ignore`.
FRONTERAS = {
    "lib/marca.ts": (
        "`<input type=\"color\">` exige un #rrggbb literal y no acepta "
        "var(--token): su valor es un dato del inquilino que viaja al "
        "servidor y sale en los PDF, no un estilo con tema"
    ),
}

#: Comentarios de bloque y de línea. Se descartan antes de mirar nada: un
#: comentario que explica por qué NO se usa `var(--token)` no es una infracción,
#: y contarlo como tal empuja a no documentar — el peor incentivo posible en un
#: control cuyo valor está en que se entienda.
COMENTARIO = re.compile(r"/\*.*?\*/|(?<![:\w])//[^\n]*", re.S)

HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")
ESPACIADO = re.compile(
    r"\b(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|gap-x|gap-y|space-x|space-y)"
    r"-\[[0-9.]+(?:px|rem|em)\]"
)
#: DAT-12 — un `?? 0` en **posición de renderizado**: dentro de `{…}` de JSX,
#: o como valor de una prop que se pinta. No se mira el `?? 0` de cálculo —
#: `map.get(k) ?? 0` al sumar es correcto—, solo el que tapa un hueco justo
#: antes de mostrarlo. La distinción es la que hace usable el control: sin
#: ella salían 84 avisos y 67 eran legítimos.
RENDER_CERO = re.compile(
    r"(?:value|count|total|amount)=\{[^}]*\?\?\s*0\}"
    r"|\{\s*[A-Za-z_][\w.?]*\s*\?\?\s*0\s*\}"
)

#: `var(--x, respaldo)` — el segundo grupo solo existe si hay respaldo.
VAR = re.compile(r"var\(\s*(--[a-z0-9-]+)\s*(,)?")
#: Definición de una propiedad personalizada en el CSS.
DEFINICION = re.compile(r"^\s*(--[a-z0-9-]+)\s*:", re.M)

#: Los bloques que forman la paleta BASE. El tema oscuro solo pisa algunos de
#: estos, así que un token que exista únicamente allí **no existe en claro**:
#: la declaración que lo cite se descarta y el elemento sale sin color. Contar
#: el archivo entero lo daba por bueno — lo cazó una mutación, no la lectura.
BLOQUES_BASE = ("@theme", ":root")


def _archivos() -> list[Path]:
    salida = []
    for ambito in AMBITOS:
        for patron in ("*.ts", "*.tsx"):
            salida.extend((WEB / ambito).rglob(patron))
    return sorted(x for x in salida if "node_modules" not in x.parts)


def tokens_definidos(css: str) -> set[str]:
    """Los de la paleta base, que son los que existen en los dos temas."""
    definidos: set[str] = set()
    for selector in BLOQUES_BASE:
        abre = css.index("{", css.index(selector))
        definidos |= set(DEFINICION.findall(css[abre + 1 : css.index("}", abre)]))
    return definidos


def revisar(ruta_relativa: str, contenido: str, definidos: set[str]) -> list[str]:
    """Motivos por los que `contenido` no pasa. Vacío = pasa."""
    if ruta_relativa in FRONTERAS:
        return []

    contenido = COMENTARIO.sub("", contenido)
    problemas = []
    for literal in sorted(set(HEX.findall(contenido))):
        problemas.append(
            f"color literal `{literal}`: no tiene tema, así que se ve igual en "
            f"claro y en oscuro. Va a un token de `globals.css`"
        )
    for literal in sorted(set(ESPACIADO.findall(contenido))):
        problemas.append(
            f"espaciado literal `{literal}`: queda fuera de la escala y el "
            f"siguiente ajuste de densidad lo deja atrás"
        )
    for literal in sorted(set(RENDER_CERO.findall(contenido))):
        problemas.append(
            f"`{literal}` pinta un cero donde no hay dato (DAT-12): un proyecto "
            f"sin presupuesto cargado y uno con presupuesto cero piden acciones "
            f"distintas. Usá `SIN_DATO` de `@/lib/sin-dato`"
        )
    for token, respaldo in sorted(set(VAR.findall(contenido))):
        if token not in definidos:
            problemas.append(
                f"cita `{token}`, que no está definido en `globals.css`. "
                f"{'Lo que se renderiza es el respaldo' if respaldo else 'La declaración se descarta'}"
            )
        elif respaldo:
            problemas.append(
                f"`var({token}, …)` lleva respaldo: si el token desapareciera, "
                f"el respaldo taparía el fallo y nadie lo vería"
            )
    return problemas


def main() -> int:
    if not GLOBALS_CSS.is_file():
        print(f"No encuentro `{GLOBALS_CSS}`, que es donde viven los tokens.", file=sys.stderr)
        return 1
    definidos = tokens_definidos(GLOBALS_CSS.read_text(encoding="utf-8"))

    fallos: list[tuple[str, list[str]]] = []
    revisados = 0
    for archivo in _archivos():
        revisados += 1
        relativa = archivo.relative_to(WEB).as_posix()
        motivos = revisar(relativa, archivo.read_text(encoding="utf-8"), definidos)
        if motivos:
            fallos.append((relativa, motivos))

    if fallos:
        print(f"DIS-01 — {len(fallos)} archivo(s) con valores visuales fuera del sistema:\n")
        for relativa, motivos in fallos:
            print(f"  {relativa}")
            for motivo in motivos:
                print(f"    - {motivo}")
        print(
            "\nLos tokens viven en `apps/web/app/globals.css`. Si de verdad hace "
            "falta un literal, es una frontera: se declara en `FRONTERAS` de "
            "este script con la razón escrita."
        )
        return 1

    print(
        f"OK — {revisados} archivos sin literales de color ni de espaciado; "
        f"{len(definidos)} tokens definidos y todos los citados existen"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
