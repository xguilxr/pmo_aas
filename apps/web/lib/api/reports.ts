import { ApiError, apiFetch } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";

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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function apiBase(): string {
  if (!API_URL) {
    throw new ApiError(0, "NETWORK_ERROR", "NEXT_PUBLIC_API_URL no está configurada");
  }
  return API_URL.replace(/\/+$/, "");
}

/**
 * Descarga un PDF desde un endpoint del backend. Lanza ApiError para
 * respuestas no 2xx y dispara la descarga en el browser en caso de éxito.
 */
async function downloadPdfFromEndpoint(
  path: string,
  body: unknown | undefined,
  method: "GET" | "POST",
): Promise<void> {
  const token = getAccessToken();
  const headers: Record<string, string> = { Accept: "application/pdf" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${apiBase()}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "include",
  });
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    let code = "UNKNOWN";
    try {
      const data = (await res.json()) as { detail?: { detail?: string; code?: string } };
      detail = data.detail?.detail ?? detail;
      code = data.detail?.code ?? code;
    } catch {
      /* noop */
    }
    throw new ApiError(res.status, code, detail);
  }

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? "reporte.pdf";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** US-NEW-038: genera Reporte de Avance y descarga el PDF resultante. */
export function generateAvanceReport(
  projectId: string,
  cutOffDate?: string,
): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/projects/${projectId}/reports/avance`,
    { cut_off_date: cutOffDate ?? null },
    "POST",
  );
}

export function downloadAvanceReport(reportId: string): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/reports/${reportId}/avance/download`,
    undefined,
    "GET",
  );
}

/** US-NEW-039: genera Reporte de Seguimiento y descarga el PDF. */
export function generateSeguimientoReport(
  projectId: string,
  cutOffDate?: string,
  windowDays = 14,
): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/projects/${projectId}/reports/seguimiento`,
    { cut_off_date: cutOffDate ?? null, window_days: windowDays },
    "POST",
  );
}

export function downloadSeguimientoReport(reportId: string): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/reports/${reportId}/seguimiento/download`,
    undefined,
    "GET",
  );
}
