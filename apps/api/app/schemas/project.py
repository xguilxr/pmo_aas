from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1)
    type: Literal["innovation", "transformation", "operation", "bau"]
    priority: int = Field(ge=1, le=5)
    organization_id: UUID
    program_id: UUID | None = None
    phase: Literal["planning", "execution", "support", "closed"] = "planning"
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
    health_status: Literal["green", "yellow", "red"] | None = None
    # ENH-101: declarative RAG override (PM manual). Use sentinel
    # "__unset__" semantics: omit = no change; explicit null = clear.
    status_rag: Literal["green", "amber", "red"] | None = None


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
    # ENH-101: declarative RAG (override del PM). None = sin override.
    status_rag: Literal["green", "amber", "red"] | None = None
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


class PhaseChange(BaseModel):
    new_phase: Literal["planning", "execution", "support", "closed"]
    comment: str | None = None


class MemberCreate(BaseModel):
    user_id: UUID
    role_in_project: Literal["pm", "team", "viewer", "stakeholder"] = "team"
