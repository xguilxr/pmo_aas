from datetime import date, datetime
from uuid import UUID

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

from app.core.magnitudes import Escala, Severidad
from app.db.base import Base, TimestampMixin, new_uuid


class _ModuleBase:
    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folio: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Risk(Base, _ModuleBase, TimestampMixin):
    __tablename__ = "risks"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_risks_tenant_folio"),)

    category: Mapped[str | None] = mapped_column(String(100))
    probability: Mapped[Escala | None] = mapped_column(SmallInteger)
    impact: Mapped[Escala | None] = mapped_column(SmallInteger)
    severity: Mapped[Severidad | None] = mapped_column(Integer)  # computed client-side for SQLite compat
    mitigation_strategy: Mapped[str | None] = mapped_column(String(5000))
    owner_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    # ENH-079: owner como Actor del catálogo (FK actors). Coexiste con
    # `owner_id` legacy hasta que el dropdown migre a Actores.
    owner_actor_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("actors.id", ondelete="SET NULL")
    )
    # US-064: área responsable. Obligatorio en ítems nuevos vía Pydantic;
    # nullable en DB para preservar legacy (pre-migración 0024).
    area_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("areas.id", ondelete="SET NULL")
    )
    identified_at: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    closure_note: Mapped[str | None] = mapped_column(String(5000))
    # US-179: campos de detención (status="on_hold"). Razón + dependencia
    # (área y responsable que bloquean) + desde cuándo está detenido (para
    # calcular el tiempo en pausa). on_hold_since lo setea el servidor al
    # entrar a on_hold.
    on_hold_reason: Mapped[str | None] = mapped_column(String(2000))
    on_hold_area_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("areas.id", ondelete="SET NULL")
    )
    on_hold_actor_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("actors.id", ondelete="SET NULL")
    )
    on_hold_since: Mapped[date | None] = mapped_column(Date)
    # US-058: comentarios tipo Jira (lista de {text, author_id, created_at}).
    comments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Issue(Base, _ModuleBase, TimestampMixin):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_issues_tenant_folio"),)

    type: Mapped[str] = mapped_column(String(32), nullable=False)  # action/issue/decision
    # ENH-177: categoría libre (alineación con Risk.category).
    category: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[Escala | None] = mapped_column(SmallInteger)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_date: Mapped[date | None] = mapped_column(Date)
    resolution: Mapped[str | None] = mapped_column(String(5000))
    comments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    owner_id: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    # ENH-079: owner como Actor del catálogo.
    owner_actor_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("actors.id", ondelete="SET NULL")
    )
    # US-064: igual que Risk.area_id.
    area_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("areas.id", ondelete="SET NULL")
    )
    # US-179: campos de detención (status="on_hold"), igual que Risk.
    on_hold_reason: Mapped[str | None] = mapped_column(String(2000))
    on_hold_area_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("areas.id", ondelete="SET NULL")
    )
    on_hold_actor_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("actors.id", ondelete="SET NULL")
    )
    on_hold_since: Mapped[date | None] = mapped_column(Date)


class ChangeRequest(Base, _ModuleBase, TimestampMixin):
    __tablename__ = "change_requests"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_chg_tenant_folio"),)

    type: Mapped[str] = mapped_column(String(32), nullable=False)  # scope/time/cost/resource
    impact: Mapped[str | None] = mapped_column(String(5000))
    requested_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(Base, _ModuleBase, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_doc_tenant_folio"),)

    category: Mapped[str | None] = mapped_column(String(32))
    file_url: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Lesson(Base, _ModuleBase, TimestampMixin):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_lesson_tenant_folio"),)

    category: Mapped[str | None] = mapped_column(String(32))
    phase: Mapped[str | None] = mapped_column(String(32))
    recommendation: Mapped[str | None] = mapped_column(String(5000))
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # US-117: dueño como Actor del catálogo (consistente con risks/issues/tasks).
    owner_actor_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("actors.id", ondelete="SET NULL")
    )


class MeetingMinute(Base, _ModuleBase, TimestampMixin):
    __tablename__ = "meeting_minutes"
    __table_args__ = (UniqueConstraint("tenant_id", "folio", name="uq_min_tenant_folio"),)

    meeting_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    participants: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    agreements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    next_meeting_date: Mapped[date | None] = mapped_column(Date)
    attachments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    transcript_file_id: Mapped[str | None] = mapped_column(String(36))
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # ENH-106 + US-143: campo de auditoría — origen de la minuta. Valores:
    # `manual` (POST normal o source_type=manual del generador unificado),
    # `transcript_ai` (job de IA aceptado a partir de transcript),
    # `minute_ai` (job de IA normalizó una minuta ya redactada — US-143),
    # `import_file` (importada desde archivo), `import_paste` (pegada).
    # No se renderiza en exports; visible solo en admin/audit-log.
    origin: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual", server_default="manual"
    )
    # US-108: sugerencias RAID detectadas por el LLM, persistidas para
    # que el PM pueda revisarlas y aprobarlas (o descartarlas) más tarde.
    # Shape: {risks: [...], issues: [...], lessons: [...], changes: [...]}.
    # Cada item: {short_desc, suggested_owner_name?, suggested_priority?,
    #            raw_quote?, status: "pending"|"approved"|"discarded",
    #            ticket_id: <uuid|null>, ticket_type: "risk"|"issue"|"lesson"|"change_request"|null}.
    raid_suggestions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
