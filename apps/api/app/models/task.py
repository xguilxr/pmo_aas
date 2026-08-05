from datetime import date, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wbs: Mapped[str | None] = mapped_column(String(64))
    # US-176: orden manual del plan (reorder por fila). Null = sin reordenar
    # (cae al orden natural por WBS). Cuando se setea, manda sobre el WBS.
    position: Mapped[int | None] = mapped_column(Integer, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("tasks.id"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # US-171 + US-177: fecha de cierre real (editable). Una tarea completada
    # con closed_at > end_date se marca "Completada con atraso" (tag amarillo);
    # una NO completada con end_date < hoy se marca "Atrasada" (tag rojo).
    closed_at: Mapped[date | None] = mapped_column(Date)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_milestone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    priority: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    # ENH-051: criticidad separada del concepto general de priority. Valores:
    # low | medium | high | critical (default medium). Check constraint en
    # migración 0037.
    criticality: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium", server_default="medium"
    )
    # ENH-097: boolean explicito de criticidad, alimentado por Report Builder
    # (EP020). Coexiste con `criticality` (string enum) — owner decidió mantener
    # ambas columnas por ahora. Backfill en migración 0063 deriva true para
    # criticality in {high, critical}.
    is_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.false()
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    external_id: Mapped[str | None] = mapped_column(String(100))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # ENH-050: vincula una tarea a un hito relacionado (otra task con
    # is_milestone=true). FK self con ondelete=SET NULL.
    related_milestone_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    # US-098 / US-103: área responsable. Apunta a `areas` (catálogo
    # tenant compartido — Op A 2026-05-07). Migración 0048 repunta
    # el FK desde `project_areas` a `areas`. Las áreas visibles para
    # un proyecto se filtran via `area_assignments`.
    # Nullable; ondelete=SET NULL para que borrar un área no rompa
    # tareas históricas.
    area_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("areas.id", ondelete="SET NULL"),
        index=True,
    )
    # ENH-079: responsable como Actor del catálogo (FK actors). Reemplaza
    # el flujo legacy `owner_id → users` para Plan. Migración 0050
    # backfilea via match user_id.
    assignee_actor_id: Mapped[UUID | None] = mapped_column(
        String(36),
        ForeignKey("actors.id", ondelete="SET NULL"),
        index=True,
    )
    # US-090: outline_level computado desde wbs.split('.').length.
    outline_level: Mapped[int | None] = mapped_column(SmallInteger)
    # US-090: predecessors / successors como JSON array de wbs_code.
    # `predecessors` es authoritative; `successors` es derivado en write
    # de los predecessors de otras tareas del mismo proyecto.
    predecessors: Mapped[list | None] = mapped_column(JSON)
    successors: Mapped[list | None] = mapped_column(JSON)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("predecessor_id", "successor_id", name="uq_task_dep"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    predecessor_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    successor_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(4), nullable=False, default="FS")  # FS/SS/FF/SF
    lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# D-9 — `is_milestone` ⟹ `duration_days = 0`
# ---------------------------------------------------------------------------
#
# La regla es del glosario (§1.2): un hito es un punto de control de duración
# cero. «Hoy no está validado», decía, y la revisión la aprobó como D-9.
#
# Vive aquí y no en el endpoint porque las tareas se escriben desde muchos
# sitios —el alta manual, los tres importadores (CSV, XLSX, MS Project), el
# regenerador de plan y la semilla de demostración— y una regla del dominio que
# se aplica en uno de seis no es una regla, es una costumbre.
#
# **Normaliza en vez de rechazar**, y es deliberado: `duration_days` es un valor
# **derivado**. El propio endpoint ignora el que manda el cliente y lo recalcula
# de las fechas (US-090). Levantar un 422 sobre un campo que el usuario no
# controla lo dejaría sin forma de arreglarlo. La contradicción que sí puede
# arreglar —marcar un hito y darle un rango de varios días— se rechaza en la
# frontera, en `TaskCreate`.
#
# Ojo con el cálculo de duración: `compute_duration_days` cuenta días
# inclusivos, así que un hito con la misma fecha de inicio y fin daba 1, no 0.
# Ese era el caso corriente que incumplía la regla — no hacía falta un dato raro.


def normalizar_hito(task: "Task") -> None:
    """Aplica la regla del glosario sobre una tarea antes de guardarla."""
    if task.is_milestone:
        task.duration_days = 0


sa.event.listen(
    Task, "before_insert", lambda _mapper, _conn, target: normalizar_hito(target)
)
sa.event.listen(
    Task, "before_update", lambda _mapper, _conn, target: normalizar_hito(target)
)
