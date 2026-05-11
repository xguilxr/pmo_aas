// US-115/US-116 — cliente API para directorio de proyecto.
import { apiFetch } from "@/lib/api";

export type ProjectRole = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
};

export type ActorMini = {
  id: string;
  name: string;
  email: string | null;
  company: string | null;
  job_title: string | null;
};

export type Participation = {
  id: string;
  tenant_id: string;
  project_id: string;
  actor_id: string;
  operational_team_id: string | null;
  project_role_id: string | null;
  functional_area_id: string | null;
  is_area_lead: boolean;
  is_primary: boolean;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  created_at: string;
  actor?: ActorMini | null;
};

export type ParticipationCreate = {
  actor_id: string;
  operational_team_id?: string | null;
  project_role_id?: string | null;
  functional_area_id?: string | null;
  is_area_lead?: boolean;
  is_primary?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ParticipationUpdate = Partial<ParticipationCreate>;

// Project roles
export const listProjectRoles = (params?: { is_active?: boolean }) =>
  apiFetch<ProjectRole[]>(
    `/api/v1/project-roles${params?.is_active !== undefined ? `?is_active=${params.is_active}` : ""}`,
  );

export const createProjectRole = (body: {
  name: string;
  description?: string | null;
  is_active?: boolean;
}) =>
  apiFetch<ProjectRole>(`/api/v1/project-roles`, {
    method: "POST",
    body,
  });

export const updateProjectRole = (
  id: string,
  body: { name?: string; description?: string | null; is_active?: boolean },
) =>
  apiFetch<ProjectRole>(`/api/v1/project-roles/${id}`, {
    method: "PATCH",
    body,
  });

export const deleteProjectRole = (id: string) =>
  apiFetch<void>(`/api/v1/project-roles/${id}`, { method: "DELETE" });

// Participations
export const listParticipations = (
  projectId: string,
  opts?: { include?: "actor"; is_active?: boolean; is_primary?: boolean },
) => {
  const qp = new URLSearchParams();
  if (opts?.include) qp.set("include", opts.include);
  if (opts?.is_active !== undefined) qp.set("is_active", String(opts.is_active));
  if (opts?.is_primary !== undefined) qp.set("is_primary", String(opts.is_primary));
  const qs = qp.toString();
  return apiFetch<Participation[]>(
    `/api/v1/projects/${projectId}/participations${qs ? `?${qs}` : ""}`,
  );
};

export const createParticipation = (
  projectId: string,
  body: ParticipationCreate,
) =>
  apiFetch<Participation>(`/api/v1/projects/${projectId}/participations`, {
    method: "POST",
    body,
  });

export const updateParticipation = (
  projectId: string,
  participationId: string,
  body: ParticipationUpdate,
) =>
  apiFetch<Participation>(
    `/api/v1/projects/${projectId}/participations/${participationId}`,
    { method: "PATCH", body },
  );

export const deleteParticipation = (projectId: string, participationId: string) =>
  apiFetch<void>(`/api/v1/projects/${projectId}/participations/${participationId}`, {
    method: "DELETE",
  });

// US-117 — actores eligibles para dropdowns de assignee/owner.
export const listEligibleActors = (projectId: string) =>
  apiFetch<ActorMini[]>(`/api/v1/projects/${projectId}/eligible-actors`);
