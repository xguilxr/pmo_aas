import { ApiError, apiFetch } from "@/lib/api";

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

/* ========== RAID STATUS (US-179) ========== */
// Estados unificados a 4 para riesgos e incidencias. On-hold captura razón +
// dependencia (área/responsable) + tiempo detenido.
export type RaidStatus = "open" | "in_progress" | "on_hold" | "resolved";

export const RAID_STATUS_LABEL: Record<RaidStatus, string> = {
  open: "Abierto",
  in_progress: "En Progreso",
  on_hold: "On Hold / Detenido",
  resolved: "Resuelto",
};

// BUG-091: items con status legacy pre-US-179 (ej. riesgos creados desde
// minutas IA con 'identified') rompían el form de edición: el Select
// mostraba "Abierto" pero el state re-enviaba el legacy y el backend lo
// rechazaba con 422. Normalizar SIEMPRE al inicializar forms/vistas.
const LEGACY_RAID_STATUS: Record<string, RaidStatus> = {
  identified: "open",
  analyzing: "in_progress",
  mitigating: "in_progress",
  materialized: "resolved",
  closed: "resolved",
};

export function normalizeRaidStatus(status: string | null | undefined): RaidStatus {
  if (!status) return "open";
  if (status in RAID_STATUS_LABEL) return status as RaidStatus;
  return LEGACY_RAID_STATUS[status] ?? "open";
}

export const RAID_STATUS_ORDER: RaidStatus[] = [
  "open",
  "in_progress",
  "on_hold",
  "resolved",
];

// US-179: estado terminal unificado (oculto por default en listas).
export const RAID_FINAL_STATUSES: RaidStatus[] = ["resolved"];

// Tags de color (Tailwind con tokens del design system) para ver los
// estados visualmente.
export const RAID_STATUS_BADGE: Record<RaidStatus, string> = {
  open: "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]",
  in_progress: "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]",
  on_hold: "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]",
  resolved: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
};

/** US-179: detención (on_hold) embebida en Risk/Issue. */
export type OnHoldDependency = {
  on_hold_reason: string | null;
  on_hold_area_id: string | null;
  on_hold_area: AreaMini | null;
  on_hold_actor_id: string | null;
  on_hold_actor_name: string | null;
  on_hold_since: string | null;
};

/** Días detenido desde on_hold_since (>=0) o null si no aplica. */
export function onHoldDays(since: string | null | undefined): number | null {
  if (!since) return null;
  const start = new Date(`${since}T00:00:00`);
  if (Number.isNaN(start.getTime())) return null;
  const today = new Date();
  const ms = today.getTime() - start.getTime();
  return Math.max(0, Math.floor(ms / 86_400_000));
}

/* ========== RISKS ========== */
// US-179: alias retro-compat → estados unificados.
export type RiskStatus = RaidStatus;

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
  owner_actor_id?: string | null;
  owner: UserMini | null;
  // ENH-175: responsable resuelto (Actor con fallback a Usuario).
  responsible_name: string | null;
  area_id: string | null;
  area: AreaMini | null;
  identified_at: string | null;
  due_date: string | null;
  status: RiskStatus;
  closure_note: string | null;
  // US-179: detención.
  on_hold_reason: string | null;
  on_hold_area_id: string | null;
  on_hold_area: AreaMini | null;
  on_hold_actor_id: string | null;
  on_hold_actor_name: string | null;
  on_hold_since: string | null;
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
  owner_actor_id?: string | null;
  area_id: string; // US-064: obligatorio en creación.
  identified_at?: string | null;
  due_date?: string | null;
  status?: RiskStatus;
  // US-179: detención.
  on_hold_reason?: string | null;
  on_hold_area_id?: string | null;
  on_hold_actor_id?: string | null;
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

// US-179: alias retro-compat → labels unificados.
export const RISK_STATUS_LABEL = RAID_STATUS_LABEL;

/* ========== ISSUES (AID) ========== */
export type IssueType = "action" | "issue" | "decision";
// US-179: estados unificados (mismo set que riesgos).
export type IssueStatus = RaidStatus;

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
  category: string | null; // ENH-177
  priority: number | null;
  committed_date: string | null;
  resolution: string | null;
  status: IssueStatus;
  owner_id: string | null;
  owner_actor_id?: string | null;
  owner: UserMini | null;
  // ENH-175: responsable resuelto (Actor con fallback a Usuario).
  responsible_name: string | null;
  area_id: string | null;
  area: AreaMini | null;
  reported_at: string | null;
  // US-179: detención.
  on_hold_reason: string | null;
  on_hold_area_id: string | null;
  on_hold_area: AreaMini | null;
  on_hold_actor_id: string | null;
  on_hold_actor_name: string | null;
  on_hold_since: string | null;
  comments: IssueComment[];
};

