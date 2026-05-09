import { ApiError, apiFetch } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) {
      for (const item of v) if (item !== undefined && item !== null) usp.append(k, String(item));
    } else {
      usp.set(k, String(v));
    }
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

/* ========== RISKS ========== */
export type RiskStatus = "identified" | "analyzing" | "mitigating" | "materialized" | "closed";

export type RiskComment = {
  text: string;
  author_id?: string;
  created_at?: string;
};

/** US-064: área mínima embebida en listas de RAID. */
export type AreaMini = {
  id: string;
  name: string;
};

/** BUG-035: owner mínimo embebido en RAID detail/list. */
export type UserMini = {
  id: string;
  full_name: string | null;
  email: string;
};

export type Risk = {
  id: string;
  folio: string;
  project_id: string;
  title: string;
  description: string | null;
  category: string | null;
  probability: number | null;
  impact: number | null;
  severity: number | null;
  mitigation_strategy: string | null;
  owner_id: string | null;
  owner: UserMini | null;
  area_id: string | null;
  area: AreaMini | null;
  identified_at: string | null;
  due_date: string | null;
  status: RiskStatus;
  closure_note: string | null;
  comments: RiskComment[];
};

export type RiskCreateBody = {
  title: string;
  description?: string | null;
  category?: string | null;
  probability: number;
  impact: number;
  mitigation_strategy?: string | null;
  owner_id?: string | null;
  area_id: string; // US-064: obligatorio en creación.
  identified_at?: string | null;
  due_date?: string | null;
  status?: RiskStatus;
};

export type RiskUpdateBody = Partial<RiskCreateBody> & { closure_note?: string | null };

export function listRisks(
  projectId: string,
  params: {
    status?: RiskStatus[];
    severity_min?: number;
    severity_max?: number;
    area_id?: string;
    q?: string;
  } = {},
): Promise<Risk[]> {
  return apiFetch<Risk[]>(`/api/v1/projects/${projectId}/risks${qs(params)}`);
}

export function createRisk(projectId: string, body: RiskCreateBody): Promise<Risk> {
  return apiFetch<Risk>(`/api/v1/projects/${projectId}/risks`, { method: "POST", body });
}

export function updateRisk(id: string, body: RiskUpdateBody): Promise<Risk> {
  return apiFetch<Risk>(`/api/v1/risks/${id}`, { method: "PATCH", body });
}

