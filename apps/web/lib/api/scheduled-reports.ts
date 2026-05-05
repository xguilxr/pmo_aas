import { apiFetch } from "@/lib/api";

export type ScheduledReportType = "avance" | "seguimiento";
export type ScheduledReportCadence = "daily" | "weekly" | "monthly" | "once";

export type ScheduledReport = {
  id: string;
  project_id: string;
  report_type: ScheduledReportType;
  cadence: ScheduledReportCadence;
  // ENH-046: opcionales según cadencia
  day_of_week: number | null;   // 0=lunes ... 6=domingo
  hour_of_day: number | null;   // 0..23
  run_at: string | null;        // ISO datetime para cadence=once
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
  day_of_week?: number | null;
  hour_of_day?: number | null;
  run_at?: string | null;
};

export type ScheduledReportUpdateBody = {
  report_type?: ScheduledReportType;
  cadence?: ScheduledReportCadence;
  recipients?: string[];
  enabled?: boolean;
  day_of_week?: number | null;
  hour_of_day?: number | null;
  run_at?: string | null;
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

/** BUG-036: dispara el envío inmediato (sin esperar la cadencia). */
export type RunNowResponse = {
  scheduled_id: string;
  queued_at: string;
  note: string;
};

export function runScheduledReportNow(id: string): Promise<RunNowResponse> {
  return apiFetch<RunNowResponse>(
    `/api/v1/scheduled-reports/${id}/run-now`,
    { method: "POST" },
  );
}

export const CADENCE_LABEL: Record<ScheduledReportCadence, string> = {
  daily: "Diario",
  weekly: "Semanal",
  monthly: "Mensual",
  once: "Una vez (fecha específica)",
};

// ENH-046: 0 = lunes ... 6 = domingo (igual que Python weekday()).
export const DAY_OF_WEEK_LABEL: Record<number, string> = {
  0: "Lunes",
  1: "Martes",
  2: "Miércoles",
  3: "Jueves",
  4: "Viernes",
  5: "Sábado",
  6: "Domingo",
};

export const DAY_OF_WEEK_SHORT: Record<number, string> = {
  0: "L",
  1: "M",
  2: "M",
  3: "J",
  4: "V",
  5: "S",
  6: "D",
};

export const REPORT_TYPE_LABEL: Record<ScheduledReportType, string> = {
  avance: "Reporte de Avance",
  seguimiento: "Reporte de Seguimiento",
};
