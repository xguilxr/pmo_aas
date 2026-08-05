"""Contraste WCAG 2.2 AA de los pares semánticos de `apps/web/app/globals.css`.

Mide MCS DIS-02: «toda combinación semántica de texto y fondo DEBE alcanzar la
relación de contraste exigida por WCAG 2.2 nivel AA».

Se escribió para la R1 del 2026-08-04 y **hoy falla a propósito**: 8 de 19 pares
están por debajo del mínimo, entre ellos el verde y el amarillo del semáforo de
salud. Por eso no está enganchado al CI todavía — un trinquete que nace rojo no
es un trinquete, es ruido. Se engancha el día que se retoquen los tokens, y
desde entonces protege el arreglo.

Los valores están copiados de `globals.css` a mano, que es la debilidad de esta
prueba: si alguien cambia el CSS y no toca este archivo, mide la paleta vieja.
Leerlo del CSS directamente es la mejora obvia y no se hizo por tiempo.

Uso:
    python scripts/check_contraste.py
"""
import math


def oklch_to_srgb(claridad, croma, tono_grados):
    h = math.radians(tono_grados)
    a, b = croma * math.cos(h), croma * math.sin(h)
    l_ = claridad + 0.3963377774 * a + 0.2158037573 * b
    m_ = claridad - 0.1055613458 * a - 0.0638541728 * b
    s_ = claridad - 0.0894841775 * a - 1.2914855480 * b
    lc, mc, sc = l_**3, m_**3, s_**3
    r = +4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc
    g = -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc
    bb = -0.0041960863 * lc - 0.7034186147 * mc + 1.7076147010 * sc
    return tuple(max(0.0, min(1.0, v)) for v in (r, g, bb))  # lineal

def hex_to_linear(hx):
    hx = hx.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(hx[i:i+2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)

def lum(rgb_lineal):
    r, g, b = rgb_lineal
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(c1, c2):
    a, b = lum(c1), lum(c2)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)

T = {
    "bg-app": hex_to_linear("F4F6FA"),
    "bg-surface": hex_to_linear("FFFFFF"),
    "bg-subtle": hex_to_linear("F8FAFD"),
    "bg-muted": hex_to_linear("E9EDF4"),
    "primary": hex_to_linear("1F1D17"),
    "secondary": hex_to_linear("3F3B30"),
    "tertiary": hex_to_linear("756F60"),
    "disabled": hex_to_linear("A39C8B"),
    "accent": hex_to_linear("2A4DA0"),
    "accent-fg": hex_to_linear("FFFFFF"),
    "success-fg": hex_to_linear("1F8A5B"),
    "warning-fg": hex_to_linear("B26B12"),
    "danger-fg": hex_to_linear("C0392B"),
    "success-bg": oklch_to_srgb(0.94, 0.05, 155),
    "warning-bg": oklch_to_srgb(0.95, 0.06, 85),
    "danger-bg": oklch_to_srgb(0.94, 0.04, 25),
    "info-bg": oklch_to_srgb(0.94, 0.04, 240),
    "info-fg": oklch_to_srgb(0.46, 0.12, 240),
    "neutral-400": oklch_to_srgb(0.70, 0.008, 80),
    "neutral-500": oklch_to_srgb(0.55, 0.009, 80),
}

PARES = [
    ("primary", "bg-surface", 4.5), ("primary", "bg-app", 4.5),
    ("secondary", "bg-surface", 4.5), ("secondary", "bg-app", 4.5),
    ("tertiary", "bg-surface", 4.5), ("tertiary", "bg-app", 4.5),
    ("tertiary", "bg-muted", 4.5), ("disabled", "bg-surface", 4.5),
    ("accent-fg", "accent", 4.5),
    ("success-fg", "success-bg", 4.5), ("success-fg", "bg-surface", 4.5),
    ("warning-fg", "warning-bg", 4.5), ("warning-fg", "bg-surface", 4.5),
    ("danger-fg", "danger-bg", 4.5), ("danger-fg", "bg-surface", 4.5),
    ("info-fg", "info-bg", 4.5), ("info-fg", "bg-surface", 4.5),
    ("neutral-500", "bg-surface", 4.5), ("neutral-400", "bg-surface", 3.0),
]

fallan = 0
for fg, bg, exig in PARES:
    r = ratio(T[fg], T[bg])
    ok = r >= exig
    fallan += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FALLA'} {fg:>12} sobre {bg:<12} {r:5.2f}:1  (exige {exig})")
print(f"\n{fallan} de {len(PARES)} pares por debajo del minimo AA")
