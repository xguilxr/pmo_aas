from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

# BUG-068: los logos pueden ser una URL externa corta o un data-URL base64 de
# un archivo subido (PNG/JPG/SVG/WEBP). Cap generoso (~3 MB de texto, suficiente
# para una imagen de 2 MB codificada) para no rechazar uploads legítimos.
_LOGO_MAX = 3_000_000


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    reason_social: str | None = None
    industry: str | None = None
    country: str | None = None
    contact_email: str | None = None
    logo_url: str | None = Field(default=None, max_length=_LOGO_MAX)
    # ENH-100: logo del cliente (consumido por EP020 Report Builder).
    client_logo_url: str | None = Field(default=None, max_length=_LOGO_MAX)
    is_active: bool = True


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    reason_social: str | None = None
    industry: str | None = None
    country: str | None = None
    contact_email: str | None = None
    logo_url: str | None = Field(default=None, max_length=_LOGO_MAX)
    # ENH-100
    client_logo_url: str | None = Field(default=None, max_length=_LOGO_MAX)
    is_active: bool | None = None


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    reason_social: str | None
    industry: str | None
    country: str | None
    contact_email: str | None
    logo_url: str | None
    # ENH-100
    client_logo_url: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class OrganizationPanelHealth(BaseModel):
    green: int = 0
    yellow: int = 0
    red: int = 0


class OrganizationPanel(BaseModel):
    id: UUID
    name: str
    logo_url: str | None
    industry: str | None
    country: str | None
    is_active: bool
    business_unit_count: int = 0
    department_count: int = 0
    program_count: int = 0
    active_project_count: int = 0
    portfolio_health: OrganizationPanelHealth = Field(
        default_factory=OrganizationPanelHealth
    )

    model_config = {"from_attributes": True}


# ---- US-033: Detalle de recursos reales por organización ----

class OrgPanelDepartment(BaseModel):
    id: UUID
    business_unit_id: UUID
    name: str
    is_active: bool


class OrgPanelBusinessUnit(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_active: bool
    departments: list[OrgPanelDepartment] = Field(default_factory=list)


class OrgPanelProgram(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_active: bool
    active_project_count: int = 0


class OrgPanelProject(BaseModel):
    id: UUID
    folio: str | None
    name: str
    phase: str | None
    health_status: str | None
    program_id: UUID | None
    pm_id: UUID | None
    pm_name: str | None = None


class OrgPanelUser(BaseModel):
    id: UUID
    full_name: str | None
    email: str | None
    role: str  # role in the org panel context: "pm" | "team" | "viewer"


class OrganizationPanelDetail(BaseModel):
    id: UUID
    name: str
    reason_social: str | None = None
    industry: str | None = None
    country: str | None = None
    contact_email: str | None = None
    logo_url: str | None = None
    # ENH-100
    client_logo_url: str | None = None
    is_active: bool
    business_units: list[OrgPanelBusinessUnit] = Field(default_factory=list)
    programs: list[OrgPanelProgram] = Field(default_factory=list)
    projects: list[OrgPanelProject] = Field(default_factory=list)
    users: list[OrgPanelUser] = Field(default_factory=list)


class BusinessUnitCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_active: bool = True


class BusinessUnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class BusinessUnitRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class DepartmentRead(BaseModel):
    id: UUID
    business_unit_id: UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    organization_id: UUID
    description: str | None = None
    strategic_alignment: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    strategic_alignment: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class ProgramRead(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    description: str | None
    strategic_alignment: str | None
    start_date: date | None
    end_date: date | None
    is_active: bool

    model_config = {"from_attributes": True}


# ---- US-034: Program summary ----

class ProgramSummaryProject(BaseModel):
    id: UUID
    folio: str | None
    name: str
    phase: str | None
    health_status: str | None
    pm_id: UUID | None
    pm_name: str | None = None
    progress: int = 0
    budget: float = 0
    actual_budget: float = 0


class ProgramSummaryRisk(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str | None = None
    folio: str | None
    title: str
    severity: int | None
    status: str


class ProgramSummary(BaseModel):
    id: UUID
    name: str
    description: str | None
    organization_id: UUID
    organization_name: str | None = None
    is_active: bool
    start_date: date | None
    end_date: date | None
    project_total: int = 0
    project_active: int = 0
    project_at_risk: int = 0
    project_closed: int = 0
    health: OrganizationPanelHealth = Field(default_factory=OrganizationPanelHealth)
    budget_planned: float = 0
    budget_actual: float = 0
    # BUG-092 — el desglose por moneda. Los dos escalares de arriba valen 0
    # cuando el programa mezcla monedas, porque ahí no hay un total que dar; el
    # desglose siempre está y es el que la pantalla pinta.
    budget_planned_by_currency: dict[str, float] = {}
    budget_actual_by_currency: dict[str, float] = {}
    projects: list[ProgramSummaryProject] = Field(default_factory=list)
    top_risks: list[ProgramSummaryRisk] = Field(default_factory=list)


class TenantProvisionRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9\-]+$")
    admin_email: str = Field(min_length=3, max_length=200)
    admin_password: str | None = None
    admin_full_name: str = Field(min_length=2, max_length=200)
    admin_username: str | None = Field(default=None, max_length=64)


class TenantProvisionResponse(BaseModel):
    tenant_id: UUID
    slug: str
    admin_user_id: UUID
    admin_password: str


class TenantRead(BaseModel):
    id: UUID
    slug: str
    name: str
    is_active: bool
    user_count: int = 0
    organization_count: int = 0
    program_count: int = 0
    project_count: int = 0

    model_config = {"from_attributes": True}