export function deleteRisk(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/risks/${id}`, { method: "DELETE" });
}

/** US-058: comentarios estilo Jira sobre un riesgo. */
export function addRiskComment(id: string, body: { text: string }): Promise<Risk> {
  return apiFetch<Risk>(`/api/v1/risks/${id}/comments`, {
    method: "POST",
    body,
  });
}

export const RISK_STATUS_LABEL: Record<RiskStatus, string> = {
  identified: "Identificado",
  analyzing: "En análisis",
  mitigating: "Mitigando",
  materialized: "Materializado",
  closed: "Cerrado",
};

/* ========== ISSUES (AID) ========== */
export type IssueType = "action" | "issue" | "decision";
export type IssueStatus = "open" | "in_progress" | "resolved" | "closed";

export type IssueComment = {
  text: string;
  user_id?: string;
  at?: string;
};

export type Issue = {
  id: string;
  folio: string;
  project_id: string;
  title: string;
  description: string | null;
  type: IssueType;
  priority: number | null;
  committed_date: string | null;
  resolution: string | null;
  status: IssueStatus;
  owner_id: string | null;
  owner: UserMini | null;
  area_id: string | null;
  area: AreaMini | null;
  reported_at: string | null;
  comments: IssueComment[];
};

export type IssueCreateBody = {
  title: string;
  description?: string | null;
  type: IssueType;
  priority?: number | null;
  committed_date?: string | null;
  owner_id?: string | null;
  area_id: string; // US-064: obligatorio en creación.
  status?: IssueStatus;
};

// ENH-054: type + reported_at editables post-creación (no estaban en
// IssueCreateBody como opcionales — ya cubiertos vía Partial — pero
// reported_at no existía en Create).
export type IssueUpdateBody = Partial<IssueCreateBody> & {
  resolution?: string | null;
  reported_at?: string | null;
};

export function listIssues(
  projectId: string,
  params: {
    status?: IssueStatus[];
    type?: IssueType[];
    overdue?: boolean;
    area_id?: string;
    q?: string;
  } = {},
): Promise<Issue[]> {
  return apiFetch<Issue[]>(`/api/v1/projects/${projectId}/issues${qs(params)}`);
}

export function createIssue(projectId: string, body: IssueCreateBody): Promise<Issue> {
  return apiFetch<Issue>(`/api/v1/projects/${projectId}/issues`, { method: "POST", body });
}

export function updateIssue(id: string, body: IssueUpdateBody): Promise<Issue> {
  return apiFetch<Issue>(`/api/v1/issues/${id}`, { method: "PATCH", body });
}

export function addIssueComment(id: string, body: { text: string }): Promise<Issue> {
  return apiFetch<Issue>(`/api/v1/issues/${id}/comments`, { method: "POST", body });
}

// DEC-007: el tipo 'issue' en backend representa "Incidente" en UI (I de RAID).
export const ISSUE_TYPE_LABEL: Record<IssueType, string> = {
  action: "Acción",
  issue: "Incidente",
  decision: "Decisión",
};

export const ISSUE_STATUS_LABEL: Record<IssueStatus, string> = {
  open: "Abierta",
  in_progress: "En progreso",
  resolved: "Resuelta",
  closed: "Cerrada",
};

/* ========== CHANGE REQUESTS ========== */
export type ChangeType = "scope" | "time" | "cost" | "resource";
export type ChangeStatus = "in_review" | "approved" | "rejected" | "implemented";

export type ChangeRequest = {
  id: string;
  folio: string;
  project_id: string;
  title: string;
  description: string | null;
  type: ChangeType;
  impact: string | null;
  status: ChangeStatus;
  requested_by: string | null;
  requested_at: string;
  approved_by: string | null;
  approved_at: string | null;
  // ENH-039: usuarios resueltos para mostrar nombres en vez de UUIDs.
  requester: UserMini | null;
  approver: UserMini | null;
};

export type ChangeRequestCreateBody = {
  title: string;
  description?: string | null;
  type: ChangeType;
  impact?: string | null;
};

export function listChanges(
  projectId: string,
  params: { status?: ChangeStatus[] } = {},
): Promise<ChangeRequest[]> {
  return apiFetch<ChangeRequest[]>(`/api/v1/projects/${projectId}/change-requests${qs(params)}`);
}

export function createChange(
  projectId: string,
  body: ChangeRequestCreateBody,
): Promise<ChangeRequest> {
  return apiFetch<ChangeRequest>(`/api/v1/projects/${projectId}/change-requests`, {
    method: "POST",
    body,
  });
}

/** ENH-087: detalle dedicado de un change request. */
export function getChange(id: string): Promise<ChangeRequest> {
  return apiFetch<ChangeRequest>(`/api/v1/change-requests/${id}`);
}

export type ChangeRequestUpdateBody = {
  title?: string;
  description?: string | null;
  impact?: string | null;
};

export function updateChange(id: string, body: ChangeRequestUpdateBody): Promise<ChangeRequest> {
  return apiFetch<ChangeRequest>(`/api/v1/change-requests/${id}`, {
    method: "PATCH",
    body,
  });
}

export function approveChange(id: string, body?: { comment?: string }): Promise<ChangeRequest> {
  return apiFetch<ChangeRequest>(`/api/v1/change-requests/${id}/approve`, {
    method: "POST",
    body: body ?? {},
  });
}

export function rejectChange(id: string, body: { comment: string }): Promise<ChangeRequest> {
  return apiFetch<ChangeRequest>(`/api/v1/change-requests/${id}/reject`, {
    method: "POST",
    body,
  });
}

export const CHANGE_TYPE_LABEL: Record<ChangeType, string> = {
  scope: "Alcance",
  time: "Tiempo",
  cost: "Costo",
  resource: "Recursos",
};

export const CHANGE_STATUS_LABEL: Record<ChangeStatus, string> = {
  in_review: "En revisión",
  approved: "Aprobado",
  rejected: "Rechazado",
  implemented: "Implementado",
};

/* ========== DOCUMENTS ========== */
export type DocumentCategory =
  | "charter"
  | "plan"
  | "raid_export"
  | "transcript"
  | "minute"
  | "report"
  | "lesson"
  | "contract"
  | "other";

export type ProjectDocument = {
  id: string;
  folio: string;
  project_id: string;
  title: string;
  description: string | null;
  category: DocumentCategory | null;
  file_url: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  version: number;
  is_current: boolean;
  status: string;
};

export type DocumentCreateBody = {
  title: string;
  description?: string | null;
  category?: DocumentCategory | null;
  file_url: string;
  mime_type: string;
  size_bytes: number;
};

export function listDocuments(projectId: string): Promise<ProjectDocument[]> {
  return apiFetch<ProjectDocument[]>(`/api/v1/projects/${projectId}/documents`);
}

export function createDocument(
  projectId: string,
  body: DocumentCreateBody,
): Promise<ProjectDocument> {
  return apiFetch<ProjectDocument>(`/api/v1/projects/${projectId}/documents`, {
    method: "POST",
    body,
  });
}

/**
 * BUG-034: pide al backend la URL de descarga.
 * - mode="presigned": URL firmada de R2/S3 (5 min) — abrir directo.
 * - mode="stream": backend local — usar fetch con Bearer + Blob.
 */
export type DocumentDownloadInfo = {
  mode: "presigned" | "stream";
  url: string;
  expires_at: string | null;
};

/**
 * Extrae el filename de un header `Content-Disposition`.
 * Acepta `filename*=UTF-8''<encoded>` (RFC 5987) y el simple `filename="..."`,
 * con preferencia por la versión UTF-8.
 *
 * Devuelve `null` si no encuentra nada parseable.
 */
function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const utf8 = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header);
  if (utf8 && utf8[1]) {
    try {
      return decodeURIComponent(utf8[1].trim());
    } catch {
      // ignora errores de decode y cae al filename simple
    }
  }
  const simple = /filename\s*=\s*"?([^";]+)"?/i.exec(header);
  if (simple && simple[1]) return simple[1].trim();
  return null;
}

export function getDocumentDownloadUrl(
  documentId: string,
): Promise<DocumentDownloadInfo> {
  return apiFetch<DocumentDownloadInfo>(
    `/api/v1/documents/${documentId}/download-url`,
  );
}

/**
 * Helper que abre un documento: usa presigned cuando está disponible
 * (S3/R2) o cae a fetch+blob para backend local. Maneja errores de
 * red mostrando un alert.
 */
export async function openDocumentForDownload(
  documentId: string,
): Promise<void> {
  try {
    const info = await getDocumentDownloadUrl(documentId);
    if (info.mode === "presigned") {
      // R2/S3 ya incluye Content-Disposition en la URL firmada.
      window.open(info.url, "_blank", "noopener,noreferrer");
      return;
    }
    // Backend local — el endpoint /download exige Bearer. Hacemos
    // fetch + blob para evitar el problema del <a href> sin auth.
    const { apiBase } = await import("@/lib/api");
    const { getAccessToken } = await import("@/lib/auth-storage");
    const token = getAccessToken();
    const res = await fetch(`${apiBase()}${info.url}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      throw new Error(`Falló la descarga (HTTP ${res.status})`);
    }
    const blob = await res.blob();
    // BUG: con `a.download = ""` el browser cae al filename de la URL.
    // En `blob:` URLs no hay filename → Chrome guesses `.file`. Hay que
    // parsear `Content-Disposition` y settear `a.download` al filename
    // real (con extensión) para que se descargue correctamente.
    const filename =
      parseContentDispositionFilename(res.headers.get("content-disposition")) ??
      "documento";
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 5_000);
  } catch (err) {
    const msg =
      err instanceof Error ? err.message : "No se pudo abrir el documento";
    window.alert(msg);
  }
}

