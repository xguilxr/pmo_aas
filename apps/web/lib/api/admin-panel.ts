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

/* ===== Tenant settings ===== */
// ENH-098: per-tenant progress calculation method (Report Builder / EP020).
export type ProgressCalculationMethod =
  | "by_task_count"
  | "by_duration"
  | "by_effort";

// ENH-099: per-tenant resource-load colorization thresholds (Report Builder / EP020).
export type TaskLoadThresholds = {
  green_max: number;
  amber_max: number;
};

export type TenantSettings = {
  locale?: string;
  currency?: string;
  date_format?: string;
  timezone?: string;
  primary_color?: string;
  logo_url?: string;
  // ENH-098: canonical storage under `settings.report_builder.progress_calculation_method`,
  // exposed by the API as a top-level convenience field.
  progress_calculation_method?: ProgressCalculationMethod;
  // ENH-099: canonical storage under `settings.report_builder.task_load_thresholds`,
  // exposed by the API as a top-level convenience field.
  task_load_thresholds?: TaskLoadThresholds;
};

export function getSettings(): Promise<{ settings: TenantSettings }> {
  return apiFetch<{ settings: TenantSettings }>("/api/v1/admin/settings");
}

export function updateSettings(body: Partial<TenantSettings>): Promise<{ settings: TenantSettings }> {
  return apiFetch<{ settings: TenantSettings }>("/api/v1/admin/settings", {
    method: "PATCH",
    body,
  });
}

/* ===== Audit logs ===== */
export type AuditLogEntry = {
  id: string;
  action: string;
  module: string | null;
  user_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  occurred_at: string | null;
};

export type ListAuditParams = {
  action?: string;
  user_id?: string;
  entity_type?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
};

export function listAuditLogs(params: ListAuditParams = {}): Promise<AuditLogEntry[]> {
  return apiFetch<AuditLogEntry[]>(`/api/v1/admin/audit-logs${qs(params)}`);
}

export function auditLogsCsvUrl(apiBase: string): string {
  return `${apiBase.replace(/\/+$/, "")}/api/v1/admin/audit-logs/export.csv`;
}

/* ===== Admin project supervision ===== */
export type AdminProjectRow = {
  id: string;
  folio: string;
  name: string;
  phase: string;
  health_status: string;
  budget: number;
  organization_id: string;
};

export function listAdminProjects(params: { include_inactive_orgs?: boolean } = {}): Promise<AdminProjectRow[]> {
  return apiFetch<AdminProjectRow[]>(`/api/v1/pmo/projects${qs(params)}`);
}

export function forceCloseProject(id: string, comment: string): Promise<{ ok: boolean; phase: string }> {
  return apiFetch<{ ok: boolean; phase: string }>(`/api/v1/pmo/projects/${id}/force-close`, {
    method: "POST",
    body: { comment },
  });
}

/* ===== Org metrics ===== */
export type OrgMetrics = {
  id: string;
  name: string;
  is_active: boolean;
  project_count_active: number;
  budget_total: number;
};

export function listOrgMetrics(): Promise<OrgMetrics[]> {
  return apiFetch<OrgMetrics[]>("/api/v1/admin/organizations/metrics");
}

/* ===== Bulk ===== */
export function bulkAssignRole(body: {
  user_ids: string[];
  role_id: string;
}): Promise<{ affected: number; total: number }> {
  return apiFetch<{ affected: number; total: number }>("/api/v1/admin/users/bulk/assign-role", {
    method: "POST",
    body,
  });
}

export function bulkDeactivateUsers(userIds: string[]): Promise<{ affected: number }> {
  return apiFetch<{ affected: number }>("/api/v1/admin/users/bulk/deactivate", {
    method: "POST",
    body: { user_ids: userIds },
  });
}

/* ===== Tenant info + stats (US-023) ===== */
export type TenantStats = {
  active_users: number;
  total_users: number;
  total_organizations: number;
  total_projects: number;
  storage_bytes: number;
};

export type TenantInfo = {
  id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  is_active: boolean;
  plan: string;
  settings: TenantSettings;
  stats: TenantStats;
};

export type TenantInfoPatch = {
  name?: string;
  logo_url?: string | null;
};

export function getTenantInfo(): Promise<TenantInfo> {
  return apiFetch<TenantInfo>("/api/v1/admin/tenant");
}

export function updateTenantInfo(
  body: TenantInfoPatch,
): Promise<Pick<TenantInfo, "id" | "slug" | "name" | "logo_url">> {
  return apiFetch<Pick<TenantInfo, "id" | "slug" | "name" | "logo_url">>(
    "/api/v1/admin/tenant",
    { method: "PATCH", body },
  );
}