export type IssueCreateBody = {
  title: string;
  description?: string | null;
  type: IssueType;
  category?: string | null; // ENH-177
  priority?: number | null;
  committed_date?: string | null;
  // BUG-084: fecha de creación elegida en el form (si se omite, el server usa hoy).
  reported_at?: string | null;
  owner_id?: string | null;
  owner_actor_id?: string | null;
  area_id: string; // US-064: obligatorio en creación.
  status?: IssueStatus;
  // US-179: detención.
  on_hold_reason?: string | null;
  on_hold_area_id?: string | null;
  on_hold_actor_id?: string | null;
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

// ENH-112: soft-delete de un incidente/acción/decisión (RAID).
export function deleteIssue(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/issues/${id}`, { method: "DELETE" });
}

// DEC-007: el tipo 'issue' en backend representa "Incidente" en UI (I de RAID).
export const ISSUE_TYPE_LABEL: Record<IssueType, string> = {
  action: "Acción",
  issue: "Incidente",
  decision: "Decisión",
};

// US-179: alias retro-compat → labels/orden/finales unificados.
export const ISSUE_STATUS_LABEL = RAID_STATUS_LABEL;
export const RISK_STATUS_ORDER = RAID_STATUS_ORDER;
export const ISSUE_STATUS_ORDER = RAID_STATUS_ORDER;
export const RISK_FINAL_STATUSES = RAID_FINAL_STATUSES;
export const ISSUE_FINAL_STATUSES = RAID_FINAL_STATUSES;

/* ========== CHANGE REQUESTS ========== */
export type ChangeType = "scope" | "time" | "cost" | "resource";
// ENH-112: `cancelled` para el flujo de cancelación de cambios.
export type ChangeStatus =
  | "in_review"
  | "approved"
  | "rejected"
  | "implemented"
  | "cancelled";

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
  // ENH-186: edición inline de tipo (mismo patrón US-178 de RAID).
  type?: ChangeType;
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

// ENH-112: cancela un cambio (status='cancelled'); queda visible para
// trazabilidad de aprobaciones.
export function cancelChange(id: string): Promise<ChangeRequest> {
  return apiFetch<ChangeRequest>(`/api/v1/change-requests/${id}/cancel`, {
    method: "POST",
    body: {},
  });
}

// ENH-112: soft-delete de un cambio (lo retira de la lista).
export function deleteChange(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/change-requests/${id}`, { method: "DELETE" });
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
  cancelled: "Cancelado",
};

// ENH-186: chips de color por estado, mismo patrón que RAID_STATUS_BADGE.
export const CHANGE_STATUS_BADGE: Record<ChangeStatus, string> = {
  in_review: "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]",
  approved: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
  rejected: "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]",
  implemented: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
  cancelled: "bg-[var(--color-subtle)] text-[var(--color-tertiary)]",
};

