import { apiFetch } from "@/lib/api";

export type ProjectPhase = "planning" | "execution" | "support" | "closed";
export type ProjectType = "innovation" | "transformation" | "operation" | "bau";
export type ProjectHealth = "green" | "yellow" | "red";
export type ProjectMemberRole = "pm" | "team" | "viewer" | "stakeholder";

export type Project = {
  id: string;
  folio: string;
  name: string;
  description: string | null;
  type: ProjectType | null;
  priority: number | null;
  phase: ProjectPhase;
  organization_id: string;
  program_id: string | null;
  pm_id: string | null;
  sponsor: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: string | null;
  actual_budget: string | null;
  progress: number;
  health_status: ProjectHealth;
  request_id: string | null;
};

export type ProjectMember = {
  user_id: string;
  role_in_project: ProjectMemberRole;
  username: string;
  full_name: string;
};

export type ProjectDetail = Project & {
  members: ProjectMember[];
  module_counts: Record<string, number>;
};

export type ProjectCreateBody = {
  name: string;
  description: string;
  type: ProjectType;
  priority: number;
  organization_id: string;
  program_id?: string | null;
  phase?: ProjectPhase;
  pm_id: string;
  sponsor?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  budget?: number | string | null;
};

export type ProjectUpdateBody = Partial<{
  name: string;
  description: string;
  type: ProjectType;
  priority: number;
  program_id: string | null;
  pm_id: string;
  sponsor: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: number | string | null;
  actual_budget: number | string | null;
  progress: number;
  health_status: ProjectHealth;
}>;

export type ListProjectsParams = {
  phase?: ProjectPhase[] | ProjectPhase;
  organization_id?: string;
  program_id?: string;
  type?: ProjectType[] | ProjectType;
  health?: ProjectHealth[] | ProjectHealth;
  priority_min?: number;
  priority_max?: number;
  q?: string;
  only_mine?: boolean;
  page?: number;
  limit?: number;
};

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) {
      for (const item of v) if (item !== undefined && item !== null) usp.append(k, String(item));
    } else {
      usp.set(k, String(v));
    }
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function listProjects(params: ListProjectsParams = {}): Promise<Project[]> {
  return apiFetch<Project[]>(`/api/v1/projects${qs(params)}`);
}

export function getProject(id: string): Promise<ProjectDetail> {
  return apiFetch<ProjectDetail>(`/api/v1/projects/${id}`);
}

export function createProject(body: ProjectCreateBody): Promise<Project> {
  return apiFetch<Project>("/api/v1/projects", { method: "POST", body });
}

export function updateProject(id: string, body: ProjectUpdateBody): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`, { method: "PATCH", body });
}

export function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}

export function changePhase(
  id: string,
  body: { new_phase: ProjectPhase; comment?: string | null },
): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}/phase/change`, { method: "POST", body });
}

export function listMembers(id: string): Promise<ProjectMember[]> {
  return apiFetch<ProjectMember[]>(`/api/v1/projects/${id}/members`);
}

export function addMember(
  id: string,
  body: { user_id: string; role_in_project?: ProjectMemberRole },
): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}/members`, { method: "POST", body });
}

export function removeMember(id: string, userId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}/members/${userId}`, { method: "DELETE" });
}

export const PHASE_LABEL: Record<ProjectPhase, string> = {
  planning: "Planificación",
  execution: "Ejecución",
  support: "Soporte",
  closed: "Cerrado",
};

export const TYPE_LABEL: Record<ProjectType, string> = {
  innovation: "Innovación",
  transformation: "Transformación",
  operation: "Operación",
  bau: "BAU",
};

export const HEALTH_LABEL: Record<ProjectHealth, string> = {
  green: "Verde",
  yellow: "Amarillo",
  red: "Rojo",
};

export const MEMBER_ROLE_LABEL: Record<ProjectMemberRole, string> = {
  pm: "Project Manager",
  team: "Equipo",
  viewer: "Observador",
  stakeholder: "Stakeholder",
};
