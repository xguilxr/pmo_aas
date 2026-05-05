from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
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
    parent_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("tasks.id"))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
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
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    external_id: Mapped[str | None] = mapped_column(String(100))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
