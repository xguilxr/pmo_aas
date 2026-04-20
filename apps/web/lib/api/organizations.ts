import { apiFetch } from "@/lib/api";

export type Organization = {
  id: string;
  name: string;
  reason_social: string | null;
  industry: string | null;
  country: string | null;
  contact_email: string | null;
  logo_url: string | null;
  is_active: boolean;
};

export type OrganizationCreateBody = {
  name: string;
  reason_social?: string | null;
  industry?: string | null;
  country?: string | null;
  contact_email?: string | null;
  is_active?: boolean;
};

export type OrganizationUpdateBody = Partial<OrganizationCreateBody>;

export type ListOrgsParams = {
  q?: string;
  is_active?: boolean;
};

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function listOrganizations(params: ListOrgsParams = {}): Promise<Organization[]> {
  return apiFetch<Organization[]>(`/api/v1/organizations${qs(params)}`);
}

export type OrganizationPanelHealth = {
  green: number;
  yellow: number;
  red: number;
};

export type OrganizationPanel = {
  id: string;
  name: string;
  logo_url: string | null;
  industry: string | null;
  country: string | null;
  is_active: boolean;
  business_unit_count: number;
  department_count: number;
  program_count: number;
  active_project_count: number;
  portfolio_health: OrganizationPanelHealth;
};

export function listOrganizationPanels(
  params: ListOrgsParams = {},
): Promise<OrganizationPanel[]> {
  return apiFetch<OrganizationPanel[]>(`/api/v1/organizations/panels${qs(params)}`);
}

export function getOrganization(id: string): Promise<Organization> {
  return apiFetch<Organization>(`/api/v1/organizations/${id}`);
}

export type OrgPanelDepartment = {
  id: string;
  business_unit_id: string;
  name: string;
  is_active: boolean;
};

export type OrgPanelBusinessUnit = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  departments: OrgPanelDepartment[];
};

export type OrgPanelProgram = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  active_project_count: number;
};

export type OrgPanelProject = {
  id: string;
  folio: string | null;
  name: string;
  phase: string | null;
  health_status: string | null;
  program_id: string | null;
  pm_id: string | null;
  pm_name: string | null;
};

export type OrgPanelUser = {
  id: string;
  full_name: string | null;
  email: string | null;
  role: string;
};

export type OrganizationPanelDetail = {
  id: string;
  name: string;
  reason_social: string | null;
  industry: string | null;
  country: string | null;
  contact_email: string | null;
  logo_url: string | null;
  is_active: boolean;
  business_units: OrgPanelBusinessUnit[];
  programs: OrgPanelProgram[];
  projects: OrgPanelProject[];
  users: OrgPanelUser[];
};

export function getOrganizationPanel(id: string): Promise<OrganizationPanelDetail> {
  return apiFetch<OrganizationPanelDetail>(`/api/v1/organizations/${id}/panel`);
}

export function createOrganization(body: OrganizationCreateBody): Promise<Organization> {
  return apiFetch<Organization>("/api/v1/organizations", { method: "POST", body });
}

export function updateOrganization(
  id: string,
  body: OrganizationUpdateBody,
): Promise<Organization> {
  return apiFetch<Organization>(`/api/v1/organizations/${id}`, { method: "PATCH", body });
}

