import { apiBase, apiFetch, ApiError } from "@/lib/api";

/** BUG-063: shape canónico de un item RAID sugerido (4 tipos comparten). */
export type AIRaidSuggestion = {
  short_desc: string;
  suggested_owner_name?: string | null;
  suggested_priority?: number | null;
  suggested_due_date?: string | null;
  raw_quote?: string | null;
};

/** BUG-063: 4 buckets canónicos A/R/D/I alineados con el modelo RAID. */
export type AIRaidBlock = {
  actions: AIRaidSuggestion[];
  risks: AIRaidSuggestion[];
  decisions: AIRaidSuggestion[];
  issues: AIRaidSuggestion[];
};

export const EMPTY_RAID_BLOCK: AIRaidBlock = {
  actions: [],
  risks: [],
  decisions: [],
  issues: [],
};

export type AIParticipant = {
  name: string;
  role?: string | null;
  area?: string | null;
  attendance?: "attended" | "absent_justified" | "absent_unjustified";
};

export type AITopic = {
  title: string;
  bullets?: string[];
  /** Legacy: minutas viejas usaban `notes`. */
  notes?: string;
};

export type AIMinutePayload = {
  header?: Record<string, unknown>;
  summary: string;
  participants: AIParticipant[];
  topics: AITopic[];
  /** Legacy: agregaciones del modelo viejo, sigue vacío en el nuevo flow. */
  agreements?: unknown[];
  free_notes?: string | null;
  /** BUG-063: shape `raid_suggestions` con 4 buckets A/R/D/I. */
  raid_suggestions?: AIRaidBlock;
  /** Legacy alias — algunos consumers leen `raid` directo. */
  raid?: AIRaidBlock;
  minute_id?: string | null;
};

export type AIJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export type DispatchResult = {
  job_id: string;
  status: AIJobStatus;
};

// US-143 — generador unificado: 3 source_types.
// - `manual` retorna {minute_id, status:"saved", folio} sincrónico (no dispatch).
// - `transcript|minute` retornan {job_id, status:"queued"} (dispatch async).
export type MinuteSourceType = "transcript" | "minute" | "manual";

export type ManualSaveResult = {
  minute_id: string;
  status: "saved";
  folio: string;
};

export type ManualMinuteData = {
  header?: {
    title?: string | null;
    date?: string | null;
    time?: string | null;
    duration?: string | null;
    modality?: string | null;
    location?: string | null;
    facilitator?: string | null;
  };
  participants?: {
    attendees?: { name: string; role?: string; area?: string }[];
    absent_justified?: { name: string; role?: string; area?: string }[];
    absent_unjustified?: { name: string; role?: string; area?: string }[];
  };
  summary?: string;
  topics?: { title: string; bullets?: string[]; notes?: string }[];
  agreements?: { description: string; owner?: string; due_date?: string }[];
  raid?: unknown[];
  free_notes?: string | null;
};

/**
 * US-051 + US-143: dispatch a Celery (transcript/minute) o persiste directo
 * (manual). El frontend discrimina por `body.status`/`body.job_id` en la
 * respuesta.
 */
export function generateMinute(body: {
  project_id: string;
  source_type?: MinuteSourceType;
  transcript?: string;
  structured_data?: ManualMinuteData;
  language?: string;
  save_as_minute?: boolean;
  title?: string;
}): Promise<DispatchResult | ManualSaveResult> {
  return apiFetch<DispatchResult | ManualSaveResult>(
    "/api/v1/ai/minutes",
    { method: "POST", body },
  );
}

/**
 * BUG-083: extrae texto plano de un archivo subido (.docx / texto) server-side.
 * El `file.text()` del navegador sobre un .docx (un ZIP binario) producía
 * basura que la IA rechazaba con 400; ahora python-docx lo procesa en backend.
 * Se usa `fetch` directo porque `apiFetch` siempre serializa JSON.
 */
export async function extractMinuteText(
  file: File,
): Promise<{ text: string; filename: string | null; chars: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const headers: Record<string, string> = { Accept: "application/json" };
  let res: Response;
  try {
    res = await fetch(`${apiBase()}/api/v1/ai/extract-text`, {
      method: "POST",
      body: formData,
      headers,
      credentials: "include",
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "No se pudo conectar con el servidor");
  }
  const data = await res.json().catch(() => ({}) as Record<string, unknown>);
  if (!res.ok) {
    const detail = (data as Record<string, unknown>).detail;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" && detail !== null
          ? String(
              (detail as Record<string, unknown>).message ??
                (detail as Record<string, unknown>).detail ??
                "No se pudo extraer el texto del archivo",
            )
          : "No se pudo extraer el texto del archivo";
    throw new ApiError(res.status, "extract_failed", message);
  }
  return data as { text: string; filename: string | null; chars: number };
}

export type AIJobRead = {
  id: string;
  status: AIJobStatus;
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  duration_ms: number | null;
  output: unknown;
  error: string | null;
};

export function getAIJob(jobId: string): Promise<AIJobRead> {
  return apiFetch<AIJobRead>(`/api/v1/ai/jobs/${jobId}`);
}

/**
 * BUG-055: marca el job como cancelado en el backend. El worker, al
 * llegar a la fase de persistencia, detecta el flag y omite el guardado
 * para evitar minutas huérfanas. La UI deja de hacer polling tras este
 * call.
 */
export function cancelAIJob(jobId: string): Promise<{ id: string; status: string }> {
  return apiFetch<{ id: string; status: string }>(
    `/api/v1/ai/jobs/${jobId}/cancel`,
    { method: "POST" },
  );
}

/** US-109 — tweaker IA del HTML del reporte. */
export type TweakHTMLBody = {
  current_html: string;
  instruction: string;
};

export type TweakHTMLResult = {
  html: string;
  model: string | null;
};

export function tweakReportHTML(body: TweakHTMLBody): Promise<TweakHTMLResult> {
  return apiFetch<TweakHTMLResult>(`/api/v1/ai/reports/tweak-html`, {
    method: "POST",
    body,
  });
}

export type ReportSections = {
  executive_summary?: string;
  achievements?: string[] | string;
  next_activities?: string[] | string;
  top_risks?: Array<{ title: string; severity?: number; status?: string }>;
  budget_status?: Record<string, unknown>;
};

export type ReportJobOutput = {
  report_id: string;
  sections: ReportSections;
};

export function draftReport(
  projectId: string,
  body: { recipients?: string[] } = {},
): Promise<DispatchResult> {
  return apiFetch<DispatchResult>(
    `/api/v1/ai/projects/${projectId}/reports/draft`,
    { method: "POST", body },
  );
}

export type SendReportResult = {
  ok: boolean;
  sent_at: string;
  recipients: string[];
};

export function sendReport(
  reportId: string,
  body: { recipients: string[]; include_pdf?: boolean; subject?: string },
): Promise<SendReportResult> {
  return apiFetch<SendReportResult>(`/api/v1/ai/reports/${reportId}/send`, {
    method: "POST",
    body,
  });
}
