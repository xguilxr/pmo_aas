import { apiFetch } from "@/lib/api";

export type AdminUser = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login: string | null;
  roles: string[];
};

export type PaginatedUsers = {
  items: AdminUser[];
  total: number;
  page: number;
  limit: number;
};

export type ListUsersParams = {
  q?: string;
  role_id?: string;
  is_active?: boolean;
  page?: number;
  limit?: number;
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

export function listUsers(params: ListUsersParams = {}): Promise<PaginatedUsers> {
  return apiFetch<PaginatedUsers>(`/api/v1/admin/users${qs(params)}`);
}

export function getUser(id: string): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/v1/admin/users/${id}`);
}

export type CreateUserBody = {
  full_name: string;
  username: string;
  email: string;
  password: string;
  role_ids: string[];
  is_active: boolean;
};

export function createUser(body: CreateUserBody): Promise<AdminUser> {
  return apiFetch<AdminUser>("/api/v1/admin/users", { method: "POST", body });
}

export type UpdateUserBody = {
  full_name?: string;
  email?: string;
  role_ids?: string[];
  is_active?: boolean;
};

export function updateUser(id: string, body: UpdateUserBody): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/v1/admin/users/${id}`, { method: "PATCH", body });
}

export function deleteUser(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/users/${id}`, { method: "DELETE" });
}

export function resetUserPassword(id: string): Promise<{ temp_password: string }> {
  return apiFetch<{ temp_password: string }>(`/api/v1/admin/users/${id}/reset-password`, {
    method: "POST",
  });
}

export function unlockUser(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/users/${id}/unlock`, { method: "POST" });
}

export type AdminRole = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Record<string, string[]>;
};

export function listRoles(): Promise<AdminRole[]> {
  return apiFetch<AdminRole[]>("/api/v1/admin/roles");
}

export function getRole(id: string): Promise<AdminRole> {
  return apiFetch<AdminRole>(`/api/v1/admin/roles/${id}`);
}

export type CreateRoleBody = {
  name: string;
  description?: string | null;
  permissions: Record<string, string[]>;
};

export function createRole(body: CreateRoleBody): Promise<AdminRole> {
  return apiFetch<AdminRole>("/api/v1/admin/roles", { method: "POST", body });
}

export type UpdateRoleBody = {
  name?: string;
  description?: string | null;
  permissions?: Record<string, string[]>;
};

export function updateRole(id: string, body: UpdateRoleBody): Promise<AdminRole> {
  return apiFetch<AdminRole>(`/api/v1/admin/roles/${id}`, { method: "PATCH", body });
}

export function deleteRole(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/roles/${id}`, { method: "DELETE" });
}

export const VALID_MODULES = [
  "projects",
  "risks",
  "issues",
  "change_requests",
  "documents",
  "lessons",
  "minutes",
  "admin.users",
  "admin.roles",
  "admin.organizations",
  "admin.projects",
  "admin.requests",
  "ai.generate",
  "dashboard",
] as const;

export const VALID_ACTIONS = [
  "read",
  "create",
  "update",
  "delete",
  "approve",
  "upload",
  "minute",
  "report",
] as const;

export const MODULE_LABELS: Record<(typeof VALID_MODULES)[number], string> = {
  projects: "Proyectos",
  risks: "Riesgos",
  issues: "Issues",
  change_requests: "Cambios",
  documents: "Documentos",
  lessons: "Lecciones",
  minutes: "Minutas",
  "admin.users": "Admin · Usuarios",
  "admin.roles": "Admin · Roles",
  "admin.organizations": "Admin · Organizaciones",
  "admin.projects": "Admin · Proyectos",
  "admin.requests": "Admin · Solicitudes",
  "ai.generate": "IA · Generación",
  dashboard: "Tablero",
};

export const ACTION_LABELS: Record<(typeof VALID_ACTIONS)[number], string> = {
  read: "Ver",
  create: "Crear",
  update: "Editar",
  delete: "Borrar",
  approve: "Aprobar",
  upload: "Subir",
  minute: "Levantar",
  report: "Reportar",
};
