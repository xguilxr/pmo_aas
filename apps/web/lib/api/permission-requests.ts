import { apiFetch } from "@/lib/api";

/**
 * US-082 — tickets de cambio de permisos del admin del tenant al
 * superadmin. Cada ticket pide un cambio puntual (módulo + acción)
 * para un usuario específico, con razón obligatoria.
 */

export type PermissionRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "cancelled";

export type PermissionRequestUserMini = {
  id: string;
  email: string;
  full_name: string | null;
};

export type PermissionRequest = {
  id: string;
  tenant_id: string;
  requested_by: PermissionRequestUserMini | null;
  target_user: PermissionRequestUserMini | null;
  module: string;
  action: string;
  requested_grant: boolean;
  reason: string;
  status: PermissionRequestStatus;
  decided_by: PermissionRequestUserMini | null;
  decided_at: string | null;
  decision_note: string | null;
  created_at: string;
  updated_at: string;
};

export type CreatePermissionRequestBody = {
  target_user_id: string;
  module: string;
  action: string;
  requested_grant: boolean;
  reason: string;
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

export function listPermissionRequests(params: {
  status?: PermissionRequestStatus;
  mine?: boolean;
} = {}): Promise<PermissionRequest[]> {
  return apiFetch<PermissionRequest[]>(
    `/api/v1/permission-requests${qs(params)}`,
  );
}

export function createPermissionRequest(
  body: CreatePermissionRequestBody,
): Promise<PermissionRequest> {
  return apiFetch<PermissionRequest>("/api/v1/permission-requests", {
    method: "POST",
    body,
  });
}

export function cancelPermissionRequest(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/permission-requests/${id}`, {
    method: "DELETE",
  });
}

export function approvePermissionRequest(
  id: string,
): Promise<PermissionRequest> {
  return apiFetch<PermissionRequest>(
    `/api/v1/superadmin/permission-requests/${id}/approve`,
    { method: "POST" },
  );
}

export function rejectPermissionRequest(
  id: string,
  decision_note: string,
): Promise<PermissionRequest> {
  return apiFetch<PermissionRequest>(
    `/api/v1/superadmin/permission-requests/${id}/reject`,
    { method: "POST", body: { decision_note } },
  );
}