// ENH-186: estados terminales — ocultos por default en la lista (toggle
// "Mostrar finalizados" los revela). `implemented` queda visible por
// default: sigue siendo relevante de seguimiento post-aprobación.
export const CHANGE_FINAL_STATUSES: ChangeStatus[] = ["approved", "rejected", "cancelled"];

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
    const res = await fetch(`${apiBase()}${info.url}`, {
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
  // ENH-187: dueño como Actor del catálogo (consistente con RAID). El
  // backend ya lo devuelve en LessonRead; faltaba en el tipo del cliente.
  owner_actor_id?: string | null;
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
  // ENH-187: edición inline de responsable (mismo patrón US-178 de RAID).
  owner_actor_id?: string | null;
};

export function updateLesson(lessonId: string, body: LessonUpdateBody): Promise<Lesson> {
  return apiFetch<Lesson>(`/api/v1/lessons/${lessonId}`, { method: "PATCH", body });
}

// ENH-112: soft-delete de una lección aprendida.
export function deleteLesson(lessonId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/lessons/${lessonId}`, { method: "DELETE" });
}

export const LESSON_CATEGORY_LABEL: Record<LessonCategory, string> = {
  success: "Éxito",
  improvement: "Mejora",
  error: "Error",
};

// ENH-187: chips de color por categoría, mismo patrón que CHANGE_STATUS_BADGE.
export const LESSON_CATEGORY_BADGE: Record<LessonCategory, string> = {
  success: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
  improvement: "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]",
  error: "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]",
};

// ENH-187: fase es texto libre en DB (el modal de creación sólo ofrece
// estos 4 valores canónicos); labels ES para filtros/chips/export.
export type LessonPhase = "planning" | "execution" | "hypercare" | "closed";

export const LESSON_PHASE_LABEL: Record<LessonPhase, string> = {
  planning: "Planificación",
  execution: "Ejecución",
  hypercare: "Hypercare",
  closed: "Cierre",
};

export const LESSON_PHASE_ORDER: LessonPhase[] = [
  "planning",
  "execution",
  "hypercare",
  "closed",
];

export const LESSON_PHASE_BADGE: Record<LessonPhase, string> = {
  planning: "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]",
  execution: "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]",
  hypercare: "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]",
  closed: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
};

/* ========== MEETING MINUTES ========== */
export type MinuteAgreement = {
  description: string;
  owner_id?: string | null;
  /** Texto libre del responsable cuando viene del LLM (no FK). */
  owner?: string | null;
  due_date?: string | null;
  status?: string | null;
};

export type MinuteParticipant = {
  user_id?: string;
  name: string;
  email?: string;
  /** Rol declarado por el LLM o capturado manualmente. */
  role?: string | null;
  /** BUG-063: área funcional del participante (PMO, Comercial, etc.). */
  area?: string | null;
  /** BUG-063: estado de asistencia. */
  attendance?: "attended" | "absent_justified" | "absent_unjustified";
};

export type MinuteTopic = {
  title: string;
  /** Bullets factuales del gold standard (5-15 por tema). */
  bullets?: string[];
  /** Legacy: minutas viejas usaban `notes` como prosa libre. */
  notes?: string;
};

/** BUG-063: estado de una sugerencia RAID persistida en una minuta. */
export type MinuteRaidSuggestion = {
  short_desc: string;
  suggested_owner_name?: string | null;
  suggested_priority?: number | null;
  suggested_due_date?: string | null;
  raw_quote?: string | null;
  status: "pending" | "approved" | "discarded";
  ticket_id?: string | null;
  ticket_type?:
    | "action"
    | "risk"
    | "decision"
    | "issue"
    | "lesson"
    | "change_request"
    | null;
};

/** BUG-063: 4 buckets canónicos A/R/D/I. Lecciones/cambios legacy se
 *  mantienen como opcionales para retro-compat con minutas viejas. */
export type MinuteRaidSuggestions = {
  actions: MinuteRaidSuggestion[];
  risks: MinuteRaidSuggestion[];
  decisions: MinuteRaidSuggestion[];
  issues: MinuteRaidSuggestion[];
  lessons?: MinuteRaidSuggestion[];
  changes?: MinuteRaidSuggestion[];
  /** Meta-bucket reservado: free_notes y otros campos opcionales. */
  _meta?: { free_notes?: string };
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
  /** BUG-063: resumen del LLM (2-3 oraciones). */
  description?: string | null;
  next_meeting_date: string | null;
  attachments: { name?: string; url: string }[];
  generated_by_ai: boolean;
  status: string;
  /** US-108: sugerencias RAID detectadas por la IA + estado de revisión PM. */
  raid_suggestions?: Partial<MinuteRaidSuggestions>;
};

export type MinuteCreateBody = {
  title: string;
  meeting_date: string;
  summary?: string | null;
  free_notes?: string | null;
  participants?: MinuteParticipant[];
  topics?: MinuteTopic[];
  agreements?: MinuteAgreement[];
  next_meeting_date?: string | null;
  attachments?: { name?: string; url: string }[];
  generated_by_ai?: boolean;
  /** BUG-058 + BUG-063: persiste las sugerencias RAID al guardar el
   *  preview. Shape A/R/D/I canónico. */
  raid_suggestions?: Partial<MinuteRaidSuggestions>;
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

/** ENH-090: detalle de una minuta para el preview in-platform. */
export function getMinute(minuteId: string): Promise<MeetingMinute> {
  return apiFetch<MeetingMinute>(`/api/v1/meeting-minutes/${minuteId}`);
}

/** US-108 + ENH-090 + ENH-095: actualiza título, `raid_suggestions` y/o
 *  las secciones estructuradas (participants / topics / agreements)
 *  desde el editor inline del preview. */
export function updateMinute(
  minuteId: string,
  body: {
    title?: string;
    summary?: string | null;
    meeting_date?: string;
    free_notes?: string | null;
    raid_suggestions?: Partial<MinuteRaidSuggestions>;
    participants?: MinuteParticipant[];
    topics?: MinuteTopic[];
    agreements?: MinuteAgreement[];
  },
): Promise<MeetingMinute> {
  return apiFetch<MeetingMinute>(`/api/v1/meeting-minutes/${minuteId}`, {
    method: "PATCH",
    body,
  });
}

/** ENH-091: borra físicamente una minuta. */
export function deleteMinute(minuteId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/meeting-minutes/${minuteId}`, {
    method: "DELETE",
  });
}

/** US-108 + BUG-063: aprueba sugerencias RAID en bulk y crea los tickets
 *  reales. Shape canónico A/R/D/I; lessons/changes mantenidos por
 *  retro-compat con minutas pre-refactor. */
export type RaidApproveItem = {
  type:
    | "actions"
    | "risks"
    | "decisions"
    | "issues"
    | "lessons"
    | "changes";
  index: number;
  short_desc?: string;
  description?: string | null;
  priority?: number | null;
};

export function approveMinuteRaidSuggestions(
  minuteId: string,
  items: RaidApproveItem[],
): Promise<MeetingMinute> {
  return apiFetch<MeetingMinute>(
    `/api/v1/meeting-minutes/${minuteId}/approve-raid-suggestions`,
    { method: "POST", body: { items } },
  );
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
  const headers: Record<string, string> = {};
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
