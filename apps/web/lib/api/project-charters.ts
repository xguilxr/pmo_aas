import { apiFetch } from "@/lib/api";

// Sección 4 del charter — derivada desde el proyecto (read-only).
export type CharterSection4 = {
  start_date: string | null;
  estimated_end_date: string | null;
  phase: string | null;
  health_status: string | null;
  progress: number | null;
  planned_progress: number | null;
  assigned_budget: string | null;
  used_budget: string | null;
  assigned_hours: string | null;
  consumed_hours: string | null;
};

export type ProjectCharter = {
  id: string;
  project_id: string;
  request_id: string | null;

  // Sección 1
  project_name: string;
  description: string | null;
  organization_id: string | null;
  business_unit_id: string | null;
  department_id: string | null;

  // Sección 2
  sponsor: string | null;
  sponsor_email: string | null;
  business_leader: string | null;
  business_leader_email: string | null;
  tech_leader: string | null;
  tech_leader_email: string | null;
  pm_id: string | null;

  // Sección 3
  project_type: string | null;
  priority: number | null;
  objective: string | null;
  restrictions: string | null;
  risks_summary: string | null;
  scope: string | null;
  key_people: string | null;
  benefits: string | null;

  section_4: CharterSection4;

  created_at: string;
  updated_at: string;
};

// Sólo secciones 1–3 son editables (DEC-008).
export type ProjectCharterUpdate = {
  project_name?: string;
  description?: string | null;
  business_unit_id?: string | null;
  department_id?: string | null;
  sponsor?: string | null;
  sponsor_email?: string | null;
  business_leader?: string | null;
  business_leader_email?: string | null;
  tech_leader?: string | null;
  tech_leader_email?: string | null;
  project_type?: string | null;
  priority?: number | null;
  objective?: string | null;
  restrictions?: string | null;
  risks_summary?: string | null;
  scope?: string | null;
  key_people?: string | null;
  benefits?: string | null;
};

export function getProjectCharter(projectId: string): Promise<ProjectCharter> {
  return apiFetch<ProjectCharter>(`/api/v1/projects/${projectId}/charter`);
}

export function updateProjectCharter(
  projectId: string,
  body: ProjectCharterUpdate,
): Promise<ProjectCharter> {
  return apiFetch<ProjectCharter>(`/api/v1/projects/${projectId}/charter`, {
    method: "PATCH",
    body,
  });
}
