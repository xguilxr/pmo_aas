"""Schemas del Project Charter (US-012, EP003).

El charter se compone de 4 secciones:
- 1: Info general (nombre, descripción, org/BU/depto)
- 2: Stakeholders (sponsor, líder negocio, líder técnico, PM)
- 3: Clasificación (tipo, prioridad, objetivo, alcance, etc.)
- 4: Datos de gestión — **derivados dinámicamente** desde `projects` y no
  persisten en esta tabla (ver DEC-008).
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ENH-081 CA3: lista configurable de campos requeridos para considerar el
# charter "completo". Si alguno está vacío, la UI muestra banner de aviso.
# Se mantiene en backend (no en BD) para iterar rápido sin migración —
# cuando el set se vuelva sensible al tenant, mover a `tenant_settings`.
CHARTER_REQUIRED_FIELDS: tuple[str, ...] = (
    "project_name",
    "description",
    "sponsor",
    "objective",
    "scope",
    "project_type",
    "priority",
)


class CharterCompleteness(BaseModel):
    is_complete: bool
    missing_fields: list[str]
    required_fields: list[str]


class CharterSection4(BaseModel):
    """Datos de gestión derivados del proyecto al consultar."""

    start_date: date | None = None
    estimated_end_date: date | None = None
    phase: str | None = None
    health_status: str | None = None
    progress: int | None = None
    planned_progress: int | None = None
    assigned_budget: Decimal | None = None
    used_budget: Decimal | None = None
    assigned_hours: Decimal | None = None
    consumed_hours: Decimal | None = None


class ProjectCharterUpdate(BaseModel):
    # Sección 1
    project_name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    portfolio_id: UUID | None = None
    program_id: UUID | None = None
    # Sección 2
    sponsor: str | None = None
    sponsor_email: EmailStr | None = None
    business_leader: str | None = None
    business_leader_email: EmailStr | None = None
    tech_leader: str | None = None
    tech_leader_email: EmailStr | None = None
    # Sección 3
    project_type: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    objective: str | None = None
    restrictions: str | None = None
    risks_summary: str | None = None
    scope: str | None = None
    key_people: str | None = None
    benefits: str | None = None


class ProjectCharterRead(BaseModel):
    id: UUID
    project_id: UUID
    request_id: UUID | None = None

    # Sección 1
    project_name: str
    description: str | None
    organization_id: UUID | None
    portfolio_id: UUID | None
    program_id: UUID | None

    # Sección 2
    sponsor: str | None
    sponsor_email: str | None
    business_leader: str | None
    business_leader_email: str | None
    tech_leader: str | None
    tech_leader_email: str | None
    pm_id: UUID | None

    # Sección 3
    project_type: str | None
    priority: int | None
    objective: str | None
    restrictions: str | None
    risks_summary: str | None
    scope: str | None
    key_people: str | None
    benefits: str | None

    # Sección 4: derivada (sólo lectura)
    section_4: CharterSection4

    # ENH-081 CA3: completeness contra `CHARTER_REQUIRED_FIELDS`.
    completeness: CharterCompleteness

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