export const DOC_CATEGORY_LABEL: Record<DocumentCategory, string> = {
  charter: "Project Charter",
  plan: "Plan",
  raid_export: "Export RAID",
  transcript: "Transcripción",
  minute: "Minuta",
  report: "Reporte",
  lesson: "Lección",
  contract: "Contrato",
  other: "Otro",
};

/* ========== LESSONS ========== */
export type LessonCategory = "success" | "improvement" | "error";

export type Lesson = {
  id: string;
  folio: string;
  project_id: string;
  title: string;
  description: string | null;
  category: LessonCategory | null;
  phase: string | null;
  recommendation: string | null;
  tags: string[];
  status: string;
};

export type LessonCreateBody = {
  title: string;
  description?: string | null;
  category: LessonCategory;
  phase?: string | null;
  recommendation?: string | null;
  tags?: string[];
};

export function listLessons(params: {
  project_id?: string;
  organization_id?: string;
  category?: LessonCategory;
  tag?: string;
  q?: string;
} = {}): Promise<Lesson[]> {
  return apiFetch<Lesson[]>(`/api/v1/lessons${qs(params)}`);
}

export function createLesson(projectId: string, body: LessonCreateBody): Promise<Lesson> {
  return apiFetch<Lesson>(`/api/v1/projects/${projectId}/lessons`, { method: "POST", body });
}

