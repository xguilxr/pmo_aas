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
# US-215: la unidad de tiempo de una tarifa. Se declara aquí y en
# `dominio/costo.py::PERIODOS`; el trinquete de abajo no existe, así que si una
# se amplía la otra tiene que seguirla — están a dos líneas de distancia a
# propósito, y el import cruzado no se hace porque un schema no importa dominio.
PeriodoTarifa = Literal["hora", "dia", "mes"]


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
    # US-215 — no se aceptan al crear. La tarifa se **congela** del catálogo, no
    # se dicta desde el cliente: aceptarla aquí permitiría registrar un costo que
    # no corresponde a ninguna tarifa aprobada, y el snapshot dejaría de ser una
    # copia verificable de algo. Se congela sola si el actor tiene tarifa y
    # periodo; si no, se pide después con `POST .../freeze-cost-rate`.


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
    # US-215 — la tarifa congelada tampoco se edita por aquí. Recongelarla es una
    # acción con intención propia y su propio endpoint, no un campo que se puede
    # tocar de paso al cambiar el área de alguien.


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
    # US-215 — la tarifa congelada, su moneda, su unidad de tiempo y cuándo se
    # congeló. Los cuatro nulos juntos significan «sin tarifa congelada», que no
    # es costo cero (MCS DAT-12).
    cost_rate_snapshot: float | None = None
    cost_currency: str | None = None
    cost_rate_period: str | None = None
    cost_rate_captured_at: datetime | None = None
    #: Lo que cuesta esta asignación con la tarifa congelada, o `None` si falta
    #: cualquiera de los cinco datos que hacen falta. Derivado, no guardado: un
    #: costo almacenado se queda viejo el día que alguien mueve las fechas.
    cost_total: float | None = None
    created_at: datetime
    # Hidratado opcional (?include=actor).
    actor: ActorMini | None = None
