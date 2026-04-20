import { apiFetch } from "@/lib/api";

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export type PlatformKpis = {
  tenants_total: number;
  tenants_active: number;
  tenants_inactive: number;
  users_total: number;
  projects_total: number;
  ai_tokens_30d: { in: number; out: number };
};

export type PlatformDashboard = {
  kpis: PlatformKpis;
  top_tenants: Array<{ id: string; slug: string; name: string; project_count: number }>;
  activity_recent: Array<{
    id: number;
    action: string;
    module: string | null;
    tenant_id: string | null;
    user_id: string | null;
    occurred_at: string | null;
  }>;
};

export function getPlatformDashboard(): Promise<PlatformDashboard> {
  return apiFetch<PlatformDashboard>("/api/v1/superadmin/dashboard");
}

export type TenantSummary = {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
  created_at: string;
  ai_mode: string | null;
};

export type SearchTenantsParams = {
  q?: string;
  ai_mode?: string;
  is_active?: boolean;
  created_from?: string;
  created_to?: string;
  cursor?: string;
  limit?: number;
};

export type SearchTenantsResult = {
  items: TenantSummary[];
  next_cursor: string | null;
};

export function searchTenants(params: SearchTenantsParams = {}): Promise<SearchTenantsResult> {
  return apiFetch<SearchTenantsResult>(`/api/v1/superadmin/tenants/search${qs(params)}`);
}

export type TenantFullDetail = {
  tenant: {
    id: string;
    slug: string;
    name: string;
    is_active: boolean;
    settings: Record<string, unknown>;
    created_at: string;
  };
  users?: Array<{
    id: string;
    username: string;
    email: string;
    is_active: boolean;
    last_login: string | null;
  }>;
  projects?: Array<{
    id: string;
    folio: string;
    name: string;
    phase: string;
    health_status: string;
    pm_id: string | null;
  }>;
  organizations?: Array<{ id: string; name: string; is_active: boolean }>;
  logs?: Array<{
    id: number;
    action: string;
    module: string | null;
    user_id: string | null;
    entity_type: string | null;
    entity_id: string | null;
    occurred_at: string | null;
  }>;
  ai_jobs?: Array<{
    id: string;
    kind: string;
    status: string;
    model_used: string | null;
    tokens_in: number | null;
    tokens_out: number | null;
    error: string | null;
    created_at: string | null;
  }>;
};

export function getTenantFullDetail(
  id: string,
  include: string = "all",
): Promise<TenantFullDetail> {
  return apiFetch<TenantFullDetail>(
    `/api/v1/superadmin/tenants/${id}/full-detail${qs({ include })}`,
  );
}

export type PlatformLogRow = {
  id: number;
  action: string;
  module: string | null;
  tenant_id: string | null;
  user_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  occurred_at: string | null;
};

export type PlatformLogParams = {
  q?: string;
  action?: string;
  tenant_id?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
};

export function getPlatformLogs(params: PlatformLogParams = {}): Promise<PlatformLogRow[]> {
  return apiFetch<PlatformLogRow[]>(`/api/v1/superadmin/logs/platform${qs(params)}`);
}

export type PlatformHealth = {
  db: boolean;
  api: boolean;
  time: string;
};

export function getPlatformHealth(): Promise<PlatformHealth> {
  return apiFetch<PlatformHealth>("/api/v1/superadmin/health");
}

export function freezeTenant(id: string): Promise<{ ok: boolean; frozen: boolean }> {
  return apiFetch<{ ok: boolean; frozen: boolean }>(
    `/api/v1/superadmin/tenants/${id}/freeze`,
    { method: "POST" },
  );
}

export function unfreezeTenant(id: string): Promise<{ ok: boolean; frozen: boolean }> {
  return apiFetch<{ ok: boolean; frozen: boolean }>(
    `/api/v1/superadmin/tenants/${id}/unfreeze`,
    { method: "POST" },
  );
}

// ---- US-NEW-042: Usuarios cross-tenant ----

export type SuperadminUserRow = {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superadmin: boolean;
  tenant_id: string | null;
  tenant_slug: string | null;
  tenant_name: string | null;
  roles: string[];
  created_at: string | null;
  last_login_at: string | null;
};

export type ListSuperadminUsersParams = {
  q?: string;
  tenant_id?: string;
  is_active?: boolean;
  is_superadmin?: boolean;
  role_name?: string;
  page?: number;
  limit?: number;
};

export type ListSuperadminUsersResult = {
  items: SuperadminUserRow[];
  page: number;
  limit: number;
  count: number;
};

export function listSuperadminUsers(
  params: ListSuperadminUsersParams = {},
): Promise<ListSuperadminUsersResult> {
  return apiFetch<ListSuperadminUsersResult>(
    `/api/v1/superadmin/users${qs(params)}`,
  );
}

export type SuperadminUserUpdate = {
  full_name?: string;
  email?: string;
  username?: string;
  is_active?: boolean;
};

export function updateSuperadminUser(
  id: string,
  body: SuperadminUserUpdate,
): Promise<Pick<SuperadminUserRow, "id" | "username" | "email" | "full_name" | "is_active">> {
  return apiFetch(`/api/v1/superadmin/users/${id}`, {
    method: "PATCH",
    body,
  });
}

export function toggleSuperadminUserActive(
  id: string,
  reason: string,
): Promise<{ id: string; is_active: boolean }> {
  return apiFetch(`/api/v1/superadmin/users/${id}/toggle-active`, {
    method: "POST",
    body: { reason },
  });
}