/** ENH-086: detalle dedicado de una lección. */
export function getLesson(lessonId: string): Promise<Lesson> {
  return apiFetch<Lesson>(`/api/v1/lessons/${lessonId}`);
}

export type LessonUpdateBody = {
  title?: string;
  description?: string | null;
  category?: LessonCategory;
  phase?: string | null;
  recommendation?: string | null;
  tags?: string[];
};

export function updateLesson(lessonId: string, body: LessonUpdateBody): Promise<Lesson> {
  return apiFetch<Lesson>(`/api/v1/lessons/${lessonId}`, { method: "PATCH", body });
}

export const LESSON_CATEGORY_LABEL: Record<LessonCategory, string> = {
  success: "Éxito",
  improvement: "Mejora",
  error: "Error",
};

/* ========== MEETING MINUTES ========== */
export type MinuteAgreement = {
  description: string;
  owner_id?: string | null;
  due_date?: string | null;
  status?: string | null;
};

export type MinuteParticipant = {
  user_id?: string;
  name: string;
  email?: string;
};

export type MinuteTopic = {
  title: string;
  notes: string;
};

export type MeetingMinute = {
  id: string;
  folio: string;
  project_id: string;
  title: string;
  meeting_date: string;
  participants: MinuteParticipant[];
  topics: MinuteTopic[];
  agreements: MinuteAgreement[];
  next_meeting_date: string | null;
  attachments: { name?: string; url: string }[];
  generated_by_ai: boolean;
  status: string;
};

export type MinuteCreateBody = {
  title: string;
  meeting_date: string;
  participants?: MinuteParticipant[];
  topics?: MinuteTopic[];
  agreements?: MinuteAgreement[];
  next_meeting_date?: string | null;
  attachments?: { name?: string; url: string }[];
  generated_by_ai?: boolean;
};

export function listMinutes(projectId: string): Promise<MeetingMinute[]> {
  return apiFetch<MeetingMinute[]>(`/api/v1/projects/${projectId}/meeting-minutes`);
}

export function createMinute(
  projectId: string,
  body: MinuteCreateBody,
): Promise<MeetingMinute> {
  return apiFetch<MeetingMinute>(`/api/v1/projects/${projectId}/meeting-minutes`, {
    method: "POST",
    body,
  });
}

export function convertAgreement(
  minuteId: string,
  agreementIndex: number,
): Promise<{ issue_id: string }> {
  return apiFetch<{ issue_id: string }>(
    `/api/v1/meeting-minutes/${minuteId}/convert-agreement`,
    { method: "POST", body: { agreement_index: agreementIndex } },
  );
}

export type MinuteExportFormat = "pdf" | "docx" | "md" | "txt";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

/**
 * US-040: descarga la minuta en el formato seleccionado. Usa fetch
 * directo + Blob porque apiFetch sólo maneja JSON.
 */
export async function exportMinute(
  minuteId: string,
  format: MinuteExportFormat,
): Promise<void> {
  if (!API_URL) {
    throw new ApiError(0, "NETWORK_ERROR", "NEXT_PUBLIC_API_URL no está configurada");
  }
  const base = API_URL.replace(/\/+$/, "");
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(
    `${base}/api/v1/meeting-minutes/${minuteId}/export?format=${format}`,
    { method: "GET", headers, credentials: "include" },
  );
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    let code = "UNKNOWN";
    try {
      const data = (await res.json()) as {
        detail?: { detail?: string; code?: string };
      };
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
  const filename = match?.[1] ?? `minuta.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
