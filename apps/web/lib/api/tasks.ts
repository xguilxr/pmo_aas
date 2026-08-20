import { apiFetch, ApiError } from "@/lib/api";

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
  wbs_code: string | null;
  parent_id: string | null;
  name: string;
  start_date: string | null;
  end_date: string | null;
  // US-171 + US-177: fecha de cierre real (YYYY-MM-DD). Completada con
  // closed_at > end_date → "Completada con atraso" (amarillo); no completada
  // con end_date < hoy → "Atrasada" (rojo).
  closed_at: string | null;
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
  // ENH-097: boolean explicito de criticidad (paralelo al enum). Sprint 26.
  is_critical?: boolean;
  // ENH-050: hito relacionado (FK self a otra task con is_milestone=true).
  related_milestone_id: string | null;
  related_milestone: { id: string; name: string; wbs_code: string | null } | null;
  // US-090: outline + predecessors / successors.
  outline_level: number | null;
  predecessors: string[] | null;
  successors: string[] | null;
  // US-098: área responsable (FK al catálogo tenant `areas`).
  area_id: string | null;
};

export type TaskCreateBody = {
  name: string;
  description?: string | null;
  wbs_code?: string | null;
  parent_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  // US-171: fecha de cierre real.
  closed_at?: string | null;
  duration_days?: number | null;
  progress?: number;
  is_milestone?: boolean;
  owner_id?: string | null;
  // ENH-079 / ENH-135: responsable como Actor del catálogo.
  assignee_actor_id?: string | null;
  priority?: number | null;
  status?: TaskStatus;
  criticality?: TaskCriticality;
  // ENH-097: boolean explicito.
  is_critical?: boolean;
  // ENH-050.
  related_milestone_id?: string | null;
  // US-090.
  predecessors?: string[] | null;
  // US-098.
  area_id?: string | null;
};

export type TaskUpdateBody = Partial<TaskCreateBody> & {
  status?: TaskStatus;
  progress?: number;
  criticality?: TaskCriticality;
  is_critical?: boolean;
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
    wbs_code: string | null;
    start: string | null;
    end: string | null;
    progress: number;
    is_milestone: boolean;
    status: string;
    external_id: string | null;
  }[];
  dependencies: GanttDependency[];
};

// --- US-218: dependencias entre tareas de proyectos distintos --------------

/** El extremo de una dependencia externa: la tarea y de qué proyecto es. */
export type ExtremoExterno = {
  task_id: string;
  task_name?: string;
  wbs_code?: string;
  end_date?: string | null;
  status?: string;
  project_id?: string;
  project_folio?: string;
  project_name?: string;
};

export type DependenciaExterna = {
  id: string;
  /** El vínculo de MS Project: FS, SS, FF o SF. */
  type: string;
  lag_days: number;
  predecessor: ExtremoExterno;
  successor: ExtremoExterno;
};

/**
 * Las dependencias externas de un proyecto, en las dos direcciones.
 *
 * Separadas porque significan cosas distintas para quien mira el plan: una
 * **entrante** es algo que este proyecto espera —y que puede retrasarlo—, y una
 * **saliente** es alguien esperándonos. Una lista sola obligaría a leer el
 * sentido en cada fila.
 */
export type DependenciasExternas = {
  entrantes: DependenciaExterna[];
  salientes: DependenciaExterna[];
};

export function listExternalDependencies(
  projectId: string,
): Promise<DependenciasExternas> {
  return apiFetch<DependenciasExternas>(
    `/api/v1/projects/${projectId}/external-dependencies`,
  );
}

export function createExternalDependency(
  projectId: string,
  body: {
    predecessor_task_id: string;
    successor_task_id: string;
    type?: string;
    lag_days?: number;
  },
): Promise<{ id: string }> {
  return apiFetch(`/api/v1/projects/${projectId}/external-dependencies`, {
    method: "POST",
    body,
  });
}

