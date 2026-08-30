from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from app.core.compatibilidad import registrar_uso
from app.dominio.moneda import resolver as resolver_moneda
from app.dominio.proyecto import FASES_RENOMBRADAS, TIPOS_RENOMBRADOS
from app.dominio.proyecto import FASES_TERMINALES as FASES_TERMINALES_DOMINIO

#: US-202 / ADR-038 — las cinco fases, en el vocabulario del producto. El
#: catálogo, el orden, las transiciones y las etiquetas viven en
#: `dominio/proyecto.py`; aquí solo está la forma que valida Pydantic.
#:
#: Se escribe literal y no derivado de `FASES` porque `Literal` **exige**
#: literales: `Literal[*FASES]` no es válido. Que las dos listas no se separen lo
#: sostiene una prueba (`test_us202_vocabulario.py`), igual que hace `Moneda` con
#: `dominio.moneda.MONEDAS`.
ProjectPhase = Literal["preparacion", "ejecucion", "hypercare", "cerrado", "cancelado"]

#: US-202 — el tipo deja de ser texto libre. Cuatro valores; el que necesita un
#: quinto está describiendo otra cosa (ver `dominio/proyecto.py`).
ProjectType = Literal["transformacion", "operacion", "innovacion", "bau"]

#: Se reexporta para no romper a quien ya lo importaba de aquí. La definición
#: está en el dominio.
FASES_TERMINALES = FASES_TERMINALES_DOMINIO


_DONDE_FASE = "fase del proyecto"

#: Un `registrar_uso` **literal** por nombre retirado, y no un
#: `registrar_uso(MAPA[valor])`. Cinco líneas en vez de una a propósito: el
#: trinquete de `test_ventanas_compatibilidad.py` busca la clave literal en el
#: código, y con razón — la pregunta que alguien se hace dentro de dos meses es
#: «¿quién registra `phase=planning`?», y una indirección no la contesta.
#:
#: Cinco contadores y no uno: el cliente que manda `planning` no es
#: necesariamente el que manda `cancelled`, así que sus ventanas llegan a cero en
#: momentos distintos y se cierran por separado.
_AVISAR_FASE: dict[str, Callable[[str], None]] = {
    "planning": lambda donde: registrar_uso("phase=planning", donde=donde),
    "execution": lambda donde: registrar_uso("phase=execution", donde=donde),
    "support": lambda donde: registrar_uso("phase=support", donde=donde),
    "closed": lambda donde: registrar_uso("phase=closed", donde=donde),
    "cancelled": lambda donde: registrar_uso("phase=cancelled", donde=donde),
}


def normalizar_fase(valor: object, *, donde: str = _DONDE_FASE) -> object:
    """Traduce el nombre viejo de la fase al canónico. Lo demás pasa igual.

    `donde` es la puerta por la que entró: el cuerpo lo manda un cliente que se
    actualiza, pero un filtro guardado en un marcador sobrevive años, así que las
    dos no se cierran a la vez. Sólo por palabra clave para no confundirse con la
    `ValidationInfo` que Pydantic pasaría en el segundo posicional.
    """
    if not isinstance(valor, str):
        return valor
    canonico = FASES_RENOMBRADAS.get(valor)
    if canonico is None:
        return valor
    _AVISAR_FASE[valor](donde)
    return canonico


def normalizar_tipo(valor: object) -> object:
    """Traduce el tipo en inglés al canónico. Lo demás pasa igual.

    Un solo contador para los tres nombres (`project_type_libre`): salían del
    mismo enum, así que se actualizan y se cierran juntos. Un valor que no esté
    en el mapa **no** se traduce ni se registra aquí: lo rechaza el enum, que es
    lo correcto — el texto libre de antes de US-202 se lee (la columna sigue
    siendo texto) pero no se vuelve a escribir.
    """
    if not isinstance(valor, str):
        return valor
    canonico = TIPOS_RENOMBRADOS.get(valor)
    if canonico is None:
        return valor
    registrar_uso("project_type_libre", donde="tipo del proyecto")
    return canonico


#: Los códigos admitidos, atados a `dominio.moneda.MONEDAS` por una prueba:
#: el desplegable, la validación y la presentación no pueden divergir.
Moneda = Literal["MXN", "USD", "EUR"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1)
    type: ProjectType
    _tipo_compat = field_validator("type", mode="before")(normalizar_tipo)
    priority: int = Field(ge=1, le=5)
    organization_id: UUID
    program_id: UUID | None = None
    #: US-199 — el portafolio del proyecto. Con `program_id` puesto se
    #: autocompleta con el del programa y un valor contradictorio se rechaza
    #: (`services/jerarquia.py`).
    portfolio_id: UUID | None = None
    phase: ProjectPhase = "preparacion"

    _fase_compat = field_validator("phase", mode="before")(normalizar_fase)
    pm_id: UUID
    sponsor: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    # BUG-092 — la moneda del presupuesto, por proyecto. Nulo = la preferida
    # del inquilino; se resuelve en `dominio.moneda.resolver`, no aquí.
    currency: Moneda | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date debe ser > start_date")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    type: ProjectType | None = None
    _tipo_compat = field_validator("type", mode="before")(normalizar_tipo)
    priority: int | None = Field(default=None, ge=1, le=5)
    program_id: UUID | None = None
    #: US-199 — mover el proyecto de portafolio. Si además cambia el programa,
    #: los dos tienen que ser coherentes.
    portfolio_id: UUID | None = None
    pm_id: UUID | None = None
    sponsor: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    actual_budget: Decimal | None = None
    currency: Moneda | None = None
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
    portfolio_id: UUID | None = None
    pm_id: UUID | None
    sponsor: str | None
    start_date: date | None
    end_date: date | None
    budget: Decimal | None
    actual_budget: Decimal | None
    # **Resuelta**, no cruda: quien la lea no tiene que saber que el nulo
    # significa «la del inquilino». Un importe que viaja sin unidad es la
    # forma en que esto se rompió la primera vez.
    #
    # Se declara opcional porque la columna lo es, y el validador de abajo se
    # encarga de que nunca salga vacía. La alternativa —resolverla en cada uno
    # de los cinco sitios que serializan un proyecto— es la que garantiza que
    # el sexto se olvide.
    currency: str | None = None
    progress: int
    health_status: str
    # US-180: salud única híbrida — fuente del semáforo + razón declarada.
    health_source: Literal["auto", "manual"] = "auto"
    health_reason: str | None = None
    request_id: UUID | None = None
    # US-084: campos del plan agregados con prioridad manual.
    manually_edited_fields: dict = {}

    model_config = {"from_attributes": True}


    @model_validator(mode="after")
    def _resolver_moneda(self, info: ValidationInfo) -> "ProjectRead":
        """La moneda efectiva del proyecto, resuelta antes de salir.

        `context={"moneda_preferida": …}` lo pone quien serializa. Si no lo
        pone, cae a la del producto en vez de devolver `null`: un importe sin
        unidad es peor que uno con la unidad por defecto, y este campo existe
        justamente porque antes salían sin ninguna.
        """
        preferida = (info.context or {}).get("moneda_preferida")
        self.currency = resolver_moneda(self.currency, preferida)
        return self

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
