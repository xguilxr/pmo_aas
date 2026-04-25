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
};

/**
 * US-077 — `listRoles` queda como shim compat hasta que `/admin/users/*`
 * se reescriba en US-078 para gestionar `role_type` directamente sin
 * roles legacy. Devuelve `[]` porque la tabla `roles` está deprecada
 * (DEC-024) y el gate del backend ignora `Role.permissions` JSON.
 */
export function listRoles(): Promise<AdminRole[]> {
  return Promise.resolve([]);
}
