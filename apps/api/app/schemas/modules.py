from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

# BUG-048: strip + min_length para evitar títulos whitespace-only.
TitleStr = Annotated[
    str, StringConstraints(min_length=2, max_length=200, strip_whitespace=True)
]
OptionalTitleStr = Annotated[
    str | None,
    StringConstraints(min_length=2, max_length=200, strip_whitespace=True),
]


# ---------- Area embed (US-064) ----------
class AreaMini(BaseModel):
    """Shape minimo del área embebida en RiskRead/IssueRead para que la
    UI no haga join aparte."""

    id: UUID
    name: str

    model_config = {"from_attributes": True}


# ---------- User embed (BUG-035) ----------
class UserMini(BaseModel):
    """Shape mínimo del owner embebido en RiskRead/IssueRead para que el
    sidebar de RAID detail muestre nombre en vez de UUID."""

    id: UUID
    full_name: str | None = None
    email: str

    model_config = {"from_attributes": True}


# ---------- Risks ----------
class RiskCreate(BaseModel):
    title: TitleStr
    description: str | None = None
    category: str | None = None
    probability: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    mitigation_strategy: str | None = None
    owner_id: UUID | None = None
    owner_actor_id: UUID | None = None
    # US-064: area_id obligatoria en creación (422 si falta).
    area_id: UUID
    identified_at: date | None = None
    due_date: date | None = None
    status: Literal["identified", "analyzing", "mitigating", "materialized", "closed"] = "identified"


class RiskUpdate(BaseModel):
    title: OptionalTitleStr = None
    description: str | None = None
    category: str | None = None
    probability: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    mitigation_strategy: str | None = None
    owner_id: UUID | None = None
    owner_actor_id: UUID | None = None
    area_id: UUID | None = None  # US-064: permite asignar área a legacy.
    # ENH-054: identified_at editable post-creación.
    identified_at: date | None = None
    due_date: date | None = None
    status: Literal["identified", "analyzing", "mitigating", "materialized", "closed"] | None = None
    closure_note: str | None = None


class RiskRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    description: str | None
    category: str | None
    probability: int | None
    impact: int | None
    severity: int | None
    mitigation_strategy: str | None
    owner_id: UUID | None
    owner_actor_id: UUID | None = None
    owner: UserMini | None = None  # BUG-035: nombre del responsable.
    # ENH-175: responsable resuelto (Actor con fallback a Usuario) para la
    # columna Responsable de las listas RAID.
    responsible_name: str | None = None
    area_id: UUID | None
    area: AreaMini | None = None  # US-064: embebido por endpoint.
    identified_at: date | None
    due_date: date | None
    status: str
    closure_note: str | None
    comments: list = []

    model_config = {"from_attributes": True}