export function deleteExternalDependency(
  projectId: string,
  dependencyId: string,
): Promise<void> {
  return apiFetch(
    `/api/v1/projects/${projectId}/external-dependencies/${dependencyId}`,
    { method: "DELETE" },
  );
}

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

// US-172: renumera el WBS de todo el proyecto (jerárquico + único).
export function renumberWbs(projectId: string): Promise<{ renumbered: number }> {
  return apiFetch<{ renumbered: number }>(
    `/api/v1/projects/${projectId}/tasks/renumber-wbs`,
    { method: "POST" },
  );
}

// US-176: reordena una tarea para que quede justo después de `afterId`
// (null = al inicio). El backend normaliza `position` de todo el proyecto.
export function moveTask(
  projectId: string,
  taskId: string,
  afterId: string | null,
): Promise<{ reordered: number }> {
  return apiFetch<{ reordered: number }>(
    `/api/v1/projects/${projectId}/tasks/${taskId}/move`,
    { method: "POST", body: { after_id: afterId } },
  );
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
  const form = new FormData();
  form.append("file", file);
  const url = `${base}/api/v1/projects/${projectId}/tasks/import?strategy=${strategy}`;
  const res = await fetch(url, {
    method: "POST",
    body: form,
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

// ENH-192: lista COMPLETA de campos mapeables — espeja
// `import_mapping_suggest.SYSTEM_FIELDS` del backend (antes el wizard
// solo ofrecía 9 y área/criticidad/hito relacionado no se podían
// re-mapear a mano).
export const SYSTEM_FIELDS = [
  "name",
  "wbs_code",
  "start_date",
  "end_date",
  "duration_days",
  "progress",
  "is_milestone",
  // ENH-191: estado importable.
  "status",
  "criticality",
  "is_critical",
  "related_milestone",
  "predecessors",
  "area",
  "resources",
] as const;

export type SystemField = (typeof SYSTEM_FIELDS)[number];

export type ImportSource = "xlsx" | "csv" | "mpp" | "xml";

// BUG-088: aviso no bloqueante del parser (WBS numérico, huérfanos, …).
export type ImportWarning = {
  code: string;
  message: string;
  count?: number;
  rows?: (number | string)[];
};

export type ImportPreviewResult = {
  job_id: string;
  source: ImportSource;
  sheets: string[]; // [] para CSV/MPP/XML
  sheet_used: string | null;
  columns_detected: Partial<Record<SystemField, number>>;
  sample_rows: (string | null)[][]; // header + hasta 10 data rows
  task_count: number;
  errors: { row?: number; error?: string }[];
  warnings?: ImportWarning[];
  // ENH-192: tareas interpretadas (primeras 10) para la vista previa.
  parsed_preview?: ParsedPreviewTask[];
  ttl_seconds: number;
  system_fields: SystemField[];
};

export type ImportConfirmResult = {
  imported: number;
  dependencies_created: number;
  errors: unknown[];
  warnings?: ImportWarning[];
  // US-188 nivel 2: valores normalizados por IA en el confirm.
  ai_normalized?: { statuses: number; resources: number };
  strategy: string;
  source: string;
};

// ENH-192: tarea YA interpretada por el parser (WBS fiel, % escalado,
// estado normalizado) — la vista previa "como quedará el plan".
export type ParsedPreviewTask = {
  row_number: number;
  wbs_code: string | null;
  name: string;
  start_date: string | null;
  end_date: string | null;
  duration_days: number | null;
  progress: number;
  status: string | null;
  is_milestone: boolean;
  is_critical: boolean | null;
  area: string | null;
  resources: string | null;
  related_milestone: string | null;
  predecessors: string | null;
};

export type ImportRepreviewResult = {
  task_count: number;
  columns_detected: Partial<Record<SystemField, number>>;
  errors: { row?: number; error?: string }[];
  warnings: ImportWarning[];
  parsed_preview: ParsedPreviewTask[];
};

async function rawFetch(
  url: string,
  init: RequestInit,
): Promise<Response> {
  const headers = new Headers(init.headers);
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

// ENH-053 — sugerencia de mapeo asistida por IA (heurística + LLM).
export type SuggestMappingItem = {
  field: SystemField | null;
  confidence: number;
  source: "ai" | "heuristic" | "none";
};

export type SuggestMappingResponse = {
  suggestions: Record<string, SuggestMappingItem>;
  system_fields: SystemField[];
  ai_used: boolean;
};

export function suggestImportMapping(
  projectId: string,
  headers: string[],
  sampleRows?: (string | null)[][],
): Promise<SuggestMappingResponse> {
  return apiFetch<SuggestMappingResponse>(
    `/api/v1/projects/${projectId}/tasks/import/suggest-mapping`,
    {
      method: "POST",
      // US-188 nivel 1: filas de muestra → la IA mapea por contenido.
      body: { headers, sample_rows: sampleRows?.slice(0, 5) ?? null },
    },
  );
}

export async function importConfirm(
  projectId: string,
  jobId: string,
  body: {
    mapping?: Partial<Record<SystemField, number>> | null;
    strategy: "merge" | "replace";
    // US-188 nivel 3: persistir la propuesta IA revisada en el preview.
    use_ai_structure?: boolean;
  },
): Promise<ImportConfirmResult> {
  return apiFetch<ImportConfirmResult>(
    `/api/v1/projects/${projectId}/tasks/import/${jobId}/confirm`,
    { method: "POST", body },
  );
}

// ENH-192: re-interpreta el archivo con un mapping manual sin persistir
// — refresca la vista interpretada + warnings al re-mapear columnas.
export function importRepreview(
  projectId: string,
  jobId: string,
  mapping: Partial<Record<SystemField, number>> | null,
): Promise<ImportRepreviewResult> {
  return apiFetch<ImportRepreviewResult>(
    `/api/v1/projects/${projectId}/tasks/import/${jobId}/repreview`,
    { method: "POST", body: { mapping } },
  );
}

// US-190 — revisión de calidad del plan (linter).
export type PlanQualityObservation = {
  code: string;
  severity: "error" | "warning" | "info";
  message: string;
  items: string[];
  count: number;
};

export type PlanQualityResult = {
  observations: PlanQualityObservation[];
  score: number;
  task_count: number;
};

export function getPlanQuality(projectId: string): Promise<PlanQualityResult> {
  return apiFetch<PlanQualityResult>(
    `/api/v1/projects/${projectId}/plan/quality`,
  );
}

// US-188 nivel 3: la IA propone el plan completo desde el archivo crudo.
export type ImportAiStructureResult = {
  task_count: number;
  warnings: ImportWarning[];
  parsed_preview: ParsedPreviewTask[];
};

export function importAiStructure(
  projectId: string,
  jobId: string,
): Promise<ImportAiStructureResult> {
  return apiFetch<ImportAiStructureResult>(
    `/api/v1/projects/${projectId}/tasks/import/${jobId}/ai-structure`,
    { method: "POST", body: {} },
  );
}

export const SYSTEM_FIELD_LABELS: Record<SystemField, string> = {
  name: "Nombre (obligatorio)",
  wbs_code: "WBS / EDT",
  start_date: "Fecha inicio",
  end_date: "Fecha fin",
  duration_days: "Duración (días)",
  progress: "% Avance",
  is_milestone: "Es hito",
  status: "Estado",
  criticality: "Criticidad (baja/media/alta)",
  is_critical: "Criticidad (Sí/No)",
  related_milestone: "Hito relacionado (WBS)",
  predecessors: "Predecesoras",
  area: "Área responsable",
  resources: "Responsable / Recursos",
};

export const TASK_STATUS_LABEL: Record<string, string> = {
  not_started: "No iniciada",
  in_progress: "En progreso",
  completed: "Completada",
  on_hold: "En pausa",
};
