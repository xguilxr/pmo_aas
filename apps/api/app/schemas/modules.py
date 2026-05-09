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
    owner: UserMini | None = None  # BUG-035: nombre del responsable.
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
    owner: UserMini | None = None  # BUG-035: nombre del responsable.
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
    status: Literal["in_review", "approved", "rejected", "implemented"] | None = None


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


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    category: Literal["success", "improvement", "error"] | None = None
    phase: str | None = None
    recommendation: str | None = None
    tags: list[str] | None = None


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

    model_config = {"from_attributes": True}


# ---------- Meeting Minutes ----------
class MeetingMinuteCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    meeting_date: datetime
    participants: list[dict] = []
    topics: list[dict] = []
    agreements: list[dict] = []
    next_meeting_date: date | None = None
    attachments: list[dict] = []
    transcript_file_id: str | None = None
    generated_by_ai: bool = False
    # BUG-058: el flujo "Previsualizar → Guardar como minuta" perdía
    # las sugerencias RAID detectadas por el LLM al persistirlas.
    # Aceptamos el shape persistible {risks/issues/lessons/changes}.
    raid_suggestions: dict = Field(default_factory=dict)


class MeetingMinuteRead(BaseModel):
    id: UUID
    folio: str
    project_id: UUID
    title: str
    meeting_date: datetime
    participants: list
    topics: list
    agreements: list
    next_meeting_date: date | None
    attachments: list
    generated_by_ai: bool
    status: str
    # US-108: sugerencias RAID detectadas por el LLM con su estado
    # actual de revisión (pending / approved / discarded).
    raid_suggestions: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class MeetingMinuteUpdate(BaseModel):
    """ENH-090/US-108/ENH-095: edición ligera de una minuta — usado para
    persistir cambios en `raid_suggestions` (descartar, editar
    short_desc) y, desde ENH-095, también las secciones estructuradas
    (participants/topics/agreements) editables inline en el preview.
    """

    title: str | None = Field(default=None, min_length=2, max_length=200)
    raid_suggestions: dict | None = None
    # ENH-095: edición por secciones desde el preview.
    participants: list[dict] | None = None
    topics: list[dict] | None = None
    agreements: list[dict] | None = None


class RaidApproveItem(BaseModel):
    """US-108: el PM aprueba un item RAID sugerido y lo convierte en
    ticket real. `index` es la posición en el array `raid_suggestions[type]`.
    `override` permite editar `short_desc` / `description` / `priority`
    antes de crear el ticket.
    """

    type: Literal["risks", "issues", "lessons", "changes"]
    index: int
    short_desc: str | None = None
    description: str | None = None
    priority: int | None = None


class RaidApproveBatch(BaseModel):
    items: list[RaidApproveItem] = Field(min_length=1)