class RiskComment(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


# ---------- Issues ----------
class IssueCreate(BaseModel):
    title: TitleStr
    description: str | None = None
    type: Literal["action", "issue", "decision"]
    priority: int | None = Field(default=None, ge=1, le=5)
    committed_date: date | None = None
    owner_id: UUID | None = None
    owner_actor_id: UUID | None = None
    area_id: UUID  # US-064: obligatorio en creación.
    status: Literal["open", "in_progress", "resolved", "closed"] = "open"


class IssueUpdate(BaseModel):
    title: OptionalTitleStr = None
    description: str | None = None
    # ENH-054: type editable (action / issue / decision) post-creación.
    type: Literal["action", "issue", "decision"] | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    # ENH-054: reported_at editable post-creación (datetime).
    reported_at: datetime | None = None
    committed_date: date | None = None
    owner_id: UUID | None = None
    owner_actor_id: UUID | None = None
    area_id: UUID | None = None  # US-064: permite asignar a legacy.
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None
    resolution: str | None = None


class IssueRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    description: str | None
    type: str
    priority: int | None
    committed_date: date | None
    resolution: str | None
    status: str
    owner_id: UUID | None
    owner_actor_id: UUID | None = None
    owner: UserMini | None = None  # BUG-035: nombre del responsable.
    # ENH-175: responsable resuelto (Actor con fallback a Usuario).
    responsible_name: str | None = None
    area_id: UUID | None
    area: AreaMini | None = None
    reported_at: datetime | None = None
    comments: list = []

    model_config = {"from_attributes": True}


class IssueComment(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


# ---------- Change Requests ----------
class ChangeRequestCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    type: Literal["scope", "time", "cost", "resource"]
    impact: str | None = None


class ChangeRequestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    impact: str | None = None
    # ENH-112: `cancelled` agregado para el flujo de cancelación de cambios.
    status: Literal["in_review", "approved", "rejected", "implemented", "cancelled"] | None = None


class ChangeRequestRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    description: str | None
    type: str
    impact: str | None
    status: str
    requested_by: UUID | None
    requested_at: datetime
    approved_by: UUID | None
    approved_at: datetime | None
    # ENH-039: usuarios resueltos para que la UI muestre nombres en
    # vez de UUIDs.
    requester: UserMini | None = None
    approver: UserMini | None = None

    model_config = {"from_attributes": True}


# ---------- Documents ----------
# US-020: categorías extendidas — el charter, export RAID, transcripts
# y minutas ahora tienen su propia clasificación para filtrado y UI.
DocumentCategory = Literal[
    "charter",
    "plan",
    "raid_export",
    "transcript",
    "minute",
    "report",
    "lesson",
    "contract",
    "other",
]

DOCUMENT_CATEGORIES: tuple[str, ...] = (
    "charter",
    "plan",
    "raid_export",
    "transcript",
    "minute",
    "report",
    "lesson",
    "contract",
    "other",
)


class DocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    category: DocumentCategory | None = "other"
    file_url: str
    mime_type: str
    size_bytes: int = Field(ge=0)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    category: DocumentCategory | None = None


class DocumentRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    description: str | None
    category: str | None
    file_url: str | None
    mime_type: str | None
    size_bytes: int | None
    version: int
    is_current: bool
    status: str

    model_config = {"from_attributes": True}


# ---------- Lessons ----------
class LessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    category: Literal["success", "improvement", "error"]
    phase: str | None = None
    recommendation: str | None = None
    tags: list[str] = []
    owner_actor_id: UUID | None = None


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    category: Literal["success", "improvement", "error"] | None = None
    phase: str | None = None
    recommendation: str | None = None
    tags: list[str] | None = None
    owner_actor_id: UUID | None = None


class LessonRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    description: str | None
    category: str | None
    phase: str | None
    recommendation: str | None
    tags: list[str] = []
    status: str
    owner_actor_id: UUID | None = None

    model_config = {"from_attributes": True}


# ---------- Meeting Minutes ----------
class MeetingMinuteCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    meeting_date: datetime
    participants: list[dict] = []
    topics: list[dict] = []
    agreements: list[dict] = []
    # BUG-063: resumen editable (2-3 oraciones) — persiste en
    # `MeetingMinute.description`. El IA lo llena al generar; el PM lo
    # edita en el preview antes de guardar.
    summary: str | None = Field(default=None, max_length=5000)
    # BUG-063: notas libres editables al final de la minuta. Persiste en
    # `raid_suggestions._meta.free_notes` para evitar migración.
    free_notes: str | None = Field(default=None, max_length=10000)
    next_meeting_date: date | None = None
    attachments: list[dict] = []
    transcript_file_id: str | None = None
    generated_by_ai: bool = False
    # ENH-106: origen de la minuta (audit-only). Default `manual`.
    # `transcript_ai` lo setea el worker de IA, no el cliente; aceptamos
    # los 4 valores en el schema para consistencia con el campo en DB.
    origin: Literal["manual", "transcript_ai", "import_file", "import_paste"] = "manual"
    # BUG-058: el flujo "Previsualizar → Guardar como minuta" perdía
    # las sugerencias RAID detectadas por el LLM al persistirlas.
    # Aceptamos el shape persistible {risks/issues/lessons/changes}.
    raid_suggestions: dict = Field(default_factory=dict)
    # BUG-061: al guardar la minuta desde el preview IA, los items RAID
    # marcados `status="pending"` se convierten en tickets reales en la
    # misma transacción. Items con `status="discarded"` (desmarcados por
    # el PM en el preview) NO se crean. Default `True` para no romper
    # llamadas manuales que ya tenían un POST seguido de approve.
    auto_approve_raid: bool = True


class MeetingMinuteRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    meeting_date: datetime
    participants: list
    topics: list
    agreements: list
    # BUG-063: resumen (2-3 oraciones) persistido en `description`.
    description: str | None = None
    next_meeting_date: date | None
    attachments: list
    generated_by_ai: bool
    # ENH-106: origen de la minuta (audit-only). No se renderiza en
    # exports; visible solo en admin/audit-log.
    origin: str = "manual"
    status: str
    # US-108: sugerencias RAID detectadas por el LLM con su estado
    # actual de revisión (pending / approved / discarded).
    raid_suggestions: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class MeetingMinuteUpdate(BaseModel):
    """ENH-090/US-108/ENH-095/BUG-063: edición ligera de una minuta —
    usado para persistir cambios en `raid_suggestions` (descartar, editar
    short_desc) y, desde ENH-095, también las secciones estructuradas
    (participants/topics/agreements) editables inline en el preview.
    BUG-063: también summary y meeting_date editables.
    """

    title: str | None = Field(default=None, min_length=2, max_length=200)
    summary: str | None = Field(default=None, max_length=5000)
    meeting_date: datetime | None = None
    raid_suggestions: dict | None = None
    # ENH-095: edición por secciones desde el preview.
    participants: list[dict] | None = None
    topics: list[dict] | None = None
    agreements: list[dict] | None = None
    free_notes: str | None = Field(default=None, max_length=10000)


class RaidApproveItem(BaseModel):
    """US-108 + BUG-063: el PM aprueba un item RAID sugerido y lo convierte
    en ticket real. `index` es la posición en el array
    `raid_suggestions[type]`. `override` permite editar `short_desc` /
    `description` / `priority` antes de crear el ticket.

    Shape canónico A/R/D/I (actions/risks/decisions/issues). Lecciones y
    cambios se mantienen para retro-compat con minutas previas al
    refactor pero el LLM ya no los emite (owner 2026-05-22).
    """

    type: Literal[
        "actions", "risks", "decisions", "issues",
        "lessons", "changes",
    ]
    index: int
    short_desc: str | None = None
    description: str | None = None
    priority: int | None = None


class RaidApproveBatch(BaseModel):
    items: list[RaidApproveItem] = Field(min_length=1)
