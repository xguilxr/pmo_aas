"""US-212 — Línea base del plan: la promesa contra la que se mide la desviación.

Dos tablas y no una columna en `tasks`. Guardar `baseline_start`/`baseline_end`
junto a las fechas vivas parece más simple y solo aguanta una línea base: la
segunda captura pisa la primera, y con ella el histórico de replanificaciones,
que es justo lo que un comité de cambios pide ver. Con dos tablas, un proyecto
tiene tantas líneas base como veces haya vuelto a prometer.

`plan_baseline_tasks.task_id` **no es una clave foránea**, y es deliberado. Una
línea base es una foto: si la tarea se borra del plan, la fila de la foto tiene
que seguir ahí, o la promesa se encoge retroactivamente y la comparación miente
en la dirección cómoda —parecería que nunca se prometió esa tarea—. Con
`ondelete="SET NULL"` la fila sobreviviría pero perdería el emparejamiento, y con
`CASCADE` desaparecería. Es el mismo criterio de `metric_snapshots.scope_id`: una
foto apunta a una entidad sin gobernar su ciclo de vida.

Por lo mismo se copian `wbs_code` y `name`: la fila tiene que poder leerse cuando
lo que retrataba ya no existe.
"""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class PlanBaseline(Base, TimestampMixin):
    __tablename__ = "plan_baselines"
    __table_args__ = (
        Index("ix_plan_baselines_project_captured", "project_id", "captured_at"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: Cómo la llama el equipo: «Firmada con el cliente», «Replan Q3».
    #: Obligatorio porque «Línea base 3» no le dice a nadie contra qué compara.
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    #: Por qué se recapturó. Es el campo que contesta «¿y esto por qué se movió?»
    #: seis meses después; sin él la respuesta se va con la persona.
    note: Mapped[str | None] = mapped_column(String(2000))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Quién la capturó. Sin FK a `users` para que borrar un usuario no borre la
    #: trazabilidad de la promesa; el nombre se resuelve al leer, si existe.
    captured_by_user_id: Mapped[UUID | None] = mapped_column(String(36))
    #: Cuántas tareas tenía el plan al capturarla. Redundante con el conteo de
    #: filas; se guarda porque el listado lo muestra y contar las filas de N
    #: líneas base son N consultas.
    task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PlanBaselineTask(Base):
    __tablename__ = "plan_baseline_tasks"
    __table_args__ = (Index("ix_plan_baseline_tasks_baseline", "baseline_id"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    baseline_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("plan_baselines.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Sin FK a propósito; ver el docstring del módulo.
    task_id: Mapped[UUID] = mapped_column(String(36), nullable=False)
    wbs_code: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    is_milestone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
