"""SVG inline helpers para reportes PDF (sin dependencias, sin navegador).

WeasyPrint rasteriza SVG embebido, así que generamos los charts como
strings SVG y los inyectamos en las plantillas Jinja con `| safe`.
"""
from __future__ import annotations


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
