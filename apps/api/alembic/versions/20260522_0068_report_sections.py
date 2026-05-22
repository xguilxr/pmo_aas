"""report_sections catalog + seed 22 atomic sections (US-120, EP020).

Revision ID: 20260522_0068
Revises: 20260522_0067
Create Date: 2026-05-22 10:00:00

US-120: catálogo global de secciones atómicas que el Report Builder
consume. Las 22 secciones seed cubren los catálogos cerrados del
draft `docs/epics/drafts/EP020-secciones-atomicas.md`:

- HDR: S-01 Portada, S-02 Información del proyecto.
- EST: S-03 Semáforo RAG, S-04 Resumen ejecutivo.
- AVN: S-06 %Avance, S-08 Avance por área, S-19 Snapshot Gantt WBS-1.
- PLN: S-09 Hitos, S-16 Críticos, S-17 Retrasadas, S-18 Próximas.
- RAID: S-14 Acciones, S-11 Riesgos, S-13 Decisiones, S-12 Issues.
- EQP: S-20 Composición, S-21 Carga.
- NAR: S-28 Bloque narrativo.
- PRT: S-33 Mapa proyectos, S-34 Top riesgos, S-35 Avance portafolio,
       S-36 Proyectos en alerta.

Secciones deferidas a v2.0 (no seedeadas): S-05 tendencia, S-07 curva S,
S-10 entregables formales, S-15 matriz P×I, S-29/S-30 IA narrativa,
S-31/S-32 KPIs configurables.
"""
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "20260522_0068"
down_revision: str | None = "20260522_0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (code, name, category, level, composition_mode_default,
#  supports_ia, description, data_shape, parameters_schema)
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
    # RAID — orden A→R→D→I
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
    # PRT — Niveles 1 y 2
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
    op.create_table(
        "report_sections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=8), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("data_shape", sa.JSON(), nullable=False),
        sa.Column("parameters_schema", sa.JSON(), nullable=False),
        sa.Column(
            "composition_mode_default",
            sa.String(length=1),
            nullable=False,
            server_default="A",
        ),
        sa.Column(
            "supports_ia",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_report_sections_code"),
    )
    op.create_index(
        "ix_report_sections_category", "report_sections", ["category"]
    )

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
            "data_shape": json.dumps(data_shape),
            "parameters_schema": json.dumps(parameters_schema),
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
    op.drop_index("ix_report_sections_category", table_name="report_sections")
    op.drop_table("report_sections")
