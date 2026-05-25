"""Re-seed `report_sections` idempotente — BUG-063.

Revision ID: 20260524_0076
Revises: 20260523_0075
Create Date: 2026-05-24 18:00:00

Owner reportó "el catálogo de secciones sigue vacío" en
`/pmo/projects/[id]/reports/builder` tras el deploy del Sprint 26-32.
La migración 0070 corrió y creó la tabla, pero las rows aparecen
ausentes en su DB (posiblemente reset post-deploy, o `bulk_insert` no
se commitó tras el `create_table` en algún path).

Esta migración es **idempotente**: si la tabla ya tiene rows, no hace
nada. Si está vacía, inserta las 22 secciones canónicas EP020 con el
mismo contenido que el seed original de 0070.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260524_0076"
down_revision: str | None = "20260523_0075"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Duplica el contenido del seed de 0070 para evitar import dinámico
# (los nombres de archivos de migración empiezan con dígitos —
# importlib no los soporta directo). Si modificas el seed canónico,
# refleja el cambio aquí.
SEED_SECTIONS: list[tuple] = [
    # HDR
    (
        "S-01", "Portada", "HDR", 3, "A", False,
        "Cover del reporte: título, periodo, logo cliente.",
        {"fields": ["title", "period", "client_logo_url"]},
        {"period": {"type": "date_range"}},
    ),
    (
        "S-02", "Información del proyecto", "HDR", 3, "A", False,
        "Folio, sponsor, PM, fecha de corte, periodo.",
        {"fields": ["folio", "sponsor", "pm", "cutoff_date", "period"]},
        {"cutoff_date": {"type": "date"}},
    ),
    # EST
    (
        "S-03", "Semáforo global RAG", "EST", 3, "A", False,
        "Estado RAG declarativo (alcance / tiempo / costo / calidad).",
        {"fields": ["scope_rag", "time_rag", "cost_rag", "quality_rag", "comment"]},
        {},
    ),
    (
        "S-04", "Resumen ejecutivo", "EST", 3, "A", True,
        "Texto libre o generado por IA.",
        {"fields": ["text"]},
        {"source": {"enum": ["manual", "ia"], "default": "manual"}},
    ),
    # AVN
    (
        "S-06", "% Avance plan vs real", "AVN", 3, "A", False,
        "Gauge / card grande con % avance según método del tenant.",
        {"fields": ["progress_plan", "progress_actual", "variance"]},
        {"variant": {"enum": ["gauge", "card"], "default": "gauge"}},
    ),
    (
        "S-08", "Avance por área / WBS", "AVN", 3, "A", False,
        "Barras horizontales: avance por área o WBS nivel 1.",
        {"fields": ["rows"], "row": ["label", "progress"]},
        {"group_by": {"enum": ["area", "wbs1"], "default": "area"}},
    ),
    (
        "S-19", "Snapshot Gantt WBS-1", "AVN", 3, "A", False,
        "Imagen renderizada del Gantt a primer nivel de WBS.",
        {"fields": ["image_url", "rendered_at"]},
        {"wbs_level": {"type": "int", "default": 1},
         "window_start": {"type": "date"}, "window_end": {"type": "date"}},
    ),
    # PLN
    (
        "S-09", "Hitos", "PLN", 3, "A", True,
        "Hitos agrupados por estado (Cumplidos / Próximos / Críticos / Vencidos).",
        {"fields": ["completed", "upcoming", "critical", "overdue"]},
        {"lookahead_proximos": {"type": "int", "default": 30},
         "ventana_cumplidos": {"type": "int", "default": 14}},
    ),
    (
        "S-16", "Críticos", "PLN", 3, "A", False,
        "Tareas críticas (is_critical=true) priorizadas por fecha plan.",
        {"fields": ["rows"], "row": ["task", "plan_end", "state", "owner", "area"]},
        {},
    ),
    (
        "S-17", "Retrasadas", "PLN", 3, "A", True,
        "Tareas vencidas; excluye milestones/críticos si S-09/S-16 están en el reporte.",
        {"fields": ["by_area"]},
        {"top_n_resumen": {"type": "int", "default": 10},
         "modo": {"enum": ["resumen", "detalle"], "default": "resumen"}},
    ),
    (
        "S-18", "Próximas (En curso + Arranca)", "PLN", 3, "A", True,
        "En curso ahora + arranca en los próximos N días.",
        {"fields": ["en_curso", "arranca"]},
        {"lookahead": {"type": "int", "default": 21},
         "mostrar_en_curso": {"type": "bool", "default": True},
         "mostrar_arranca": {"type": "bool", "default": True}},
    ),
    # RAID
    (
        "S-14", "Acciones (A)", "RAID", 3, "A", False,
        "Acciones pendientes con responsable y fecha compromiso.",
        {"fields": ["rows"], "row": ["title", "owner", "due_date", "status"]},
        {"top_n": {"type": "int", "default": 10}},
    ),
    (
        "S-11", "Riesgos (R)", "RAID", 3, "A", True,
        "Top N riesgos por severidad con dueño y mitigación.",
        {"fields": ["rows"], "row": ["title", "severity", "owner", "mitigation"]},
        {"top_n": {"type": "int", "default": 10}},
    ),
    (
        "S-13", "Decisiones (D)", "RAID", 3, "A", False,
        "Decisiones del periodo con sponsor que decide.",
        {"fields": ["rows"], "row": ["title", "sponsor", "date", "outcome"]},
        {},
    ),
    (
        "S-12", "Issues (I)", "RAID", 3, "A", True,
        "Issues abiertos; default modo resumen.",
        {"fields": ["rows"], "row": ["title", "owner", "severity", "status"]},
        {"modo": {"enum": ["resumen", "detalle"], "default": "resumen"}},
    ),
    # EQP
    (
        "S-20", "Composición del equipo / actores activos", "EQP", 3, "B", False,
        "Listado de actores activos del periodo agrupados por área.",
        {"fields": ["by_area"]},
        {},
    ),
    (
        "S-21", "Carga por responsable", "EQP", 3, "B", False,
        "Número de tareas abiertas por responsable; semáforo por umbrales tenant.",
        {"fields": ["rows"], "row": ["owner", "open_tasks", "load_rag"]},
        {},
    ),
    # NAR
    (
        "S-28", "Bloque narrativo libre", "NAR", 3, "A", False,
        "Rich text editable para notas, contexto, próximos pasos.",
        {"fields": ["html"]},
        {},
    ),
    # PRT
    (
        "S-33", "Mapa de proyectos por estado", "PRT", 1, "A", False,
        "Matriz de proyectos del portafolio segmentados por estado RAG.",
        {"fields": ["projects"], "project": ["name", "rag", "phase"]},
        {"group_by": {"enum": ["rag", "phase"], "default": "rag"}},
    ),
    (
        "S-34", "Top riesgos del portafolio", "PRT", 1, "A", True,
        "Top N riesgos cross-proyecto ordenados por severidad.",
        {"fields": ["rows"], "row": ["project", "risk", "severity", "owner"]},
        {"top_n": {"type": "int", "default": 10}},
    ),
    (
        "S-35", "Avance promedio del portafolio", "PRT", 1, "A", False,
        "Avance ponderado del portafolio (usa método configurado del tenant).",
        {"fields": ["avg_progress", "by_project"]},
        {},
    ),
    (
        "S-36", "Proyectos en alerta", "PRT", 1, "A", True,
        "Proyectos amber/red con razón principal del semáforo.",
        {"fields": ["rows"], "row": ["project", "rag", "reason"]},
        {},
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = bind.execute(sa.text("SELECT COUNT(*) FROM report_sections")).scalar()
    if existing and int(existing) > 0:
        # Idempotencia: ya hay rows. Nada que hacer.
        return

    now = datetime.now(UTC)
    rows = []
    for (
        code, name, category, level, mode, supports_ia,
        description, data_shape, parameters_schema,
    ) in SEED_SECTIONS:
        rows.append({
            "id": str(uuid.uuid4()),
            "code": code,
            "name": name,
            "description": description,
            "category": category,
            "level": level,
            # BUG-063: dicts NATIVOS (sin json.dumps) para evitar
            # double-encoding en sa.JSON.
            "data_shape": data_shape,
            "parameters_schema": parameters_schema,
            "composition_mode_default": mode,
            "supports_ia": supports_ia,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
        })

    sections_tbl = sa.table(
        "report_sections",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("level", sa.Integer),
        sa.column("data_shape", sa.JSON),
        sa.column("parameters_schema", sa.JSON),
        sa.column("composition_mode_default", sa.String),
        sa.column("supports_ia", sa.Boolean),
        sa.column("enabled", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(sections_tbl, rows)


def downgrade() -> None:
    # No-op: la migración original (0070) es la responsable de los rows.
    # Si necesitas borrar todo, hazlo en un downgrade de 0070.
    pass
