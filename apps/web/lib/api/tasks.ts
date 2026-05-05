import { apiFetch, ApiError } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";

export type TaskStatus = "not_started" | "in_progress" | "completed" | "on_hold";

// ENH-051: criticidad de tarea (separada de priority general).
export type TaskCriticality = "low" | "medium" | "high" | "critical";

export type TaskOwnerMini = {
  id: string;
  full_name: string | null;
  email: string;
};

export type Task = {
  id: string;
  project_id: string;
  wbs: string | null;
  parent_id: string | null;
  name: string;
  start_date: string | null;
  end_date: string | null;
  duration_days: number | null;
  progress: number;
  is_milestone: boolean;
  status: TaskStatus | string;
  source: string;
  external_id: string | null;
  // ENH-049: responsable embebido para mostrar en la columna sin
  // round-trip extra a /users.
  owner_id: string | null;
  owner: TaskOwnerMini | null;
  // ENH-051: criticidad. Default "medium" si la columna está fresca.
  criticality: TaskCriticality;
  // ENH-050: hito relacionado (FK self a otra task con is_milestone=true).
  related_milestone_id: string | null;
  related_milestone: { id: string; name: string; wbs: string | null } | null;
  // US-090: outline + predecessors / successors.
  outline_level: number | null;
  predecessors: string[] | null;
  successors: string[] | null;
};

export type TaskCreateBody = {
  name: string;
  description?: string | null;
  wbs?: string | null;
  parent_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  duration_days?: number | null;
  progress?: number;
  is_milestone?: boolean;
  owner_id?: string | null;
  priority?: number | null;
  status?: TaskStatus;
  criticality?: TaskCriticality;
  // ENH-050.
  related_milestone_id?: string | null;
  // US-090.
  predecessors?: string[] | null;
};

export type TaskUpdateBody = Partial<TaskCreateBody> & {
  status?: TaskStatus;
  progress?: number;
  criticality?: TaskCriticality;
  related_milestone_id?: string | null;
  predecessors?: string[] | null;
};

export const TASK_CRITICALITY_LABEL: Record<TaskCriticality, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  critical: "Crítica",
};

export type GanttDependency = {
  predecessor_id: string;
  successor_id: string;
  type: "FS" | "SS" | "FF" | "SF" | string;
  lag_days: number | null;
};

export type GanttData = {
  tasks: {
    id: string;
    name: string;
    wbs: string | null;
    start: string | null;
    end: string | null;
    progress: number;
    is_milestone: boolean;
    status: string;
    external_id: string | null;
  }[];
  dependencies: GanttDependency[];
};

export function listTasks(projectId: string): Promise<Task[]> {
  return apiFetch<Task[]>(`/api/v1/projects/${projectId}/tasks`);
}

export function createTask(projectId: string, body: TaskCreateBody): Promise<Task> {
  return apiFetch<Task>(`/api/v1/projects/${projectId}/tasks`, { method: "POST", body });
}

export function updateTask(taskId: string, body: TaskUpdateBody): Promise<Task> {
  return apiFetch<Task>(`/api/v1/tasks/${taskId}`, { method: "PATCH", body });
}

export function deleteTask(taskId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/tasks/${taskId}`, { method: "DELETE" });
}

export function getGantt(projectId: string): Promise<GanttData> {
  return apiFetch<GanttData>(`/api/v1/projects/${projectId}/gantt`);
}

export async function importMsProject(
  projectId: string,
  file: File,
  strategy: "merge" | "replace" = "replace",
): Promise<{
  imported: number;
  dependencies_created: number;
  errors: string[];
  strategy: string;
}> {
  const base = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
  const token = getAccessToken();
  const form = new FormData();
  form.append("file", file);
  const url = `${base}/api/v1/projects/${projectId}/tasks/import?strategy=${strategy}`;
  const res = await fetch(url, {
    method: "POST",
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: "include",
  });
  const text = await res.text();
  const data = text ? safeParse(text) : null;
  if (!res.ok) {
    const detail =
      (data as { detail?: { detail?: string; code?: string } } | null)?.detail?.detail ??
      (data as { detail?: string } | null)?.detail ??
      `Error ${res.status}`;
    const code =
      (data as { detail?: { code?: string } } | null)?.detail?.code ?? "UNKNOWN";
    throw new ApiError(res.status, String(code), String(detail));
  }
  return data as {
    imported: number;
    dependencies_created: number;
    errors: string[];
    strategy: string;
  };
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// US-070 — Wizard de mapeo de columnas (preview + confirm).

export const SYSTEM_FIELDS = [
  "name",
  "wbs",
  "start_date",
  "end_date",
  "duration_days",
  "progress",
  "is_milestone",
  "predecessors",
  "resources",
] as const;

export type SystemField = (typeof SYSTEM_FIELDS)[number];

export type ImportSource = "xlsx" | "csv" | "mpp" | "xml";

export type ImportPreviewResult = {
  job_id: string;
  source: ImportSource;
  sheets: string[]; // [] para CSV/MPP/XML
  sheet_used: string | null;
  columns_detected: Partial<Record<SystemField, number>>;
  sample_rows: (string | null)[][]; // header + hasta 10 data rows
  task_count: number;
  errors: { row?: number; error?: string }[];
  ttl_seconds: number;
  system_fields: SystemField[];
};

export type ImportConfirmResult = {
  imported: number;
  dependencies_created: number;
  errors: unknown[];
  strategy: string;
  source: string;
};

async function rawFetch(
  url: string,
  init: RequestInit,
): Promise<Response> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...init, headers, credentials: "include" });
}

async function _decode<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? safeParse(text) : null;
  if (!res.ok) {
    const detail =
      (data as { detail?: { detail?: string; code?: string } } | null)?.detail
        ?.detail ??
      (data as { detail?: string } | null)?.detail ??
      `Error ${res.status}`;
    const code =
      (data as { detail?: { code?: string } } | null)?.detail?.code ??
      "UNKNOWN";
    throw new ApiError(res.status, String(code), String(detail));
  }
  return data as T;
}

export async function importPreview(
  projectId: string,
  file: File,
  sheet?: string | null,
): Promise<ImportPreviewResult> {
  const base = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
  const form = new FormData();
  form.append("file", file);
  const qs = sheet ? `?sheet=${encodeURIComponent(sheet)}` : "";
  const url = `${base}/api/v1/projects/${projectId}/tasks/import/preview${qs}`;
  const res = await rawFetch(url, { method: "POST", body: form });
  return _decode<ImportPreviewResult>(res);
}

export async function importConfirm(
  projectId: string,
  jobId: string,
  body: {
    mapping?: Partial<Record<SystemField, number>> | null;
    strategy: "merge" | "replace";
  },
): Promise<ImportConfirmResult> {
  return apiFetch<ImportConfirmResult>(
    `/api/v1/projects/${projectId}/tasks/import/${jobId}/confirm`,
    { method: "POST", body },
  );
}

export const SYSTEM_FIELD_LABELS: Record<SystemField, string> = {
  name: "Nombre (obligatorio)",
  wbs: "WBS / EDT",
  start_date: "Fecha inicio",
  end_date: "Fecha fin",
  duration_days: "Duración (días)",
  progress: "% Avance",
  is_milestone: "Es hito",
  predecessors: "Predecesoras",
  resources: "Recursos",
};

export const TASK_STATUS_LABEL: Record<string, string> = {
  not_started: "No iniciada",
  in_progress: "En progreso",
  completed: "Completada",
  on_hold: "En pausa",
};
