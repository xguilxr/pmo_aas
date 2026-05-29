"""SVG inline helpers para reportes PDF (sin dependencias, sin navegador).

WeasyPrint rasteriza SVG embebido, así que generamos los charts como
strings SVG y los inyectamos en las plantillas Jinja con `| safe`.
"""
from __future__ import annotations

import math


def treemap_svg(items: list[dict]) -> str:
    """Treemap 1-D (barra proporcional) sized por `value`, coloreado por
    `color`. `items`: [{label, value, color}]. WeasyPrint rasteriza el SVG.
    Devuelve "" si no hay valores positivos."""
    rows = [i for i in items if (i.get("value") or 0) > 0]
    total = sum(i["value"] for i in rows)
    if total <= 0:
        return ""
    w, h = 320.0, 48.0
    parts = [
        f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="100%" height="48" '
        f'preserveAspectRatio="none" role="img" aria-label="Treemap presupuesto por salud">'
    ]
    x = 0.0
    for i in rows:
        seg = (i["value"] / total) * w
        label = (i.get("label") or "")[:18]
        parts.append(
            f'<rect x="{x:.1f}" y="0" width="{max(0.5, seg - 1):.1f}" height="{h}" '
            f'fill="{i.get("color", "#9ca3af")}" rx="1"/>'
        )
        if seg > 26:
            parts.append(
                f'<text x="{x + 3:.1f}" y="14" font-size="7" fill="#fff">{label}</text>'
            )
        x += seg
    parts.append("</svg>")
    return "".join(parts)


def curve_svg(
    actual: list[float],
    planned: list[float],
    actual_color: str = "#16a34a",
    planned_color: str = "#6b7280",
) -> str:
    """Curva-S: dos líneas (real sólida, planeado punteado) en 0-100%. "" si
    no hay puntos. Asume `actual` y `planned` alineados por índice/fecha."""
    n = max(len(actual), len(planned))
    if n == 0:
        return ""
    w, h, pad = 320.0, 90.0, 8.0

    def x_at(i: int) -> float:
        return w / 2 if n == 1 else pad + i * (w - 2 * pad) / (n - 1)

    def y_at(v: float) -> float:
        return h - pad - (max(0.0, min(100.0, v)) / 100.0) * (h - 2 * pad)

    def poly(vals: list[float]) -> str:
        return " ".join(f"{x_at(i):.1f},{y_at(v):.1f}" for i, v in enumerate(vals))

    parts = [
        f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="100%" height="90" '
        f'preserveAspectRatio="none" role="img" aria-label="Curva-S planeado vs real">'
    ]
    if planned:
        parts.append(
            f'<polyline points="{poly(planned)}" fill="none" stroke="{planned_color}" '
            f'stroke-width="1.3" stroke-dasharray="4 3" stroke-linejoin="round"/>'
        )
    if actual:
        parts.append(
            f'<polyline points="{poly(actual)}" fill="none" stroke="{actual_color}" '
            f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def sparkline_svg(values: list[float], color: str = "#182e4e") -> str:
    """Línea de tendencia para una serie pequeña. "" si no hay puntos."""
    n = len(values)
    if n == 0:
        return ""
    w, h, pad = 320.0, 60.0, 6.0
    vmax = max(values)
    vmin = min(0.0, min(values))
    span = (vmax - vmin) or 1.0

    def x_at(i: int) -> float:
        return w / 2 if n == 1 else pad + i * (w - 2 * pad) / (n - 1)

    def y_at(v: float) -> float:
        return h - pad - ((v - vmin) / span) * (h - 2 * pad)

    pts = " ".join(f"{x_at(i):.1f},{y_at(v):.1f}" for i, v in enumerate(values))
    area = f"{pad:.1f},{h - pad:.1f} {pts} {x_at(n - 1):.1f},{h - pad:.1f}"
    last_x, last_y = x_at(n - 1), y_at(values[-1])
    return (
        f'<svg viewBox="0 0 {w:.0f} {h:.0f}" width="100%" height="60" '
        f'preserveAspectRatio="none" role="img" aria-label="Tendencia">'
        f'<polygon points="{area}" fill="{color}" fill-opacity="0.10"/>'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.6" fill="{color}"/>'
        f"</svg>"
    )


def donut_svg(
    segments: list[dict],
    center_label: str | None = None,
    center_sub: str | None = None,
    size: float = 120.0,
    thickness: float = 20.0,
) -> str:
    """Dona de composición (salud, status, etc). `segments`:
    [{label, value, color}]. Usa stroke-dasharray sobre círculos completos
    (no arcos <path>), así un único segmento al 100% pinta el anillo
    completo en vez de colapsar. Devuelve "" si no hay valores positivos."""
    rows = [s for s in segments if (s.get("value") or 0) > 0]
    total = sum(s["value"] for s in rows)
    if total <= 0:
        return ""
    cx = cy = size / 2
    r = size / 2 - thickness / 2 - 2
    circ = 2 * math.pi * r
    parts = [
        f'<svg viewBox="0 0 {size:.0f} {size:.0f}" width="{size:.0f}" '
        f'height="{size:.0f}" role="img" aria-label="Distribución">',
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="none" '
        f'stroke="#e8e3d7" stroke-width="{thickness:.0f}"/>',
        f'<g transform="rotate(-90 {cx:.1f} {cy:.1f})">',
    ]
    offset = 0.0
    for s in rows:
        length = s["value"] / total * circ
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="none" '
            f'stroke="{s.get("color", "#9ca3af")}" stroke-width="{thickness:.0f}" '
            f'stroke-dasharray="{length:.2f} {circ - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}"/>'
        )
        offset += length
    parts.append("</g>")
    if center_label is not None:
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="{size * 0.2:.0f}" '
            f'font-weight="700" fill="#182e4e">{center_label}</text>'
        )
        if center_sub:
            parts.append(
                f'<text x="{cx:.1f}" y="{cy + size * 0.16:.1f}" '
                f'text-anchor="middle" font-size="{size * 0.085:.0f}" '
                f'fill="#756f60">{center_sub}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def gauge_svg(
    percent: float,
    color: str = "#2A4DA0",
    size: float = 120.0,
    thickness: float = 14.0,
    suffix: str = "%",
) -> str:
    """Gauge circular (avance/consumo) 0-100 con el valor al centro."""
    pct = max(0.0, min(100.0, float(percent or 0)))
    cx = cy = size / 2
    r = size / 2 - thickness / 2 - 2
    circ = 2 * math.pi * r
    filled = pct / 100 * circ
    return (
        f'<svg viewBox="0 0 {size:.0f} {size:.0f}" width="{size:.0f}" '
        f'height="{size:.0f}" role="img" aria-label="Avance {pct:.0f}%">'
        f'<g transform="rotate(-90 {cx:.1f} {cy:.1f})">'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="none" '
        f'stroke="#e8e3d7" stroke-width="{thickness:.0f}"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" fill="none" '
        f'stroke="{color}" stroke-width="{thickness:.0f}" stroke-linecap="round" '
        f'stroke-dasharray="{filled:.2f} {circ - filled:.2f}"/>'
        f"</g>"
        f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
        f'dominant-baseline="central" font-size="{size * 0.24:.0f}" '
        f'font-weight="700" fill="#182e4e">{round(pct)}{suffix}</text>'
        f"</svg>"
    )
