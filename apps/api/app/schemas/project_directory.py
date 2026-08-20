"""US-115 — schemas para project_participations + project_roles."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class ProjectRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProjectRoleRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


# US-183: asignación con FTE% y ciclo de vida de capacidad.
AssignmentType = Literal["directa", "advisory", "backup", "shared_service", "steerco_only"]
AssignmentStatus = Literal["tentativa", "activa", "cerrada", "cancelada"]
# US-217: el papel RACI de la participación. `None` es válido y frecuente: la
# mayoría no tiene papel asignado, y forzar uno obligaría a inventarlo para
# poder guardar la participación.
RaciPapel = Literal["A", "R", "C", "I"]


class ParticipationCreate(BaseModel):
    actor_id: UUID
    operational_team_id: UUID | None = None
    project_role_id: UUID | None = None
    functional_area_id: UUID | None = None
    is_area_lead: bool = False
    is_primary: bool = False
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True
    # US-183: FTE% asignado (None = sin cuantificar, no suma saturación).
    allocation_pct: float | None = Field(default=None, ge=0, le=100)
    assignment_type: AssignmentType = "directa"
    status: AssignmentStatus = "activa"
    is_critical: bool = False
    phase: str | None = Field(default=None, max_length=32)
    # US-217 — RACI y stakeholder clave.
    raci: RaciPapel | None = None
    is_key_stakeholder: bool = False


class ParticipationUpdate(BaseModel):
    operational_team_id: UUID | None = None
    project_role_id: UUID | None = None
    functional_area_id: UUID | None = None
    is_area_lead: bool | None = None
    is_primary: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    # US-183.
    allocation_pct: float | None = Field(default=None, ge=0, le=100)
    assignment_type: AssignmentType | None = None
    status: AssignmentStatus | None = None
    is_critical: bool | None = None
    phase: str | None = Field(default=None, max_length=32)
    # US-217. `raci` no puede distinguir «no lo mandes» de «ponlo a nulo» con un
    # `None` a secas, así que quitar el papel se pide con la cadena vacía: el
    # `PATCH` lo traduce. Es la misma convención que ya usan los campos de texto
    # opcionales del resto del contrato.
    raci: RaciPapel | Literal[""] | None = None
    is_key_stakeholder: bool | None = None


class ActorMini(BaseModel):
    id: UUID
    name: str
    email: str | None = None
    company: str | None = None
    job_title: str | None = None


class ParticipationRead(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    actor_id: UUID
    operational_team_id: UUID | None
    project_role_id: UUID | None
    functional_area_id: UUID | None
    is_area_lead: bool
    is_primary: bool
    start_date: date | None
    end_date: date | None
    is_active: bool
    # US-183: FTE% y ciclo de vida de capacidad.
    allocation_pct: float | None = None
    assignment_type: str = "directa"
    status: str = "activa"
    is_critical: bool = False
    phase: str | None = None
    # US-217.
    raci: str | None = None
    is_key_stakeholder: bool = False
    created_at: datetime
    # Hidratado opcional (?include=actor).
    actor: ActorMini | None = None
