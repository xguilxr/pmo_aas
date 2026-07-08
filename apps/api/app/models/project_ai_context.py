"""US-185 — Memoria de proyecto para IA (extensión EP008, Revamp 1.0).

Contexto persistente por proyecto que se inyecta en TODA generación de IA
(minutas, reportes) como bloque <CONTEXTO_DEL_PROYECTO>:

- ``context_md``: curado por el PM — objetivo, glosario/siglas, reglas de
  negocio, actores clave, tono. Fuente de verdad humana.
- ``instructions_md``: instrucciones permanentes de generación (formato,
  idioma, qué destacar) — el equivalente persistente de las free_notes.
- ``auto_summary_md``: resumen acumulativo que la IA actualiza al guardar
  minutas nuevas (decisiones, acuerdos, temas recurrentes). El PM puede
  editarlo/podarlo.

1 fila por proyecto (unique). Scope tenant para particionado.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ProjectAIContext(Base, TimestampMixin):
    __tablename__ = "project_ai_contexts"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_ai_context_project"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    context_md: Mapped[str | None] = mapped_column(Text)
    instructions_md: Mapped[str | None] = mapped_column(Text)
    auto_summary_md: Mapped[str | None] = mapped_column(Text)
    auto_summary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
