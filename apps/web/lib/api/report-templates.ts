import { apiFetch } from "@/lib/api";

/**
 * ENH-085 — plantillas tenant-shared para reportes HTML.
 *
 * Distinto de `ai_report_templates` (per-project, config wizard de IA).
 * Aquí guardamos `html_content` final tweakeado para reusar como base
 * en otros proyectos.
 */

export type ReportTemplateMini = {
  id: string;
  name: string;
  description: string | null;
  is_shared: boolean;
  created_by: string | null;
  created_at: string;
  last_used_at: string | null;
};

export type ReportTemplate = ReportTemplateMini & {
  tenant_id: string;
  html_content: string;
};

export type ReportTemplateCreateBody = {
  name: string;
  description?: string | null;
  html_content: string;
  is_shared?: boolean;
};

export type ReportTemplateUpdateBody = {
  name?: string;
  description?: string | null;
  html_content?: string;
  is_shared?: boolean;
};

export function listReportTemplates(): Promise<ReportTemplateMini[]> {
  return apiFetch<ReportTemplateMini[]>(`/api/v1/report-templates`);
}

export function createReportTemplate(
  body: ReportTemplateCreateBody,
): Promise<ReportTemplate> {
  return apiFetch<ReportTemplate>(`/api/v1/report-templates`, {
    method: "POST",
    body,
  });
}

export function getReportTemplate(id: string): Promise<ReportTemplate> {
  return apiFetch<ReportTemplate>(`/api/v1/report-templates/${id}`);
}

export function updateReportTemplate(
  id: string,
  body: ReportTemplateUpdateBody,
): Promise<ReportTemplate> {
  return apiFetch<ReportTemplate>(`/api/v1/report-templates/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteReportTemplate(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/report-templates/${id}`, { method: "DELETE" });
}
