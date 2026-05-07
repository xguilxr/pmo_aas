"""Schemas para Áreas → Equipos → Actores (catálogo tenant) — US-097."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------- Area ----------
class AreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    lead_name: str | None = Field(default=None, max_length=200)
    is_active: bool = True


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    lead_name: str | None = None
    is_active: bool | None = None


class AreaRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    lead_name: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Team ----------
class TeamCreate(BaseModel):
    area_id: UUID
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class TeamUpdate(BaseModel):
    area_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class TeamRead(BaseModel):
    id: UUID
    tenant_id: UUID
    area_id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Actor ----------
class ActorCreate(BaseModel):
    team_id: UUID | None = None
    user_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True


class ActorUpdate(BaseModel):
    team_id: UUID | None = None
    user_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    is_active: bool | None = None


class ActorRead(BaseModel):
    id: UUID
    tenant_id: UUID
    team_id: UUID | None
    user_id: UUID | None
    name: str
    email: str | None
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Tree ----------
class TreeActor(BaseModel):
    id: UUID
    name: str
    email: str | None
    phone: str | None
    user_id: UUID | None
    is_active: bool

    model_config = {"from_attributes": True}


class TreeTeam(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    actors: list[TreeActor] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TreeArea(BaseModel):
    id: UUID
    name: str
    description: str | None
    lead_name: str | None = None
    is_active: bool
    teams: list[TreeTeam] = Field(default_factory=list)
    unassigned_actors: list[TreeActor] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AreaTreeResponse(BaseModel):
    areas: list[TreeArea]
    orphan_actors: list[TreeActor] = Field(default_factory=list)


# ---------- Actor reassign (US-099) ----------
class ActorReassignBody(BaseModel):
    target_actor_id: UUID
    scopes: list[str] = Field(default_factory=lambda: ["tasks"])
    deactivate_source: bool = True


class ActorReassignResponse(BaseModel):
    tasks_moved: int
    raid_moved: int = 0
    minutes_moved: int = 0
    source_deactivated: bool
