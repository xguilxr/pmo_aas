import { apiFetch } from "@/lib/api";

// US-202 / ADR-038 (2026-08-19): el vocabulario pasa al español, que es el del
// glosario, el de la interfaz y el de quien la usa. El API acepta los nombres
// viejos a la entrada durante una ventana de compatibilidad, pero siempre
// devuelve el canónico, así que aquí solo existe el nuevo.
// `hypercare` se queda: no tiene traducción que no sea peor, y ADR-019 ya lo
// renombró una vez desde `support`.
// ADR-022: `cancelado` es un final distinto de `cerrado`. Un proyecto cortado a
// mitad terminaba antes en «cerrado», indistinguible de uno que cumplió.
export type ProjectPhase =
  | "preparacion"
  | "ejecucion"
  | "hypercare"
  | "cerrado"
  | "cancelado";
// US-202: el tipo deja de ser texto libre. Cuatro valores, y `bau` se queda en
// la sigla porque es como lo dice quien lo pide.
export type ProjectType = "transformacion" | "operacion" | "innovacion" | "bau";
export type ProjectHealth = "green" | "yellow" | "red";
// US-180: fuente del semáforo único — 'auto' (motor de reglas) o
// 'manual' (declarado por el PM con razón).
export type ProjectHealthSource = "auto" | "manual";
export type ProjectMemberRole = "pm" | "team" | "viewer" | "stakeholder";

export type Project = {
  id: string;
  folio: string;
  /**
   * BUG-092 — la moneda del presupuesto, **ya resuelta** por la API: nunca
   * llega vacía. El frontend no aplica la regla «nulo = la del inquilino»,
   * porque esa regla vive en el backend y dos sitios decidiéndola divergen.
   */
  currency: string;
  name: string;
  description: string | null;
  type: ProjectType | null;
  priority: number | null;
  phase: ProjectPhase;
  organization_id: string;
  program_id: string | null;
  /** US-199 — con programa, es el del programa (regla de consistencia). */
  portfolio_id: string | null;
  pm_id: string | null;
  sponsor: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: string | null;
  actual_budget: string | null;
  progress: number;
  health_status: ProjectHealth;
  // US-180: salud única híbrida.
  health_source: ProjectHealthSource;
  health_reason: string | null;
  request_id: string | null;
  // US-084: { field: { edited_at, edited_by } } por agregado del plan
  // que el PM marcó como editado a mano (importadores deben respetar).
  manually_edited_fields: Record<
    string,
    { edited_at: string; edited_by: string }
  >;
};

export type ProjectMember = {
  user_id: string;
  role_in_project: ProjectMemberRole;
  username: string;
  full_name: string;
};

export type ProjectDetail = Project & {
  members: ProjectMember[];
  module_counts: Record<string, number>;
  // ENH-129: KPIs de tareas para el gauge de Avance del Resumen.
  task_kpis: Record<string, number>;
};

export type ProjectCreateBody = {
  name: string;
  /** BUG-092 — `null` deja que aplique la preferida del inquilino. */
  currency?: string | null;
  description: string;
  type: ProjectType;
  priority: number;
  organization_id: string;
  program_id?: string | null;
  /** US-199 — se autocompleta con el del programa si se manda programa. */
  portfolio_id?: string | null;
  phase?: ProjectPhase;
  pm_id: string;
  sponsor?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  budget?: number | string | null;
};

export type ProjectUpdateBody = Partial<{
  /** BUG-092 — `null` devuelve el proyecto a la preferida del inquilino. */
  currency: string | null;
  name: string;
  description: string;
  type: ProjectType;
  priority: number;
  program_id: string | null;
  portfolio_id: string | null;
  pm_id: string;
  sponsor: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: number | string | null;
  actual_budget: number | string | null;
  progress: number;
  health_status: ProjectHealth;
}>;

// ---- US-180: salud única híbrida ----

export type HealthDimensionKey =
  | "schedule"
  | "budget"
  | "risks"
  | "decisions"
  | "resources";

export type HealthCause = {
  type: string;
  what: string;
  owner: string | null;
  due_date: string | null;
  days: number | null;
  severity?: number;
};

export type HealthDimension = {
  key: HealthDimensionKey;
  label: string;
  // null = N/A (sin datos para esta dimensión).
  color: ProjectHealth | null;
  summary: string;
  causes: HealthCause[];
  metrics: Record<string, number>;
};

