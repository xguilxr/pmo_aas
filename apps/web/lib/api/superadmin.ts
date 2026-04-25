import { apiFetch } from "@/lib/api";

export type Tenant = {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
  user_count: number;
  organization_count: number;
  program_count: number;
  project_count: number;
};

export type TenantHierarchy = {
  organization_count: number;
  business_unit_count: number;
  department_count: number;
  program_count: number;
  project_count: number;
};

export type TenantProvisionBody = {
  name: string;
  slug: string;
  admin_email: string;
  admin_full_name: string;
  admin_username?: string | null;
  admin_password?: string | null;
};

export type TenantProvisionResponse = {
  tenant_id: string;
  slug: string;
  admin_user_id: string;
  admin_password: string;
};

export type TenantDetail = {
  tenant: { id: string; slug: string; name: string; is_active: boolean };
  users: {
    id: string;
    username: string;
    email: string;
    is_active: boolean;
    role_type: "admin" | "user" | "viewer" | null;
    is_superadmin: boolean;
  }[];
  organizations: { id: string; name: string; is_active: boolean }[];
  programs: { id: string; name: string; organization_id: string }[];
  hierarchy: TenantHierarchy;
};

export type JoinAsAdminResponse = {
  access_token: string;
  active_tenant_id: string;
  tenant_slug: string;
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

export function provisionTenant(body: TenantProvisionBody): Promise<TenantProvisionResponse> {
  return apiFetch<TenantProvisionResponse>("/api/v1/superadmin/provision", {
    method: "POST",
    body,
  });
}

export function listTenants(includeInactive = false): Promise<Tenant[]> {
  return apiFetch<Tenant[]>(
    `/api/v1/superadmin/tenants${qs({ include_inactive: includeInactive || undefined })}`,
  );
}

export function getTenantDetail(id: string): Promise<TenantDetail> {
  return apiFetch<TenantDetail>(`/api/v1/superadmin/tenants/${id}/detail`);
}

export function softDeleteTenant(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/superadmin/tenants/${id}`, { method: "DELETE" });
}

export function hardDeleteTenant(id: string, confirmSlug: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/superadmin/tenants/${id}/permanent${qs({ confirm_slug: confirmSlug })}`,
    { method: "DELETE" },
  );
}

export function joinAsAdmin(id: string): Promise<JoinAsAdminResponse> {
  return apiFetch<JoinAsAdminResponse>(`/api/v1/superadmin/tenants/${id}/join-as-admin`, {
    method: "POST",
  });
}

// US-072 — gestión de role_type por superadmin.
export type SuperadminUserRow = {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role_type: "admin" | "user" | "viewer" | null;
  is_active: boolean;
  is_superadmin: boolean;
};

export function listTenantUsers(
  tenantId: string,
  filters: { q?: string; role_type?: string } = {},
): Promise<SuperadminUserRow[]> {
  return apiFetch<SuperadminUserRow[]>(
    `/api/v1/superadmin/tenants/${tenantId}/users${qs(filters)}`,
  );
}

export function updateUserRoleType(
  userId: string,
  roleType: "admin" | "user" | "viewer",
): Promise<{ id: string; role_type: string; from?: string | null; changed: boolean }> {
  return apiFetch(`/api/v1/superadmin/users/${userId}/role-type`, {
    method: "PATCH",
    body: { role_type: roleType },
  });
}

// US-074 — superadmin self-profile.
export type SuperadminMe = {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_superadmin: boolean;
};

export type SuperadminMeUpdateBody = {
  current_password: string;
  email?: string;
  full_name?: string;
  new_password?: string;
  // BUG-032: si el endpoint devuelve 409 con
  // code=EMAIL_TAKEN_OFFER_TAKEOVER, la UI ofrece reintentar con
  // este flag en true → libera el email del user en clash.
  force_takeover_email?: boolean;
};

export function getSuperadminMe(): Promise<SuperadminMe> {
  return apiFetch<SuperadminMe>("/api/v1/superadmin/me");
}

export function updateSuperadminMe(body: SuperadminMeUpdateBody): Promise<SuperadminMe> {
  return apiFetch<SuperadminMe>("/api/v1/superadmin/me", {
    method: "PATCH",
    body,
  });
}

// US-073 + DEC-021 — overrides de permisos por tenant.
export type PermissionOverride = {
  id: string;
  role_type: "admin" | "user" | "viewer";
  module: string;
  action: string;
  granted: boolean;
  reason: string;
  updated_by_user_id: string | null;
};

export type PermissionOverrideUpsert = {
  role_type: "admin" | "user" | "viewer";
  module: string;
  action: string;
  granted: boolean;
  reason: string;
};

export function listPermissionOverrides(
  tenantId: string,
): Promise<PermissionOverride[]> {
  return apiFetch<PermissionOverride[]>(
    `/api/v1/superadmin/tenants/${tenantId}/permission-overrides`,
  );
}

export function upsertPermissionOverrides(
  tenantId: string,
  body: PermissionOverrideUpsert[],
): Promise<PermissionOverride[]> {
  return apiFetch<PermissionOverride[]>(
    `/api/v1/superadmin/tenants/${tenantId}/permission-overrides`,
    { method: "PUT", body },
  );
}

export function deletePermissionOverride(
  tenantId: string,
  overrideId: string,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/superadmin/tenants/${tenantId}/permission-overrides/${overrideId}`,
    { method: "DELETE" },
  );
}
