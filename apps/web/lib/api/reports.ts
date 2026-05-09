import { ApiError, apiFetch } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";

export type ReportPeriod = "daily" | "weekly" | "monthly";
export type ReportStatus = "draft" | "sent";

export type ReportSections = Record<string, string>;

export type ReportGenerator = "manual" | "ai" | "avance" | "seguimiento";

export type Report = {
  id: string;
  project_id: string;
  title: string;
  period: ReportPeriod | null;
  status: ReportStatus;
  recipients: string[];
  sections: ReportSections;
  generated_by_ai: boolean;
  generator?: ReportGenerator;
  cut_off_date?: string | null;
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
 * Solicita un PDF al backend. Retorna un Blob con el PDF y el filename
 * extraído del Content-Disposition. Lanza ApiError para respuestas no 2xx.
 */
async function fetchPdfFromEndpoint(
  path: string,
  body: unknown | undefined,
  method: "GET" | "POST",
): Promise<{ blob: Blob; filename: string }> {
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
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  const plainMatch = /filename="?([^";]+)"?/i.exec(disposition);
  const filename = utf8Match
    ? decodeURIComponent(utf8Match[1])
    : (plainMatch?.[1] ?? "reporte.pdf");
  return { blob, filename };
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
  const { blob, filename } = await fetchPdfFromEndpoint(path, body, method);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * ENH-014: abre el PDF inline en una pestaña nueva para preview sin
 * forzar descarga. Retorna sin hacer nada si la pestaña es bloqueada.
 */
