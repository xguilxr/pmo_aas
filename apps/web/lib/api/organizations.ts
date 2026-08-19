import { apiFetch } from "@/lib/api";

export type Organization = {
  id: string;
  name: string;
  reason_social: string | null;
  industry: string | null;
  country: string | null;
  contact_email: string | null;
  logo_url: string | null;
  /** ENH-100: logo del cliente (usado por el header de reportes EP020). */
  client_logo_url: string | null;
  is_active: boolean;
};

export type OrganizationCreateBody = {
  name: string;
  reason_social?: string | null;
  industry?: string | null;
  country?: string | null;
  contact_email?: string | null;
  logo_url?: string | null;
  /** ENH-100 */
  client_logo_url?: string | null;
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
  /** US-199 — la jerarquía nueva cuenta portafolios (ADR-037). */
  portfolio_count: number;
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

export type OrgPanelProgram = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  active_project_count: number;
  /** US-199 — de qué portafolio es, para anidarlo sin otra consulta. */
  portfolio_id: string | null;
};

/** US-199 — un portafolio con sus programas dentro (ADR-037). Reemplaza a
 *  `OrgPanelBusinessUnit`/`OrgPanelDepartment`. */
export type OrgPanelPortfolio = {
  id: string;
  name: string;
  code: string | null;
  description: string | null;
  is_active: boolean;
  programs: OrgPanelProgram[];
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
  /** ENH-100 */
  client_logo_url: string | null;
  is_active: boolean;
  portfolios: OrgPanelPortfolio[];
  /** La lista plana, además del árbol: quien solo necesita «los programas de
   *  esta organización» no tiene que recorrer los portafolios. */
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
  /** US-199 — obligatorio en la base; el alta lo resuelve si no se manda. */
  portfolio_id: string;
  description: string | null;
  strategic_alignment: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
};

export type ProgramCreateBody = {
  name: string;
  organization_id: string;
  /** Opcional: sin él, el programa cae en el «Portafolio General» (DEC-030). */
  portfolio_id?: string | null;
  description?: string | null;
  strategic_alignment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ProgramUpdateBody = {
  name?: string;
  /** Mover el programa de portafolio arrastra sus proyectos (US-199). */
  portfolio_id?: string | null;
  description?: string | null;
  strategic_alignment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ListProgramsParams = {
  organization_id?: string;
  portfolio_id?: string;
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
  portfolio_id: string | null;
  portfolio_name: string | null;
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

// US-088: hard delete (segundo paso) — programs.

export type HardDeletePreview = {
  entity_type: string;
  entity_id: string;
  entity_name: string;
  is_active: boolean;
  confirm_slug: string;
  cascades: Record<string, number>;
  blockers: string[];
};

export function previewHardDeleteProgram(id: string): Promise<HardDeletePreview> {
  return apiFetch<HardDeletePreview>(`/api/v1/programs/${id}/hard-delete-preview`);
}

export function hardDeleteProgram(id: string, confirm: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/programs/${id}/permanent?confirm=${encodeURIComponent(confirm)}`,
    { method: "DELETE" },
  );
}

export function previewHardDeleteOrganization(
  id: string,
): Promise<HardDeletePreview> {
  return apiFetch<HardDeletePreview>(`/api/v1/organizations/${id}/hard-delete-preview`);
}

export function hardDeleteOrganization(id: string, confirm: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/organizations/${id}/permanent?confirm=${encodeURIComponent(confirm)}`,
    { method: "DELETE" },
  );
}

export function previewHardDeletePortfolio(id: string): Promise<HardDeletePreview> {
  return apiFetch<HardDeletePreview>(`/api/v1/portfolios/${id}/hard-delete-preview`);
}

export function hardDeletePortfolio(id: string, confirm: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/portfolios/${id}/permanent?confirm=${encodeURIComponent(confirm)}`,
    { method: "DELETE" },
  );
}

// -- Portafolios (US-199 / ADR-037) ----
// Reemplazan a unidades de negocio y departamentos, cuyos endpoints se
// retiraron: `/business-units` y `/departments` responden 404.

export type Portfolio = {
  id: string;
  organization_id: string;
  name: string;
  code: string | null;
  description: string | null;
  owner_actor_id: string | null;
  is_active: boolean;
  /** Derivados: el portafolio no guarda métricas propias (ADR-037). */
  program_count: number;
  active_project_count: number;
};

export type PortfolioCreateBody = {
  name: string;
  code?: string | null;
  description?: string | null;
  /** El dueño ejecutivo es un actor del catálogo, no un usuario: el sponsor
   *  del cliente casi nunca tiene cuenta en la plataforma. */
  owner_actor_id?: string | null;
  is_active?: boolean;
};

export type PortfolioUpdateBody = Partial<PortfolioCreateBody>;

export function listPortfolios(
  organizationId: string,
  params: { q?: string; is_active?: boolean } = {},
): Promise<Portfolio[]> {
  return apiFetch<Portfolio[]>(
    `/api/v1/organizations/${organizationId}/portfolios${qs(params)}`,
  );
}

export function getPortfolio(id: string): Promise<Portfolio> {
  return apiFetch<Portfolio>(`/api/v1/portfolios/${id}`);
}

export function createPortfolio(
  organizationId: string,
  body: PortfolioCreateBody,
): Promise<Portfolio> {
  return apiFetch<Portfolio>(`/api/v1/organizations/${organizationId}/portfolios`, {
    method: "POST",
    body,
  });
}

export function updatePortfolio(
  id: string,
  body: PortfolioUpdateBody,
): Promise<Portfolio> {
  return apiFetch<Portfolio>(`/api/v1/portfolios/${id}`, { method: "PATCH", body });
}

/** Primer paso de la papelera (ADR-017): desactiva. Con programas activos
 *  dentro exige `force`, y entonces los desactiva en cascada. */
export function deletePortfolio(id: string, force = false): Promise<void> {
  const tail = force ? "?force=true" : "";
  return apiFetch<void>(`/api/v1/portfolios/${id}${tail}`, { method: "DELETE" });
}
