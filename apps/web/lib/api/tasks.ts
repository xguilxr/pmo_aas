import { apiFetch, ApiError } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";

export type TaskStatus = "not_started" | "in_progress" | "completed" | "on_hold";

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
};

export type TaskUpdateBody = Partial<TaskCreateBody> & {
  status?: TaskStatus;
  progress?: number;
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

export const TASK_STATUS_LABEL: Record<string, string> = {
  not_started: "No iniciada",
  in_progress: "En progreso",
  completed: "Completada",
  on_hold: "En pausa",
};