async function previewPdfFromEndpoint(
  path: string,
  body?: unknown,
  method: "GET" | "POST" = "GET",
): Promise<void> {
  const { blob } = await fetchPdfFromEndpoint(path, body, method);
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank", "noopener,noreferrer");
  if (!win) {
    URL.revokeObjectURL(url);
    throw new ApiError(
      0,
      "POPUP_BLOCKED",
      "El navegador bloqueó la ventana. Permite pop-ups para ver el preview.",
    );
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** US-038: genera Reporte de Avance y descarga el PDF resultante. */
export function generateAvanceReport(
  projectId: string,
  cutOffDate?: string,
  // ENH-063.
  periodDays?: number,
): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/projects/${projectId}/reports/avance`,
    { cut_off_date: cutOffDate ?? null, period_days: periodDays ?? null },
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

/** US-039: genera Reporte de Seguimiento y descarga el PDF. */
export function generateSeguimientoReport(
  projectId: string,
  cutOffDate?: string,
  windowDays = 14,
  // ENH-063: si periodDays viene, sobreescribe windowDays.
  periodDays?: number,
): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/projects/${projectId}/reports/seguimiento`,
    {
      cut_off_date: cutOffDate ?? null,
      window_days: windowDays,
      period_days: periodDays ?? null,
    },
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

/** ENH-014: preview (inline) de un Reporte de Avance generado. */
export function previewAvanceReport(reportId: string): Promise<void> {
  return previewPdfFromEndpoint(
    `/api/v1/reports/${reportId}/avance/download?inline=true`,
  );
}

/** ENH-014: preview (inline) de un Reporte de Seguimiento generado. */
export function previewSeguimientoReport(reportId: string): Promise<void> {
  return previewPdfFromEndpoint(
    `/api/v1/reports/${reportId}/seguimiento/download?inline=true`,
  );
}

/**
 * ENH-055 fase 2: genera el reporte template y lo abre inline (preview).
 * El backend persiste a ReportHistory automáticamente (US-092).
 */
export function previewAvanceTemplate(
  projectId: string,
  cutOffDate?: string,
  // ENH-063: período canónico (1/7/14/30/90 días).
  periodDays?: number,
): Promise<void> {
  return previewPdfFromEndpoint(
    `/api/v1/projects/${projectId}/reports/avance`,
    { cut_off_date: cutOffDate ?? null, period_days: periodDays ?? null },
    "POST",
  );
}

export function previewSeguimientoTemplate(
  projectId: string,
  period?: string,
  // ENH-063.
  periodDays?: number,
): Promise<void> {
  return previewPdfFromEndpoint(
    `/api/v1/projects/${projectId}/reports/seguimiento`,
    {
      period: period ?? null,
      period_days: periodDays ?? null,
    },
    "POST",
  );
}

// ===========================================================================
// US-092 — Historial de reportes generados (manual + scheduler).
// ===========================================================================

export type ReportHistoryItem = {
  id: string;
  project_id: string;
  report_type: "avance" | "seguimiento" | string;
  generated_at: string;
  generated_by_user_id: string | null;
  file_size_bytes: number | null;
  scheduled_report_id: string | null;
  source_report_id: string | null;
  generated_by_name: string | null;
};

export function listReportHistory(
  projectId: string,
): Promise<ReportHistoryItem[]> {
  return apiFetch<ReportHistoryItem[]>(
    `/api/v1/projects/${projectId}/report-history`,
  );
}

export function downloadReportHistory(historyId: string): Promise<void> {
  return downloadPdfFromEndpoint(
    `/api/v1/report-history/${historyId}/download`,
    undefined,
    "GET",
  );
}

export function previewReportHistory(historyId: string): Promise<void> {
  return previewPdfFromEndpoint(
    `/api/v1/report-history/${historyId}/download?inline=true`,
  );
}

// ENH-081 — house-keeping: borrar entry del historial.
export function deleteReportHistory(historyId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/report-history/${historyId}`, {
    method: "DELETE",
  });
}

// US-111 rework: abre el HTML interactivo (con filtros vanilla JS) en
// una tab nueva. Requiere que el reporte tenga `html_content` o que
// regenere on-the-fly (export endpoint hace ambos).
export async function previewReportHtml(reportId: string): Promise<void> {
  const token = getAccessToken();
  const headers: Record<string, string> = { Accept: "text/html" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(
    `${apiBase()}/api/v1/reports/${reportId}/export?format=html&inline=true`,
    {
      method: "GET",
      headers,
      credentials: "include",
    },
  );
  if (!res.ok) {
    throw new ApiError(res.status, "PREVIEW_FAILED", `HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank", "noopener,noreferrer");
  if (!win) {
    URL.revokeObjectURL(url);
    throw new ApiError(0, "POPUP_BLOCKED", "Permite pop-ups para ver el HTML.");
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

// US-093 — Reportes: creación con IA + preview.
export type AIReportGenerateBody = {
  base?: "avance" | "seguimiento" | "custom";
  period_end?: string | null;
  include_kpis?: boolean;
  include_tasks?: boolean;
  include_raid?: boolean;
  include_milestones?: boolean;
  free_notes?: string;
  save_to_history?: boolean;
  // ENH-071: filtros configurables sobre el listado del reporte.
  date_from?: string | null;
  date_to?: string | null;
  area_ids?: string[] | null;
  assignee_actor_ids?: string[] | null;
  criticalities?: string[] | null;
  statuses?: string[] | null;
  severities?: string[] | null;
};

export type AIReportGenerateResponse = {
  html: string;
  history_id: string | null;
};

export function aiGenerateReport(
  projectId: string,
  body: AIReportGenerateBody,
): Promise<AIReportGenerateResponse> {
  return apiFetch<AIReportGenerateResponse>(
    `/api/v1/projects/${projectId}/reports/ai-generate`,
    { method: "POST", body },
  );
}

// ENH-080 — Plantillas reusables del reporte IA.
export type AIReportTemplateConfig = {
  include_kpis?: boolean;
  include_tasks?: boolean;
  include_raid?: boolean;
  include_milestones?: boolean;
  free_notes?: string;
  area_ids?: string[] | null;
  assignee_actor_ids?: string[] | null;
  criticalities?: string[] | null;
  statuses?: string[] | null;
  severities?: string[] | null;
  date_from?: string | null;
  date_to?: string | null;
};

export type AIReportTemplate = {
  id: string;
  project_id: string;
  name: string;
  base: "avance" | "seguimiento" | "custom";
  config: AIReportTemplateConfig;
  created_by: string | null;
  created_at: string;
};

export function listAIReportTemplates(
  projectId: string,
): Promise<AIReportTemplate[]> {
  return apiFetch<AIReportTemplate[]>(
    `/api/v1/projects/${projectId}/ai-report-templates`,
  );
}

export function createAIReportTemplate(
  projectId: string,
  body: { name: string; base: "avance" | "seguimiento" | "custom"; config: AIReportTemplateConfig },
): Promise<AIReportTemplate> {
  return apiFetch<AIReportTemplate>(
    `/api/v1/projects/${projectId}/ai-report-templates`,
    { method: "POST", body },
  );
}

export function deleteAIReportTemplate(templateId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/ai-report-templates/${templateId}`, {
    method: "DELETE",
  });
}
