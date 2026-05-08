"""ProjectArtifact — catálogo estricto de artefactos por proyecto (US-106).

Whitelist: charter | plan | raid | organigrama. Solo 1 fila por (project, type).
El charter sigue viviendo en `project_charters`; esta tabla guarda metadata
de los archivos vivos (Plan binario, export RAID, etc.) y unifica el shape
para el módulo Documentos.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid

ARTIFACT_TYPES = ("charter", "plan", "raid", "organigrama")


class ProjectArtifact(Base):
    __tablename__ = "project_artifacts"
    __table_args__ = (
        UniqueConstraint("project_id", "type", name="uq_artifact_project_type"),
        CheckConstraint(
            "type IN ('charter','plan','raid','organigrama')",
            name="ck_artifact_type_whitelist",
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_format: Mapped[str | None] = mapped_column(String(16))
    storage_url: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    filename: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
