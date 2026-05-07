// US-097 — catálogo tenant Áreas → Equipos → Actores.
import { apiFetch } from "@/lib/api";

export type Area = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
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
  user_id: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
};

export type TreeActor = {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  user_id: string | null;
  is_active: boolean;
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
  name: string;
  description: string | null;
  is_active: boolean;
  teams: TreeTeam[];
  unassigned_actors: TreeActor[];
};

export type AreaTreeResponse = {
  areas: TreeArea[];
  orphan_actors: TreeActor[];
};

// ---------- Areas ----------
export function listAreas(params?: { q?: string; is_active?: boolean }): Promise<Area[]> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  if (params?.is_active != null) qs.set("is_active", String(params.is_active));
  const tail = qs.toString();
  return apiFetch<Area[]>(`/api/v1/areas${tail ? `?${tail}` : ""}`);
}

export function getAreasTree(includeInactive = false): Promise<AreaTreeResponse> {
  return apiFetch<AreaTreeResponse>(
    `/api/v1/areas/tree${includeInactive ? "?include_inactive=true" : ""}`,
  );
}

export function createArea(body: {
  name: string;
  description?: string | null;
  is_active?: boolean;
}): Promise<Area> {
  return apiFetch<Area>("/api/v1/areas", { method: "POST", body });
}

export function updateArea(
  id: string,
  body: { name?: string; description?: string | null; is_active?: boolean },
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
  user_id?: string | null;
  name: string;
  email?: string | null;
  phone?: string | null;
  is_active?: boolean;
}): Promise<Actor> {
  return apiFetch<Actor>("/api/v1/actors", { method: "POST", body });
}

export function updateActor(
  id: string,
  body: {
    team_id?: string | null;
    user_id?: string | null;
    name?: string;
    email?: string | null;
    phone?: string | null;
    is_active?: boolean;
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
