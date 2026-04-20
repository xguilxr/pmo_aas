import { apiFetch } from "@/lib/api";

export type ProjectAreaType = "area" | "actor" | "team";

export type ProjectArea = {
  id: string;
  project_id: string;
  name: string;
  type: ProjectAreaType;
  description: string | null;
  contact_name: string | null;
  contact_email: string | null;
  is_active: boolean;
};

export type ProjectAreaCreateBody = {
  name: string;
  type?: ProjectAreaType;
  description?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  is_active?: boolean;
};

export type ProjectAreaUpdateBody = Partial<ProjectAreaCreateBody>;

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function listProjectAreas(
  projectId: string,
  params: { q?: string; is_active?: boolean; type?: ProjectAreaType } = {},
): Promise<ProjectArea[]> {
  return apiFetch<ProjectArea[]>(
    `/api/v1/projects/${projectId}/areas${qs(params)}`,
  );
}

export function createProjectArea(
  projectId: string,
  body: ProjectAreaCreateBody,
): Promise<ProjectArea> {
  return apiFetch<ProjectArea>(`/api/v1/projects/${projectId}/areas`, {
    method: "POST",
    body,
  });
}

export function updateProjectArea(
  id: string,
  body: ProjectAreaUpdateBody,
): Promise<ProjectArea> {
  return apiFetch<ProjectArea>(`/api/v1/project-areas/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteProjectArea(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/project-areas/${id}`, { method: "DELETE" });
}
