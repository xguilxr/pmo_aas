"""US-115 — schemas para project_participations + project_roles."""
from datetime import date, datetime
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


class ParticipationUpdate(BaseModel):
    operational_team_id: UUID | None = None
    project_role_id: UUID | None = None
    functional_area_id: UUID | None = None
    is_area_lead: bool | None = None
    is_primary: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


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
    created_at: datetime
    # Hidratado opcional (?include=actor).
    actor: ActorMini | None = None
