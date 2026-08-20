"""US-212 / D-6 — la línea base del plan entra al esquema.

Es la brecha B-1 del diagnóstico. Sin línea base, «desviación», «retraso» y
«sobrecosto» son palabras que la plataforma ya usa sin referente: un Gantt que
se mueve solo no está atrasado respecto de nada.

## Dos tablas y no dos columnas en `tasks`

`baseline_start` / `baseline_end` junto a las fechas vivas es más barato y solo
aguanta **una** línea base: la segunda captura pisa la primera, y con ella el
histórico de replanificaciones — que es exactamente lo que un comité de cambios
pide ver («¿cuántas veces se movió esta fecha?»). Con dos tablas, un proyecto
tiene tantas líneas base como veces haya vuelto a prometer, y cada una lleva
quién la capturó y por qué.

## `plan_baseline_tasks.task_id` no lleva clave foránea

Deliberado. Una línea base es una **foto**: si la tarea se borra del plan, su
fila en la foto tiene que seguir ahí. Con `CASCADE` desaparecería y la promesa
se encogería retroactivamente —parecería que nunca se prometió esa tarea, que es
la dirección cómoda de mentir—. Con `SET NULL` la fila sobreviviría pero
perdería el emparejamiento, y la comparación la contaría como una promesa
anónima. Mismo criterio que `metric_snapshots.scope_id`: una foto apunta a una
entidad sin gobernar su ciclo de vida.

Por eso también se copian `wbs_code` y `name`: la fila tiene que poder leerse
cuando lo que retrataba ya no existe.

## Sin datos que migrar, y no es un atajo

No hay línea base previa que convertir: el concepto no existía. Capturar una
automáticamente desde el plan de hoy sería lo peor que podría hacer esta
migración — inventaría una promesa que nadie hizo, con la fecha de hoy, y todo
proyecto aparecería con desviación cero. La ausencia de línea base es un estado
que la interfaz **dice** (MCS DAT-12), no uno que se rellena.

## La bajada

Suelta los índices antes que las tablas —en Postgres soltar una tabla se lleva
sus índices, y un `drop_index` posterior muere con «index does not exist»; es el
fallo que la 0109 dejó en el CI del 2026-08-19—. Y suelta primero la tabla hija:
al revés, la clave ajena de `plan_baseline_tasks` apuntaría a una tabla que ya no
existe. Destruye las líneas base capturadas, que es lo esperable en un
`downgrade` que retira una entidad: no hay dónde guardarlas.

Revision ID: 20260820_0113
Revises: 20260820_0112
Create Date: 2026-08-20
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0113"
down_revision: str | None = "20260820_0112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_baselines",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_plan_baselines_tenant_id", "plan_baselines", ["tenant_id"])
    op.create_index("ix_plan_baselines_project_id", "plan_baselines", ["project_id"])
    # El listado siempre pide «las líneas base de este proyecto, la más reciente
    # primero»; el índice compuesto la sirve sin ordenar en memoria.
    op.create_index(
        "ix_plan_baselines_project_captured",
        "plan_baselines",
        ["project_id", "captured_at"],
    )

    op.create_table(
        "plan_baseline_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "baseline_id",
            sa.String(length=36),
            sa.ForeignKey("plan_baselines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Sin clave ajena a `tasks`: ver el encabezado del módulo.
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("wbs_code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column(
            "is_milestone", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index(
        "ix_plan_baseline_tasks_baseline", "plan_baseline_tasks", ["baseline_id"]
    )


def downgrade() -> None:
    # Índices antes que su tabla, e hija antes que madre. Ver el encabezado.
    op.drop_index("ix_plan_baseline_tasks_baseline", table_name="plan_baseline_tasks")
    op.drop_table("plan_baseline_tasks")

    op.drop_index("ix_plan_baselines_project_captured", table_name="plan_baselines")
    op.drop_index("ix_plan_baselines_project_id", table_name="plan_baselines")
    op.drop_index("ix_plan_baselines_tenant_id", table_name="plan_baselines")
    op.drop_table("plan_baselines")
