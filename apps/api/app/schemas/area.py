"""Schemas para Áreas → Equipos → Actores (catálogo tenant) — US-097."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------- Area ----------
class AreaLeadInput(BaseModel):
    """ENH-078: input de líder al crear/editar un Área.

    Si `actor_id` se pasa, se reusa el Actor existente y se marca
    `is_lead=true`. Si se pasa `name`, se crea un Actor nuevo (sin
    team) con `is_lead=true` y se enlaza.
    """

    actor_id: UUID | None = None
    name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)


class AreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True
    lead: AreaLeadInput | None = None
    # BUG-061: si se pasa, el área queda scoped a esa organización.
    # Si se omite/None, el área es tenant-global.
    organization_id: UUID | None = None
    # BUG-085: scope de creación. Cuando un área se crea desde un proyecto
    # (o programa), el backend deriva la organización del proyecto/programa
    # y crea el AreaAssignment del scope correcto (proyecto/programa/org)
    # para que el área quede visible y se propague hacia los hijos sin que
    # el frontend tenga que conocer el organization_id. Exactamente uno de
    # {project_id, program_id, organization_id} debe venir.
    project_id: UUID | None = None
    program_id: UUID | None = None


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None
    lead_actor_id: UUID | None = None
    # BUG-061: permite mover un área entre orgs o convertirla en global
    # (pasar explícitamente null no se distingue de "no enviar" en
    # exclude_unset; el endpoint trata `organization_id` con
    # `model_dump(exclude_unset=True)` para distinguir).
    organization_id: UUID | None = None


class AreaRead(BaseModel):
    id: UUID
    tenant_id: UUID
    organization_id: UUID | None = None
    name: str
    description: str | None
    lead_actor_id: UUID | None = None
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

# US-182: clasificación del recurso (pool con capacidad).
ResourceType = Literal[
    "cliente_negocio", "cliente_it", "e4_pmo", "e4_tecnologia", "vendor_externo"
]
PortfolioFunction = Literal[
    "pm", "pmo", "arquitectura", "infraestructura", "aplicaciones", "datos",
    "seguridad", "integraciones", "negocio", "change", "testing", "vendor",
]
Seniority = Literal["junior", "mid", "senior", "lead"]
ScarcityLevel = Literal["alta", "media", "baja"]


class _ActorResourceFields(BaseModel):
    """US-182 — campos del pool de recursos (compartidos create/update)."""

    organization_id: UUID | None = None
    resource_type: ResourceType | None = None
    portfolio_function: PortfolioFunction | None = None
    seniority: Seniority | None = None
    scarcity_level: ScarcityLevel | None = None
    location: str | None = Field(default=None, max_length=100)
    skills_tags: list[str] | None = None
    nominal_capacity_pct: float | None = Field(default=None, ge=0, le=100)
    project_capacity_pct: float | None = Field(default=None, ge=0, le=100)
    is_key_resource: bool | None = None
    is_shared_resource: bool | None = None
    fte_cost_rate: float | None = Field(default=None, ge=0)


class ActorCreate(_ActorResourceFields):
    team_id: UUID | None = None
    # ENH-084 rework: área directa (sin team).
    area_id: UUID | None = None
    user_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    is_lead: bool = False
    # US-114: enriquecimiento.
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    manager_actor_id: UUID | None = None


class ActorUpdate(_ActorResourceFields):
    team_id: UUID | None = None
    area_id: UUID | None = None
    user_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    is_active: bool | None = None
    is_lead: bool | None = None
    company: str | None = None
    job_title: str | None = None
    manager_actor_id: UUID | None = None


class ActorRead(BaseModel):
    id: UUID
    tenant_id: UUID
    team_id: UUID | None
    area_id: UUID | None = None
    user_id: UUID | None
    name: str
    email: str | None
    phone: str | None
    is_active: bool
    is_lead: bool = False
    company: str | None = None
    job_title: str | None = None
    manager_actor_id: UUID | None = None
    # US-182: pool de recursos con capacidad.
    organization_id: UUID | None = None
    resource_type: str | None = None
    portfolio_function: str | None = None
    seniority: str | None = None
    scarcity_level: str | None = None
    location: str | None = None
    skills_tags: list[str] = []
    nominal_capacity_pct: float = 100
    project_capacity_pct: float = 100
    is_key_resource: bool = False
    is_shared_resource: bool = True
    fte_cost_rate: float | None = None
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
    is_lead: bool = False
    # ENH-084 rework: expone area_id/team_id para que el frontend
    # pueda hidratar el modal de edit con la asignación actual.
    team_id: UUID | None = None
    area_id: UUID | None = None

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
    organization_id: UUID | None = None
    name: str
    description: str | None
    lead_actor_id: UUID | None = None
    is_active: bool
    teams: list[TreeTeam] = Field(default_factory=list)
    unassigned_actors: list[TreeActor] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AreaTreeResponse(BaseModel):
    areas: list[TreeArea]
    orphan_actors: list[TreeActor] = Field(default_factory=list)


# ---------- Area assignments (US-103) ----------
class AreaAssignmentRead(BaseModel):
    id: UUID
    area_id: UUID
    organization_id: UUID | None
    program_id: UUID | None
    project_id: UUID | None
    is_global: bool
    created_at: datetime
    # ENH-080: nombres legibles para mostrar en el dropdown de Admin/Áreas
    # sin obligar al frontend a hacer N batch-fetches por área. Resueltos
    # en el endpoint via join.
    organization_name: str | None = None
    program_name: str | None = None
    project_name: str | None = None

    model_config = {"from_attributes": True}


class AssignmentScope(BaseModel):
    """Item de scope: exactamente uno de los IDs setteado, o is_global."""

    organization_id: UUID | None = None
    program_id: UUID | None = None
    project_id: UUID | None = None
    is_global: bool = False


class AreaAssignmentSetBody(BaseModel):
    """PUT /admin/areas/{id}/assignments — reemplaza el set completo."""

    scopes: list[AssignmentScope] = Field(default_factory=list)


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
