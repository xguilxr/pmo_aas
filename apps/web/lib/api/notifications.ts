import { apiFetch } from "@/lib/api";

export type NotificationType =
  | "request_approved"
  | "request_rejected"
  | "request_needs_info"
  | "pm_assigned"
  | "pm_removed"
  | "phase_changed"
  | "aid_overdue"
  | "risk_high"
  | "change_pending"
  | "minute_generated"
  | "report_sent"
  | string;

export type NotificationItem = {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  link: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export type NotificationPreferences = {
  email_enabled: boolean;
  by_type: Record<string, "email_and_inapp" | "inapp_only">;
};

type ListParams = {
  is_read?: boolean;
  page?: number;
  limit?: number;
};

function toQs(p: ListParams): string {
  const u = new URLSearchParams();
  if (p.is_read !== undefined) u.set("is_read", String(p.is_read));
  if (p.page) u.set("page", String(p.page));
  if (p.limit) u.set("limit", String(p.limit));
  const s = u.toString();
  return s ? `?${s}` : "";
}

export function listNotifications(params: ListParams = {}): Promise<NotificationItem[]> {
  return apiFetch<NotificationItem[]>(`/api/v1/notifications${toQs(params)}`);
}

export function getUnreadCount(): Promise<{ count: number }> {
  return apiFetch<{ count: number }>(`/api/v1/notifications/unread-count`);
}

export function markRead(id: string): Promise<NotificationItem> {
  return apiFetch<NotificationItem>(`/api/v1/notifications/${id}/read`, {
    method: "POST",
  });
}

export function markAllRead(): Promise<{ ok: true }> {
  return apiFetch<{ ok: true }>(`/api/v1/notifications/read-all`, {
    method: "POST",
  });
}

export function getPreferences(): Promise<NotificationPreferences> {
  return apiFetch<NotificationPreferences>(`/api/v1/notifications/preferences`);
}

export function updatePreferences(
  body: Partial<NotificationPreferences>,
): Promise<NotificationPreferences> {
  return apiFetch<NotificationPreferences>(`/api/v1/notifications/preferences`, {
    method: "PATCH",
    body,
  });
}

export const NOTIFICATION_TYPE_LABEL: Record<string, string> = {
  request_approved: "Solicitud aprobada",
  request_rejected: "Solicitud rechazada",
  request_needs_info: "Solicitud requiere info",
  pm_assigned: "PM asignado",
  pm_removed: "PM removido",
  phase_changed: "Cambio de fase",
  aid_overdue: "AID vencida",
  risk_high: "Riesgo severo",
  change_pending: "Cambio en revisión",
  minute_generated: "Minuta IA generada",
  report_sent: "Reporte enviado",
};
