import { apiFetch } from "@/lib/api";

/** ENH-084: shape canónico de un item RAID sugerido (4 tipos comparten). */
export type AIRaidSuggestion = {
  short_desc: string;
  suggested_owner_name?: string | null;
  suggested_priority?: number | null;
  raw_quote?: string | null;
};

export type AIRaidBlock = {
  risks: AIRaidSuggestion[];
  issues: AIRaidSuggestion[];
  lessons: AIRaidSuggestion[];
  changes: AIRaidSuggestion[];
};

export const EMPTY_RAID_BLOCK: AIRaidBlock = {
  risks: [],
  issues: [],
  lessons: [],
  changes: [],
};

export type AIMinutePayload = {
  summary: string;
  participants: { name: string; role?: string }[];
  topics: { title: string; notes: string }[];
  agreements: { description: string; owner?: string; due_date?: string }[];
  decisions: { description: string; rationale?: string }[];
  next_steps: { action: string; owner?: string; due_date?: string }[];
  risks_blockers: { description: string }[];
  /** ENH-084: 4 secciones RAID estandarizadas. */
  raid?: AIRaidBlock;
  minute_id?: string | null;
};

export type AIJobStatus = "queued" | "running" | "succeeded" | "failed";

export type DispatchResult = {
  job_id: string;
  status: AIJobStatus;
};

/**
 * US-051: dispatch a Celery. Devuelve 202 con {job_id, status}.
 * La UI debe hacer polling con `pollAIJob` (o el hook `useAIJobPolling`)
 * hasta status=succeeded|failed.
 */
export function generateMinute(body: {
  project_id: string;
  transcript: string;
  language?: string;
  save_as_minute?: boolean;
  title?: string;
}): Promise<DispatchResult> {
  return apiFetch<DispatchResult>("/api/v1/ai/minutes", { method: "POST", body });
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
