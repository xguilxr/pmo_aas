import { apiFetch } from "@/lib/api";

export type ReportPeriod = "daily" | "weekly" | "monthly";
export type ReportStatus = "draft" | "sent";

export type ReportSections = Record<string, string>;

export type Report = {
  id: string;
  project_id: string;
  title: string;
  period: ReportPeriod | null;
  status: ReportStatus;
  recipients: string[];
  sections: ReportSections;
  generated_by_ai: boolean;
  created_at: string;
  sent_at: string | null;
};

export type ReportCreateBody = {
  title?: string;
  period?: ReportPeriod;
  recipients?: string[];
  sections?: ReportSections;
};

export type ReportUpdateBody = {
  title?: string;
  period?: ReportPeriod;
  recipients?: string[];
  sections?: ReportSections;
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

export function listReports(
  projectId: string,
  params: { status?: ReportStatus; period?: ReportPeriod } = {},
): Promise<Report[]> {
  return apiFetch<Report[]>(`/api/v1/projects/${projectId}/reports${qs(params)}`);
}

export function createReport(
  projectId: string,
  body: ReportCreateBody,
): Promise<Report> {
  return apiFetch<Report>(`/api/v1/projects/${projectId}/reports`, {
    method: "POST",
    body,
  });
}

export function getReport(id: string): Promise<Report> {
  return apiFetch<Report>(`/api/v1/reports/${id}`);
}

export function updateReport(id: string, body: ReportUpdateBody): Promise<Report> {
  return apiFetch<Report>(`/api/v1/reports/${id}`, { method: "PATCH", body });
}

export function deleteReport(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/reports/${id}`, { method: "DELETE" });
}

export const SECTION_LABELS: Record<string, string> = {
  resumen_ejecutivo: "Resumen Ejecutivo",
  avance_plan: "Avance del Plan",
  acciones_pendientes: "Acciones Pendientes",
  decisiones_requeridas: "Decisiones Requeridas",
  riesgos_top: "Riesgos Top",
};

export const PERIOD_LABEL: Record<ReportPeriod, string> = {
  daily: "Diario",
  weekly: "Semanal",
  monthly: "Mensual",
};