export type HealthFocusItem = {
  dimension: HealthDimensionKey;
  dimension_label: string;
  color: ProjectHealth;
  what: string;
  type: string;
  owner: string | null;
  due_date: string | null;
  days: number | null;
  suggested_action: string;
};

export type HealthDetail = {
  health_status: ProjectHealth;
  health_source: ProjectHealthSource;
  health_reason: string | null;
  computed: ProjectHealth;
  dimensions: HealthDimension[];
  focus: HealthFocusItem[];
};

export function getHealthDetail(projectId: string): Promise<HealthDetail> {
  return apiFetch<HealthDetail>(`/api/v1/projects/${projectId}/health-detail`);
}

// status=null → volver a fuente automática (recalcula de inmediato).
export function declareHealth(
  projectId: string,
  body: { status: ProjectHealth | null; reason?: string | null },
): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${projectId}/health`, {
    method: "PATCH",
    body,
  });
}

// US-191 — evaluación periódica de salud (5 dimensiones + overall).
export type HealthEvaluation = {
  id: string;
  project_id: string;
  evaluated_at: string;
  schedule: ProjectHealth | null;
  budget: ProjectHealth | null;
  risks: ProjectHealth | null;
  decisions: ProjectHealth | null;
  resources: ProjectHealth | null;
  overall: ProjectHealth;
  note: string | null;
  created_by: string | null;
  created_at: string;
};

export type HealthEvaluationBody = {
  evaluated_at?: string | null;
  schedule?: ProjectHealth | null;
  budget?: ProjectHealth | null;
  risks?: ProjectHealth | null;
  decisions?: ProjectHealth | null;
  resources?: ProjectHealth | null;
  overall: ProjectHealth;
  note?: string | null;
};

export function createHealthEvaluation(
  projectId: string,
  body: HealthEvaluationBody,
): Promise<HealthEvaluation> {
  return apiFetch<HealthEvaluation>(
    `/api/v1/projects/${projectId}/health-evaluations`,
    { method: "POST", body },
  );
}

export function listHealthEvaluations(
  projectId: string,
  limit = 12,
): Promise<HealthEvaluation[]> {
  return apiFetch<HealthEvaluation[]>(
    `/api/v1/projects/${projectId}/health-evaluations?limit=${limit}`,
  );
}

export type ListProjectsParams = {
  phase?: ProjectPhase[] | ProjectPhase;
  organization_id?: string;
  program_id?: string;
  /** US-201 — filtro por portafolio (cascada Organización→Portafolio→Programa). */
  portfolio_id?: string;
  /** US-200 — los que todavía no están en ningún portafolio (importación
   *  masiva, sobre todo): sin esto serían invisibles hasta clasificarlos. */
  no_portfolio?: boolean;
  no_program?: boolean;
  type?: ProjectType[] | ProjectType;
  health?: ProjectHealth[] | ProjectHealth;
  priority_min?: number;
  priority_max?: number;
  q?: string;
  only_mine?: boolean;
  page?: number;
  limit?: number;
};

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

export function listProjects(params: ListProjectsParams = {}): Promise<Project[]> {
  return apiFetch<Project[]>(`/api/v1/projects${qs(params)}`);
}

export function getProject(id: string): Promise<ProjectDetail> {
  return apiFetch<ProjectDetail>(`/api/v1/projects/${id}`);
}

// US-149: feed de actividad del proyecto (audit log).
export type ActivityItem = {
  id: number;
  action: string;
  module: string | null;
  occurred_at: string;
  user_id: string | null;
  user_name: string | null;
  details: Record<string, unknown>;
};

export function getProjectActivity(id: string, limit = 20): Promise<ActivityItem[]> {
  return apiFetch<ActivityItem[]>(`/api/v1/projects/${id}/activity?limit=${limit}`);
}

export function createProject(body: ProjectCreateBody): Promise<Project> {
  return apiFetch<Project>("/api/v1/projects", { method: "POST", body });
}

export function updateProject(id: string, body: ProjectUpdateBody): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`, { method: "PATCH", body });
}

/**
 * US-084: quita el flag de "editado manualmente" del campo dado.
 * Field ∈ start_date | end_date | budget | progress.
 */
