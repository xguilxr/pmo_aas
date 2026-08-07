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

  // ENH-081 CA3: lista de campos requeridos calculada server-side.
  completeness: CharterCompleteness;

  created_at: string;
  updated_at: string;
};

export type CharterCompleteness = {
  is_complete: boolean;
  missing_fields: string[];
  required_fields: string[];
};

// ENH-081 CA3: labels en español por campo requerido (UI banner).
export const CHARTER_FIELD_LABEL: Record<string, string> = {
  project_name: "Nombre",
  description: "Descripción",
  sponsor: "Sponsor",
  objective: "Objetivo",
  scope: "Alcance",
  project_type: "Tipo de proyecto",
  priority: "Prioridad",
  business_leader: "Líder de negocio",
  tech_leader: "Líder técnico",
  benefits: "Beneficios",
  restrictions: "Restricciones",
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

/**
 * US-083: descarga el charter en .docx o .pdf. El endpoint genera el
 * archivo on-demand desde el state actual (incluso si está vacío) y
 * lo devuelve como bytes con Content-Disposition: attachment.
 *
 * Hace fetch con Bearer + crea Blob URL para descargar (igual que
 * `openDocumentForDownload` en BUG-034). Esto evita el problema del
 * `<a href>` plain sin auth.
 */
export async function downloadCharter(
  projectId: string,
  format: "docx" | "pdf" = "docx",
): Promise<void> {
  const { apiBase } = await import("@/lib/api");
  const res = await fetch(
    `${apiBase()}/api/v1/projects/${projectId}/charter/download?format=${format}`,
  );
  if (!res.ok) {
    throw new Error(`Falló la descarga (HTTP ${res.status})`);
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 5_000);
}
