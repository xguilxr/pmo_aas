import { apiFetch } from "@/lib/api";

export type RoleType = "admin" | "pm_sr" | "user";

export const ROLE_TYPE_LABEL: Record<RoleType, string> = {
  admin: "Admin",
  pm_sr: "PM Sr",
  user: "PM",
};

export type AdminUser = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login: string | null;
  roles: string[];
  role_type: RoleType | null;
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
  role_type?: RoleType; // US-078
  excluded_organization_ids?: string[]; // US-078
};

export function createUser(body: CreateUserBody): Promise<AdminUser> {
  return apiFetch<AdminUser>("/api/v1/admin/users", { method: "POST", body });
}

export type UpdateUserBody = {
  full_name?: string;
  email?: string;
  role_ids?: string[];
  is_active?: boolean;
  role_type?: RoleType; // US-078
  must_change_password?: boolean; // US-078
};

export function updateUser(id: string, body: UpdateUserBody): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/v1/admin/users/${id}`, { method: "PATCH", body });
}

export function deleteUser(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/users/${id}`, { method: "DELETE" });
}

// US-088: hard delete (segundo paso) — users.
import type { HardDeletePreview } from "@/lib/api/organizations";

export function previewHardDeleteUser(id: string): Promise<HardDeletePreview> {
  return apiFetch<HardDeletePreview>(`/api/v1/admin/users/${id}/hard-delete-preview`);
}

export function hardDeleteUser(id: string, confirm: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/admin/users/${id}/permanent?confirm=${encodeURIComponent(confirm)}`,
    { method: "DELETE" },
  );
}

export function resetUserPassword(id: string): Promise<{ temp_password: string }> {
  return apiFetch<{ temp_password: string }>(`/api/v1/admin/users/${id}/reset-password`, {
    method: "POST",
  });
}

export function unlockUser(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/admin/users/${id}/unlock`, { method: "POST" });
}

// US-078: forzar cambio en próximo login (no toca password actual).
export function forcePasswordChange(id: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/admin/users/${id}/force-password-change`,
    { method: "POST" }
  );
}

// US-078: membership opt-out user↔organización.
export type ExcludedOrgsResponse = { organization_ids: string[] };

export function getExcludedOrganizations(
  userId: string
): Promise<ExcludedOrgsResponse> {
  return apiFetch<ExcludedOrgsResponse>(
    `/api/v1/admin/users/${userId}/excluded-organizations`
  );
}

export function setExcludedOrganizations(
  userId: string,
  organizationIds: string[]
): Promise<ExcludedOrgsResponse> {
  return apiFetch<ExcludedOrgsResponse>(
    `/api/v1/admin/users/${userId}/excluded-organizations`,
    { method: "PUT", body: { organization_ids: organizationIds } }
  );
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
