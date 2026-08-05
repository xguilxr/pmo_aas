"""Contraste WCAG 2.2 AA de los pares semánticos de `apps/web/app/globals.css`.

Mide **MCS DIS-02**: «toda combinación semántica de texto y fondo DEBE alcanzar
la relación de contraste exigida por WCAG 2.2 nivel AA».

Se escribió para la R1 del 2026-08-04, cuando 8 de 19 pares estaban por debajo
del mínimo, y **no se enganchó al CI** porque nacía rojo: un trinquete que falla
desde el primer día se desactiva en dos, y entonces no vigila nada. El
2026-08-05 se retocaron los tokens y desde entonces corre en CI.

**Ahora lee los valores del CSS.** La primera versión los llevaba copiados a
mano, y su propio encabezado admitía el agujero: quien cambiara `globals.css`
sin tocar este archivo seguiría midiendo la paleta vieja, en verde. Un control
que puede desincronizarse de lo que vigila no es un control — y era justo el
caso que este script existe para evitar, porque un contraste verificado a mano
se rompe en el siguiente ajuste de marca.

Uso:
    python scripts/check_contraste.py        # exit 1 si algún par falla
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "apps" / "web" / "app" / "globals.css"

# ---------------------------------------------------------------------------
# Conversión de color
# ---------------------------------------------------------------------------


def oklch_a_srgb_lineal(claridad: float, croma: float, tono_grados: float):
    h = math.radians(tono_grados)
    a, b = croma * math.cos(h), croma * math.sin(h)
    l_ = claridad + 0.3963377774 * a + 0.2158037573 * b
    m_ = claridad - 0.1055613458 * a - 0.0638541728 * b
    s_ = claridad - 0.0894841775 * a - 1.2914855480 * b
    lc, mc, sc = l_**3, m_**3, s_**3
    r = +4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc
    g = -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc
    bb = -0.0041960863 * lc - 0.7034186147 * mc + 1.7076147010 * sc
    return tuple(max(0.0, min(1.0, v)) for v in (r, g, bb))


def hex_a_srgb_lineal(hx: str):
    hx = hx.lstrip("#")
    if len(hx) == 3:
        hx = "".join(c * 2 for c in hx)
    fuera = []
    for i in (0, 2, 4):
        c = int(hx[i : i + 2], 16) / 255
        fuera.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(fuera)


def luminancia(rgb_lineal) -> float:
    r, g, b = rgb_lineal
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def relacion(c1, c2) -> float:
    a, b = luminancia(c1), luminancia(c2)
    alto, bajo = max(a, b), min(a, b)
    return (alto + 0.05) / (bajo + 0.05)


# ---------------------------------------------------------------------------
# Lectura de globals.css
# ---------------------------------------------------------------------------

_OKLCH = re.compile(
    r"oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)\s*(?:/\s*[\d.]+\s*)?\)", re.I
)
_HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_DECLARACION = re.compile(r"--(color-[\w-]+)\s*:\s*([^;]+);")


def _valor_a_lineal(bruto: str):
    """`None` si el valor no es un color sólido que sepamos medir."""
    if m := _OKLCH.search(bruto):
        claridad = float(m.group(1)) / (100 if m.group(2) else 1)
        return oklch_a_srgb_lineal(claridad, float(m.group(3)), float(m.group(4)))
    if m := _HEX.search(bruto):
        return hex_a_srgb_lineal(m.group(1))
    return None


#: La paleta clara está repartida en dos bloques: `@theme` trae la escala neutra
#: y el acento —los que Tailwind convierte en utilidades—, y `:root` los tokens
#: semánticos. El tema oscuro solo pisa algunos de `:root`.
BLOQUES = {"claro": ("@theme", ":root"), "oscuro": ('[data-theme="dark"]',)}


def _cuerpo(css: str, selector: str) -> str:
    """El contenido entre llaves del bloque que abre `selector`.

    Se corta por llaves y no con una expresión regular sobre todo el archivo
    porque `globals.css` tiene más bloques —`@media`, utilidades— cuyos tokens
    no pertenecen a ninguna de las dos paletas.
    """
    abre = css.index("{", css.index(selector))
    return css[abre + 1 : css.index("}", abre)]


def paletas() -> dict[str, dict]:
    """`{tema: {token: rgb_lineal}}`. El oscuro hereda del claro lo que no pisa."""
    css = CSS.read_text(encoding="utf-8")

    def leer(selectores):
        tokens = {}
        for selector in selectores:
            for nombre, bruto in _DECLARACION.findall(_cuerpo(css, selector)):
                if (color := _valor_a_lineal(bruto)) is not None:
                    tokens[nombre] = color
        return tokens

    claro = leer(BLOQUES["claro"])
    return {"claro": claro, "oscuro": {**claro, **leer(BLOQUES["oscuro"])}}


# ---------------------------------------------------------------------------
# Los pares que el propio diseño declara semánticos
# ---------------------------------------------------------------------------

#: `(texto, fondo, mínimo, temas)`. 4.5 es AA para texto normal; 3.0 es el
#: mínimo de WCAG 1.4.11 para elementos no textuales, que es lo que le aplica a
#: `neutral-400`: sirve de borde y pista visual, no para leer.
#:
#: Se nombran los alias `color-surface`/`color-app` y no `color-bg-surface`,
#: que es el par de tokens que el bloque oscuro **no** pisa: medir contra ellos
#: daría fondo blanco en tema oscuro y un resultado sin sentido.
#:
#: Los dos pares de la escala neutra se miden **solo en claro**, y no por
#: comodidad: `--color-neutral-*` es una escala fija que ningún tema pisa —es
#: paleta, no token semántico— así que «neutral-500 sobre la superficie
#: oscura» no es una combinación que el diseño declare en ninguna parte. En
#: oscuro el texto sale de `primary`/`secondary`/`tertiary`, que sí se miden en
#: los dos. Hoy además ningún componente usa la escala neutra directamente.
PARES = [
    ("color-primary", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-primary", "color-app", 4.5, ("claro", "oscuro")),
    ("color-secondary", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-secondary", "color-app", 4.5, ("claro", "oscuro")),
    ("color-tertiary", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-tertiary", "color-app", 4.5, ("claro", "oscuro")),
    ("color-tertiary", "color-muted", 4.5, ("claro", "oscuro")),
    ("color-accent-fg", "color-accent", 4.5, ("claro", "oscuro")),
    ("color-success-fg", "color-success-bg", 4.5, ("claro", "oscuro")),
    ("color-success-fg", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-warning-fg", "color-warning-bg", 4.5, ("claro", "oscuro")),
    ("color-warning-fg", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-danger-fg", "color-danger-bg", 4.5, ("claro", "oscuro")),
    ("color-danger-fg", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-info-fg", "color-info-bg", 4.5, ("claro", "oscuro")),
    ("color-info-fg", "color-surface", 4.5, ("claro", "oscuro")),
    ("color-neutral-500", "color-surface", 4.5, ("claro",)),
    ("color-neutral-400", "color-surface", 3.0, ("claro",)),
]

#: Fuera de medición, con el motivo escrito. WCAG 1.4.3 excluye el texto de los
#: controles inactivos, y `--color-disabled` solo aparece en variantes
#: `disabled:` de `button.tsx` e `input.tsx` y en la pista apagada de
#: `switch.tsx`. **La exención depende de ese uso:** el día que el token tiña
#: texto tenue que igual hay que leer, deja de estar exento y vuelve a PARES.
EXENTOS = {"color-disabled": "WCAG 1.4.3 — solo tiñe controles inactivos"}


def main() -> int:
    todas = paletas()
    fallan = 0
    medidos = 0

    for tema, tokens in todas.items():
        print(f"\n--- tema {tema} ---")
        for texto, fondo, minimo, temas in PARES:
            if tema not in temas:
                continue
            medidos += 1
            if texto not in tokens or fondo not in tokens:
                print(f"AUSENTE {texto} / {fondo} — no está en globals.css")
                fallan += 1
                continue
            r = relacion(tokens[texto], tokens[fondo])
            ok = r >= minimo
            fallan += 0 if ok else 1
            print(
                f"{'OK   ' if ok else 'FALLA'} {texto:>20} sobre {fondo:<20} "
                f"{r:5.2f}:1  (exige {minimo})"
            )

    for token, motivo in EXENTOS.items():
        print(f"\nEXENTO {token} — {motivo}")

    total = medidos
    if fallan:
        print(f"\n{fallan} de {total} pares por debajo del mínimo AA")
        return 1
    print(f"\n{total} de {total} pares cumplen WCAG 2.2 AA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
