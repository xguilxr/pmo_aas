import { apiFetch } from "@/lib/api";

export type ScheduledReportType = "avance" | "seguimiento";
export type ScheduledReportCadence = "daily" | "weekly" | "monthly";

export type ScheduledReport = {
  id: string;
  project_id: string;
  report_type: ScheduledReportType;
  cadence: ScheduledReportCadence;
  recipients: string[];
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type ScheduledReportCreateBody = {
  report_type: ScheduledReportType;
  cadence: ScheduledReportCadence;
  recipients: string[];
  enabled?: boolean;
};

export type ScheduledReportUpdateBody = {
  report_type?: ScheduledReportType;
  cadence?: ScheduledReportCadence;
  recipients?: string[];
  enabled?: boolean;
};

export function listScheduledReports(
  projectId: string,
): Promise<ScheduledReport[]> {
  return apiFetch<ScheduledReport[]>(
    `/api/v1/projects/${projectId}/scheduled-reports`,
  );
}

export function createScheduledReport(
  projectId: string,
  body: ScheduledReportCreateBody,
): Promise<ScheduledReport> {
  return apiFetch<ScheduledReport>(
    `/api/v1/projects/${projectId}/scheduled-reports`,
    { method: "POST", body },
  );
}

export function updateScheduledReport(
  id: string,
  body: ScheduledReportUpdateBody,
): Promise<ScheduledReport> {
  return apiFetch<ScheduledReport>(`/api/v1/scheduled-reports/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteScheduledReport(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/scheduled-reports/${id}`, { method: "DELETE" });
}

export const CADENCE_LABEL: Record<ScheduledReportCadence, string> = {
  daily: "Diario",
  weekly: "Semanal",
  monthly: "Mensual",
};

export const REPORT_TYPE_LABEL: Record<ScheduledReportType, string> = {
  avance: "Reporte de Avance",
  seguimiento: "Reporte de Seguimiento",
};
