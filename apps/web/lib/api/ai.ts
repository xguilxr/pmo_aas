import { apiFetch } from "@/lib/api";

export type AIMinutePayload = {
  summary: string;
  participants: { name: string; role?: string }[];
  topics: { title: string; notes: string }[];
  agreements: { description: string; owner?: string; due_date?: string }[];
  decisions: { description: string; rationale?: string }[];
  next_steps: { action: string; owner?: string; due_date?: string }[];
  risks_blockers: { description: string }[];
};

export type GenerateMinuteResult = {
  job_id: string;
  status: string;
  model: string;
  output: AIMinutePayload;
  minute_id: string | null;
};

export function generateMinute(body: {
  project_id: string;
  transcript: string;
  language?: string;
  save_as_minute?: boolean;
  title?: string;
}): Promise<GenerateMinuteResult> {
  return apiFetch<GenerateMinuteResult>("/api/v1/ai/minutes", { method: "POST", body });
}

export type AIJobRead = {
  id: string;
  status: string;
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

export type ReportDraftResult = {
  report_id: string;
  sections: ReportSections;
  model: string;
};

export function draftReport(
  projectId: string,
  body: { recipients?: string[] } = {},
): Promise<ReportDraftResult> {
  return apiFetch<ReportDraftResult>(
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