export function resetPlanAggregateOverride(
  id: string,
  field: "start_date" | "end_date" | "budget" | "progress",
): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}/plan-aggregates/reset`, {
    method: "POST",
    body: { field },
  });
}

export function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}

export function changePhase(
  id: string,
  body: { new_phase: ProjectPhase; comment?: string | null },
): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}/phase/change`, { method: "POST", body });
}

export function listMembers(id: string): Promise<ProjectMember[]> {
  return apiFetch<ProjectMember[]>(`/api/v1/projects/${id}/members`);
}

export function addMember(
  id: string,
  body: { user_id: string; role_in_project?: ProjectMemberRole },
): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}/members`, { method: "POST", body });
}

export function removeMember(id: string, userId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}/members/${userId}`, { method: "DELETE" });
}

export const PHASE_LABEL: Record<ProjectPhase, string> = {
  preparacion: "Preparación",
  ejecucion: "Ejecución",
  hypercare: "Hypercare",
  cerrado: "Cerrado",
  cancelado: "Cancelado",
};

// US-202: el orden del ciclo de vida, para desplegables y ejes de gráficos —
// alfabético pondría «cancelado» primero, que no es por donde empieza nada.
export const PHASE_ORDER: readonly ProjectPhase[] = [
  "preparacion",
  "ejecucion",
  "hypercare",
  "cerrado",
  "cancelado",
];

/**
 * El tono de la insignia de fase. Vive con el catálogo y no en las pantallas:
 * estaba escrito dos veces —en la lista de proyectos y en el detalle— con las
 * mismas cinco claves y los mismos cinco valores, y una fase nueva obligaba a
 * recordar las dos copias.
 *
 * ADR-022: `cancelado` **no** comparte el tono de `cerrado`. Distinguir a
 * simple vista un proyecto que cumplió de uno que se cortó es la razón de ser
 * de esa decisión, y aquí es donde se hace visible.
 */
export const PHASE_BADGE_TONE: Record<
  ProjectPhase,
  "info" | "success" | "warning" | "neutral" | "danger"
> = {
  preparacion: "info",
  ejecucion: "success",
  hypercare: "warning",
  cerrado: "neutral",
  cancelado: "danger",
};

export const TYPE_LABEL: Record<ProjectType, string> = {
  transformacion: "Transformación",
  operacion: "Operación",
  innovacion: "Innovación",
  bau: "BAU (operación continua)",
};

export const HEALTH_LABEL: Record<ProjectHealth, string> = {
  green: "Verde",
  yellow: "Amarillo",
  red: "Rojo",
};

/**
 * El semáforo en palabras. Existía cinco veces —tres bajo este mismo nombre,
 * una como `RAG_LABEL`— porque la salud llega de la API como `string` y no
 * como `ProjectHealth`: cada pantalla se hacía su propio `Record<string,
 * string>` para poder indexarlo. Esta función es ese accesor, una vez.
 */
export function etiquetaSalud(valor: string | null | undefined): string {
  if (!valor) return "—";
  return HEALTH_LABEL[valor as ProjectHealth] ?? valor;
}

export const MEMBER_ROLE_LABEL: Record<ProjectMemberRole, string> = {
  pm: "Project Manager",
  team: "Equipo",
  viewer: "Observador",
  stakeholder: "Stakeholder",
};

// US-185: memoria de proyecto para IA (contexto persistente inyectado en
// toda generación de minutas/reportes del proyecto).
export type ProjectAIContext = {
  project_id: string;
  context_md: string | null;
  instructions_md: string | null;
  auto_summary_md: string | null;
  auto_summary_updated_at: string | null;
  updated_at: string | null;
};

export type ProjectAIContextUpdateBody = Partial<{
  context_md: string | null;
  instructions_md: string | null;
  auto_summary_md: string | null;
}>;

export function getProjectAIContext(id: string): Promise<ProjectAIContext> {
  return apiFetch<ProjectAIContext>(`/api/v1/projects/${id}/ai-context`);
}

export function updateProjectAIContext(
  id: string,
  body: ProjectAIContextUpdateBody,
): Promise<ProjectAIContext> {
  return apiFetch<ProjectAIContext>(`/api/v1/projects/${id}/ai-context`, {
    method: "PUT",
    body,
  });
}
