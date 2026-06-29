// US-097 — catálogo tenant Áreas → Equipos → Actores.
import { apiFetch } from "@/lib/api";

export type Area = {
  id: string;
  tenant_id: string;
  /** BUG-061: null = área tenant-global; set = área scoped a esa org. */
  organization_id?: string | null;
  name: string;
  description: string | null;
  /** ENH-078: FK al Actor líder (con is_lead=true). */
  lead_actor_id?: string | null;
  is_active: boolean;
  created_at: string;
};

export type Team = {
  id: string;
  tenant_id: string;
  area_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
};

export type Actor = {
  id: string;
  tenant_id: string;
  team_id: string | null;
  area_id?: string | null;
  user_id: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_lead?: boolean;
  // US-114: enriquecimiento.
  company?: string | null;
  job_title?: string | null;
  manager_actor_id?: string | null;
  created_at: string;
};

export type TreeActor = {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  user_id: string | null;
  is_active: boolean;
  is_lead?: boolean;
  team_id?: string | null;
  area_id?: string | null;
};

export type TreeTeam = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  actors: TreeActor[];
};

export type TreeArea = {
  id: string;
  organization_id?: string | null;
  name: string;
  description: string | null;
  lead_actor_id?: string | null;
  is_active: boolean;
  teams: TreeTeam[];
  unassigned_actors: TreeActor[];
};

export type AreaTreeResponse = {
  areas: TreeArea[];
  orphan_actors: TreeActor[];
};

// ---------- Areas ----------
export function listAreas(params?: {
  q?: string;
  is_active?: boolean;
  organization_id?: string | null;
  include_global?: boolean;
}): Promise<Area[]> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  if (params?.is_active != null) qs.set("is_active", String(params.is_active));
  if (params?.organization_id) qs.set("organization_id", params.organization_id);
  if (params?.include_global != null)
    qs.set("include_global", String(params.include_global));
  const tail = qs.toString();
  return apiFetch<Area[]>(`/api/v1/areas${tail ? `?${tail}` : ""}`);
}

export function getAreasTree(
  params?: {
    includeInactive?: boolean;
    organization_id?: string | null;
    include_global?: boolean;
  },
): Promise<AreaTreeResponse> {
  const qs = new URLSearchParams();
  if (params?.includeInactive) qs.set("include_inactive", "true");
  if (params?.organization_id) qs.set("organization_id", params.organization_id);
  if (params?.include_global != null)
    qs.set("include_global", String(params.include_global));
  const tail = qs.toString();
  return apiFetch<AreaTreeResponse>(
    `/api/v1/areas/tree${tail ? `?${tail}` : ""}`,
  );
}

export type AreaLeadInput = {
  actor_id?: string | null;
  name?: string | null;
  email?: string | null;
  phone?: string | null;
};

export function createArea(body: {
  name: string;
  description?: string | null;
  is_active?: boolean;
  lead?: AreaLeadInput | null;
  /** BUG-061: si se omite o null el área queda tenant-global. */
  organization_id?: string | null;
  /**
   * BUG-085: scope de creación. Pasá `project_id` (o `program_id`) cuando
   * creás el área desde un proyecto/programa: el backend deriva el
   * organization_id del padre y crea el AreaAssignment del scope correcto
   * (proyecto queda en el proyecto; programa/org propagan a los hijos).
   */
  project_id?: string | null;
  program_id?: string | null;
}): Promise<Area> {
  return apiFetch<Area>("/api/v1/areas", { method: "POST", body });
}

export function updateArea(
  id: string,
  body: {
    name?: string;
    description?: string | null;
    is_active?: boolean;
    lead_actor_id?: string | null;
    organization_id?: string | null;
  },
): Promise<Area> {
  return apiFetch<Area>(`/api/v1/areas/${id}`, { method: "PATCH", body });
}

export function deleteArea(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/areas/${id}`, { method: "DELETE" });
}

// ---------- Teams ----------
export function listTeams(params?: {
  area_id?: string;
  q?: string;
  is_active?: boolean;
}): Promise<Team[]> {
  const qs = new URLSearchParams();
  if (params?.area_id) qs.set("area_id", params.area_id);
  if (params?.q) qs.set("q", params.q);
  if (params?.is_active != null) qs.set("is_active", String(params.is_active));
  const tail = qs.toString();
  return apiFetch<Team[]>(`/api/v1/teams${tail ? `?${tail}` : ""}`);
}

export function createTeam(body: {
  area_id: string;
  name: string;
  description?: string | null;
  is_active?: boolean;
}): Promise<Team> {
  return apiFetch<Team>("/api/v1/teams", { method: "POST", body });
}

export function updateTeam(
  id: string,
  body: {
    area_id?: string;
    name?: string;
    description?: string | null;
    is_active?: boolean;
  },
): Promise<Team> {
  return apiFetch<Team>(`/api/v1/teams/${id}`, { method: "PATCH", body });
}

export function deleteTeam(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/teams/${id}`, { method: "DELETE" });
}