export function deleteOrganization(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/organizations/${id}`, { method: "DELETE" });
}

export type Program = {
  id: string;
  name: string;
  organization_id: string;
  description: string | null;
  strategic_alignment: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
};

export type ProgramCreateBody = {
  name: string;
  organization_id: string;
  description?: string | null;
  strategic_alignment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ProgramUpdateBody = {
  name?: string;
  description?: string | null;
  strategic_alignment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ListProgramsParams = {
  organization_id?: string;
  is_active?: boolean;
};

export function listPrograms(params: ListProgramsParams = {}): Promise<Program[]> {
  return apiFetch<Program[]>(`/api/v1/programs${qs(params)}`);
}

export type ProgramSummaryProject = {
  id: string;
  folio: string | null;
  name: string;
  phase: string | null;
  health_status: string | null;
  pm_id: string | null;
  pm_name: string | null;
  progress: number;
  budget: number;
  actual_budget: number;
};

export type ProgramSummaryRisk = {
  id: string;
  project_id: string;
  project_name: string | null;
  folio: string | null;
  title: string;
  severity: number | null;
  status: string;
};

export type ProgramSummary = {
  id: string;
  name: string;
  description: string | null;
  organization_id: string;
  organization_name: string | null;
  is_active: boolean;
  start_date: string | null;
  end_date: string | null;
  project_total: number;
  project_active: number;
  project_at_risk: number;
  project_closed: number;
  health: OrganizationPanelHealth;
  budget_planned: number;
  budget_actual: number;
  projects: ProgramSummaryProject[];
  top_risks: ProgramSummaryRisk[];
};

export function getProgramSummary(id: string): Promise<ProgramSummary> {
  return apiFetch<ProgramSummary>(`/api/v1/programs/${id}/summary`);
}

export function createProgram(body: ProgramCreateBody): Promise<Program> {
  return apiFetch<Program>("/api/v1/programs", { method: "POST", body });
}

export function updateProgram(id: string, body: ProgramUpdateBody): Promise<Program> {
  return apiFetch<Program>(`/api/v1/programs/${id}`, { method: "PATCH", body });
}

export function deleteProgram(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/programs/${id}`, { method: "DELETE" });
}

// -- Business Units ----

export type BusinessUnit = {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
};

export type BusinessUnitCreateBody = {
  name: string;
  description?: string | null;
  is_active?: boolean;
};

export type BusinessUnitUpdateBody = Partial<BusinessUnitCreateBody>;

export function listBusinessUnits(
  organizationId: string,
  params: { q?: string; is_active?: boolean } = {},
): Promise<BusinessUnit[]> {
  return apiFetch<BusinessUnit[]>(
    `/api/v1/organizations/${organizationId}/business-units${qs(params)}`,
  );
}

export function createBusinessUnit(
  organizationId: string,
  body: BusinessUnitCreateBody,
): Promise<BusinessUnit> {
  return apiFetch<BusinessUnit>(
    `/api/v1/organizations/${organizationId}/business-units`,
    { method: "POST", body },
  );
}

export function updateBusinessUnit(
  id: string,
  body: BusinessUnitUpdateBody,
): Promise<BusinessUnit> {
  return apiFetch<BusinessUnit>(`/api/v1/business-units/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteBusinessUnit(id: string, force = false): Promise<void> {
  const tail = force ? "?force=true" : "";
  return apiFetch<void>(`/api/v1/business-units/${id}${tail}`, { method: "DELETE" });
}

// -- Departments ----

export type Department = {
  id: string;
  business_unit_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
};

export type DepartmentCreateBody = {
  name: string;
  description?: string | null;
  is_active?: boolean;
};

export type DepartmentUpdateBody = Partial<DepartmentCreateBody>;

export function listDepartments(
  businessUnitId: string,
  params: { q?: string; is_active?: boolean } = {},
): Promise<Department[]> {
  return apiFetch<Department[]>(
    `/api/v1/business-units/${businessUnitId}/departments${qs(params)}`,
  );
}

export function createDepartment(
  businessUnitId: string,
  body: DepartmentCreateBody,
): Promise<Department> {
  return apiFetch<Department>(
    `/api/v1/business-units/${businessUnitId}/departments`,
    { method: "POST", body },
  );
}

export function updateDepartment(
  id: string,
  body: DepartmentUpdateBody,
): Promise<Department> {
  return apiFetch<Department>(`/api/v1/departments/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteDepartment(id: string, force = false): Promise<void> {
  const tail = force ? "?force=true" : "";
  return apiFetch<void>(`/api/v1/departments/${id}${tail}`, { method: "DELETE" });
}
