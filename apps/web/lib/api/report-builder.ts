/**
 * API client del Report Builder — US-123/124/125/126/130 (EP020).
 *
 * - `listSections` — catálogo global de secciones atómicas (S-XX).
 * - `listBuilderTemplates` — plantillas seed + plantillas del tenant.
 * - `renderBuilder` — preview en vivo (JSON o HTML).
 * - `exportBuilderPdf` — descarga PDF del template renderizado.
 * - `createBuilderTemplate` — guardar plantilla (US-126).
 */
import { apiFetch, apiBase } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";

export type SectionCategory =
  | "HDR"
  | "EST"
  | "AVN"
  | "PLN"
  | "RAID"
  | "EQP"
  | "NAR"
  | "KPI"
  | "PRT";

export type ReportSection = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category: SectionCategory;
  level: number;
  data_shape: Record<string, unknown>;
  parameters_schema: Record<string, unknown>;
  composition_mode_default: "A" | "B";
  supports_ia: boolean;
  enabled: boolean;
};

export type TemplateVisibility = "private" | "project" | "tenant";

export type ReportBuilderTemplate = {
  id: string;
  tenant_id: string | null;
  code: string;
  name: string;
  description: string | null;
  level: number;
  composition_mode: "A" | "B";
  section_codes: string[];
  default_parameters: Record<string, Record<string, unknown>>;
  is_seed: boolean;
  owner_id: string | null;
  project_id: string | null;
  visibility: TemplateVisibility;
  created_at: string;
  updated_at: string;
};

export type RenderRequest = {
  template: string;
  project_id?: string | null;
  organization_id?: string | null;
  program_id?: string | null;
  level?: number;
  /** El corte se define automáticamente al generar (hoy); el builder ya
   *  no lo pide en la plantilla. Sigue opcional para compat con export. */
  cut_off_date?: string | null;
  window_days?: number;
  /** BUG-063: filtro de área a nivel reporte (barra superior). */
  area_id?: string | null;
  params?: Record<string, Record<string, unknown>>;
};

export type RenderResponse = {
  html: string;
  json: Record<string, unknown>;
  sections_meta: Array<{
    code: string;
    name: string;
    category: string | null;
    template: string;
  }>;
};

export function listSections(opts: { level?: number; category?: string } = {}): Promise<ReportSection[]> {
  const usp = new URLSearchParams();
  if (opts.level) usp.set("level", String(opts.level));
  if (opts.category) usp.set("category", opts.category);
  const q = usp.toString();
  return apiFetch(`/api/v1/report-sections${q ? `?${q}` : ""}`);
}

export function listBuilderTemplates(opts: { level?: number } = {}): Promise<ReportBuilderTemplate[]> {
  const usp = new URLSearchParams();
  if (opts.level) usp.set("level", String(opts.level));
  const q = usp.toString();
  return apiFetch(`/api/v1/report-builder-templates${q ? `?${q}` : ""}`);
}

export function renderBuilder(body: RenderRequest, format: "json" | "pdf" = "json"): Promise<RenderResponse> {
  return apiFetch(`/api/v1/report-builder/render?format=${format}`, {
    method: "POST",
    body,
  });
}

/** Descarga binaria del PDF — bypass `apiFetch` para tener `blob()`. */
export async function exportBuilderPdf(
  templateId: string,
  body: Omit<RenderRequest, "template">
): Promise<Blob> {
  const token = getAccessToken();
  const res = await fetch(
    `${apiBase()}/api/v1/report-builder/templates/${templateId}/export?format=pdf`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/pdf",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Export PDF falló (${res.status}): ${txt.slice(0, 200)}`);
  }
  return res.blob();
}

/** US-126 — crear plantilla custom (private/project visibility). */
export type CreateBuilderTemplateBody = {
  code: string;
  name: string;
  description?: string | null;
  level: number;
  composition_mode: "A" | "B";
  section_codes: string[];
  default_parameters?: Record<string, Record<string, unknown>>;
  visibility?: "private" | "project";
  project_id?: string | null;
};

export function createBuilderTemplate(body: CreateBuilderTemplateBody): Promise<ReportBuilderTemplate> {
  return apiFetch(`/api/v1/report-builder-templates`, {
    method: "POST",
    body,
  });
}

export function updateBuilderTemplate(
  id: string,
  body: Partial<CreateBuilderTemplateBody>
): Promise<ReportBuilderTemplate> {
  return apiFetch(`/api/v1/report-builder-templates/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteBuilderTemplate(id: string): Promise<void> {
  return apiFetch(`/api/v1/report-builder-templates/${id}`, { method: "DELETE" });
}

/** US-127 — chat IA conversacional. */
export type ChatAction = {
  type:
    | "add_section"
    | "remove_section"
    | "update_section_params"
    | "reorder_section"
    | "no_op";
  code?: string | null;
  index?: number | null;
  to?: number | null;
  params?: Record<string, unknown> | null;
};

export type ChatRequest = {
  user_message: string;
  canvas_codes: string[];
  composition_mode: "A" | "B";
  history?: Array<{ role: "user" | "assistant" | "system"; content: string }>;
};

export type ChatResponse = {
  message: string;
  actions: ChatAction[];
  raw_output: string | null;
};

export function chatWithBuilder(body: ChatRequest): Promise<ChatResponse> {
  return apiFetch(`/api/v1/report-builder/ai-chat`, { method: "POST", body });
}

/** US-131 — crear suscripción del Report Builder (report_type='custom'). */
export type ScheduleCustomBody = {
  cadence: "daily" | "weekly" | "monthly" | "once";
  recipients: string[];
  day_of_week?: number | null;
  hour_of_day?: number | null;
  day_of_month?: number | null;
  run_at?: string | null;
  report_builder_template_id: string;
  enabled?: boolean;
};

export function createCustomSchedule(
  projectId: string,
  body: ScheduleCustomBody
): Promise<unknown> {
  return apiFetch(`/api/v1/projects/${projectId}/scheduled-reports`, {
    method: "POST",
    body: { ...body, report_type: "custom" },
  });
}
