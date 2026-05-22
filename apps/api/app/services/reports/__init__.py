"""Report Builder engine (EP020).

`engine.render_template(...)` toma una plantilla declarativa
(`ReportBuilderTemplate`) + scope + ventana temporal y devuelve
`{html, json, sections_meta}`.
"""
from app.services.reports.engine import RenderResult, render_template

__all__ = ["RenderResult", "render_template"]
