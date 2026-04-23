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
  /** US-062: líder del área (FK a users, nullable). */
  area_leader_id: string | null;
  is_active: boolean;
};

export type ProjectAreaCreateBody = {
  name: string;
  type?: ProjectAreaType;
  description?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  area_leader_id?: string | null;
  is_active?: boolean;
};

export type ProjectAreaUpdateBody = Partial<ProjectAreaCreateBody>;

/** ENH-020 + US-062: recurso asignado al área (interno o externo). */
export type ProjectAreaResource = {
  id: string;
  area_id: string;
  user_id: string | null;
  name: string | null;
  email: string | null;
  role: string | null;
  is_active: boolean;
};

export type ProjectAreaResourceCreateBody = {
  user_id?: string | null;
  name?: string | null;
  email?: string | null;
  role?: string | null;
  is_active?: boolean;
};

export type ProjectAreaResourceUpdateBody = {
  name?: string | null;
  email?: string | null;
  role?: string | null;
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

export function listAreaResources(
  areaId: string,
  params: { is_active?: boolean } = {},
): Promise<ProjectAreaResource[]> {
  return apiFetch<ProjectAreaResource[]>(
    `/api/v1/project-areas/${areaId}/resources${qs(params)}`,
  );
}

export function createAreaResource(
  areaId: string,
  body: ProjectAreaResourceCreateBody,
): Promise<ProjectAreaResource> {
  return apiFetch<ProjectAreaResource>(
    `/api/v1/project-areas/${areaId}/resources`,
    { method: "POST", body },
  );
}

export function updateAreaResource(
  resourceId: string,
  body: ProjectAreaResourceUpdateBody,
): Promise<ProjectAreaResource> {
  return apiFetch<ProjectAreaResource>(
    `/api/v1/project-area-resources/${resourceId}`,
    { method: "PATCH", body },
  );
}

export function deleteAreaResource(resourceId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/project-area-resources/${resourceId}`, {
    method: "DELETE",
  });
}