// ---------- Actors ----------
export function listActors(params?: {
  team_id?: string;
  area_id?: string;
  q?: string;
  is_active?: boolean;
}): Promise<Actor[]> {
  const qs = new URLSearchParams();
  if (params?.team_id) qs.set("team_id", params.team_id);
  if (params?.area_id) qs.set("area_id", params.area_id);
  if (params?.q) qs.set("q", params.q);
  if (params?.is_active != null) qs.set("is_active", String(params.is_active));
  const tail = qs.toString();
  return apiFetch<Actor[]>(`/api/v1/actors${tail ? `?${tail}` : ""}`);
}

export function createActor(body: {
  team_id?: string | null;
  area_id?: string | null;
  user_id?: string | null;
  name: string;
  email?: string | null;
  phone?: string | null;
  is_active?: boolean;
  is_lead?: boolean;
  // US-114: enriquecimiento.
  company?: string | null;
  job_title?: string | null;
  manager_actor_id?: string | null;
}): Promise<Actor> {
  return apiFetch<Actor>("/api/v1/actors", { method: "POST", body });
}

export function updateActor(
  id: string,
  body: {
    team_id?: string | null;
    area_id?: string | null;
    user_id?: string | null;
    name?: string;
    email?: string | null;
    phone?: string | null;
    is_active?: boolean;
    is_lead?: boolean;
  },
): Promise<Actor> {
  return apiFetch<Actor>(`/api/v1/actors/${id}`, { method: "PATCH", body });
}

export function deleteActor(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/actors/${id}`, { method: "DELETE" });
}

// US-099 — bulk reassign tasks/raid/minutes from one actor to another.
export type ActorReassignBody = {
  target_actor_id: string;
  scopes?: string[];
  deactivate_source?: boolean;
};

export type ActorReassignResponse = {
  tasks_moved: number;
  raid_moved: number;
  minutes_moved: number;
  source_deactivated: boolean;
};

export function reassignActor(
  id: string,
  body: ActorReassignBody,
): Promise<ActorReassignResponse> {
  return apiFetch<ActorReassignResponse>(
    `/api/v1/actors/${id}/reassign`,
    { method: "POST", body },
  );
}

// ---------- Area assignments (US-103) ----------
export type AreaAssignment = {
  id: string;
  area_id: string;
  organization_id: string | null;
  program_id: string | null;
  project_id: string | null;
  is_global: boolean;
  created_at: string;
  // ENH-080: nombres legibles resueltos en backend.
  organization_name?: string | null;
  program_name?: string | null;
  project_name?: string | null;
};

export type AssignmentScope = {
  organization_id?: string | null;
  program_id?: string | null;
  project_id?: string | null;
  is_global?: boolean;
};

export function listAreaAssignments(areaId: string): Promise<AreaAssignment[]> {
  return apiFetch<AreaAssignment[]>(
    `/api/v1/admin/areas/${areaId}/assignments`,
  );
}

export function setAreaAssignments(
  areaId: string,
  scopes: AssignmentScope[],
): Promise<AreaAssignment[]> {
  return apiFetch<AreaAssignment[]>(
    `/api/v1/admin/areas/${areaId}/assignments`,
    { method: "PUT", body: { scopes } },
  );
}

export function listAreasByProject(projectId: string): Promise<Area[]> {
  return apiFetch<Area[]>(`/api/v1/admin/areas/by-project/${projectId}`);
}

// ENH-082 — re-sync runtime de tenant users → Actores en área PMO.
export type PmoSyncResponse = {
  created: number;
  linked: number;
  skipped: number;
  total_users: number;
  synced_at: string;
};

export function syncPmoUsers(): Promise<PmoSyncResponse> {
  return apiFetch<PmoSyncResponse>("/api/v1/admin/areas/pmo/sync-users", {
    method: "POST",
  });
}

// ENH-079 — Actores asignables como responsables/owners del proyecto.
export function listActorsByProject(projectId: string): Promise<Actor[]> {
  return apiFetch<Actor[]>(
    `/api/v1/admin/areas/by-project/${projectId}/actors`,
  );
}
