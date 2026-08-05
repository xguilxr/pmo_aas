from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

#: D-2 / ADR-019 — las cuatro fases del proyecto.
#:
#: `hypercare` era `support` hasta el 2026-08-05. El nombre viejo se lee como
#: «mesa de ayuda», que es una función permanente; la fase es acompañamiento
#: acotado tras la puesta en marcha, y una forma de cierre.
ProjectPhase = Literal["planning", "execution", "hypercare", "closed"]

#: Ventana de compatibilidad. Un cliente que todavía mande `support` —una
#: pestaña abierta desde antes del despliegue, un filtro guardado, un script—
#: sigue funcionando y su valor se guarda ya como `hypercare`. Se quita cuando
#: no queden clientes viejos; hasta entonces, romperlos sería cobrarle al
#: usuario un cambio de vocabulario que no pidió.
_FASES_RENOMBRADAS = {"support": "hypercare"}


def normalizar_fase(valor: object) -> object:
    """Traduce el nombre viejo de la fase al canónico. Lo demás pasa igual."""
    return _FASES_RENOMBRADAS.get(valor, valor) if isinstance(valor, str) else valor


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1)
    type: Literal["innovation", "transformation", "operation", "bau"]
    priority: int = Field(ge=1, le=5)
    organization_id: UUID
    program_id: UUID | None = None
    phase: ProjectPhase = "planning"

    _fase_compat = field_validator("phase", mode="before")(normalizar_fase)
    pm_id: UUID
    sponsor: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date debe ser > start_date")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    type: Literal["innovation", "transformation", "operation", "bau"] | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    program_id: UUID | None = None
    pm_id: UUID | None = None
    sponsor: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    actual_budget: Decimal | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    # US-180: editar health_status por este PATCH genérico equivale a una
    # declaración manual (health_source='manual', sin razón). El flujo
    # recomendado es PATCH /projects/{id}/health (razón obligatoria en
    # amarillo/rojo y opción de volver a 'auto').
    health_status: Literal["green", "yellow", "red"] | None = None


class ProjectRead(BaseModel):
    id: UUID
    folio: str
    name: str
    description: str | None
    type: str | None
    priority: int | None
    phase: str
    organization_id: UUID
    program_id: UUID | None
    pm_id: UUID | None
    sponsor: str | None
    start_date: date | None
    end_date: date | None
    budget: Decimal | None
    actual_budget: Decimal | None
    progress: int
    health_status: str
    # US-180: salud única híbrida — fuente del semáforo + razón declarada.
    health_source: Literal["auto", "manual"] = "auto"
    health_reason: str | None = None
    request_id: UUID | None = None
    # US-084: campos del plan agregados con prioridad manual.
    manually_edited_fields: dict = {}

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectRead):
    members: list[dict] = []
    module_counts: dict[str, int] = {}
    # ENH-129: KPIs de tareas para el gauge de Avance del Resumen.
    # Claves: milestones_total, milestones_done, critical_total,
    # critical_done, overdue.
    task_kpis: dict[str, int] = {}


class ActivityItem(BaseModel):
    """US-149: evento del audit log para el feed de actividad del proyecto."""

    id: int
    action: str
    module: str | None = None
    occurred_at: datetime
    user_id: UUID | None = None
    user_name: str | None = None
    details: dict = {}


class PhaseChange(BaseModel):
    new_phase: ProjectPhase

    _fase_compat = field_validator("new_phase", mode="before")(normalizar_fase)
    comment: str | None = None


class HealthDeclare(BaseModel):
    """US-180 — declarar el semáforo (override manual) o volver a 'auto'.

    `status=None` regresa la salud a fuente automática (el motor de reglas
    recalcula de inmediato). En amarillo/rojo la razón es obligatoria.
    """

    status: Literal["green", "yellow", "red"] | None = None
    reason: str | None = Field(default=None, max_length=2000)


# US-191 — evaluación periódica de salud (5 dimensiones + overall).
RagColor = Literal["green", "yellow", "red"]


class HealthEvaluationCreate(BaseModel):
    """Cada guardado es un punto en la historia (fecha libre, default
    hoy). Las dimensiones son opcionales; el overall (la "sexta") es
    obligatorio y se aplica al semáforo del proyecto como declaración
    manual — en amarillo/rojo la nota es obligatoria (regla US-180)."""

    evaluated_at: date | None = None
    schedule: RagColor | None = None
    budget: RagColor | None = None
    risks: RagColor | None = None
    decisions: RagColor | None = None
    resources: RagColor | None = None
    overall: RagColor
    note: str | None = Field(default=None, max_length=2000)


class HealthEvaluationRead(BaseModel):
    id: UUID
    project_id: UUID
    evaluated_at: date
    schedule: str | None
    budget: str | None
    risks: str | None
    decisions: str | None
    resources: str | None
    overall: str
    note: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberCreate(BaseModel):
    user_id: UUID
    role_in_project: Literal["pm", "team", "viewer", "stakeholder"] = "team"
