// US-183 — cliente de los endpoints de capacidad/saturación de recursos.
import { apiFetch } from "@/lib/api";

export type CapacityWindow = "today" | "week" | "3weeks" | "month";
export type CapacityColor = "green" | "yellow" | "red";

export type CapacityParams = {
  window?: CapacityWindow;
  organization_id?: string;
};

export type CapacityThresholds = {
  yellow_over: number;
  red_over: number;
};

export type CapacityResource = {
  actor_id: string;
  name: string;
  discipline: string | null;
  resource_type: string | null;
  seniority: string | null;
  scarcity_level: string | null;
  area_id: string | null;
  team_id: string | null;
  organization_id: string | null;
  is_key_resource: boolean;
  is_shared_resource: boolean;
  capacity_pct: number;
  demand_pct: number;
  tentative_pct: number;
  gap_pct: number;
  over_pct: number;
  projects_count: number;
  unquantified_count: number;
  color: CapacityColor;
  // ENH-198: filtro por área/sub-área + % de uso (teórica vs FTE).
  area_name?: string | null;
  team_name?: string | null;
  usage_pct?: number | null;
};

export type CapacityDisciplineAgg = {
  discipline: string;
  capacity_pct: number;
  demand_pct: number;
  gap_pct: number;
  resources: number;
  overloaded: number;
  color: CapacityColor;
};

export type CapacityAreaAgg = {
  area_id: string;
  name: string;
  capacity_pct: number;
  demand_pct: number;
  gap_pct: number;
  resources: number;
  overloaded: number;
  color: CapacityColor;
};

export type CapacityTeamAgg = {
  team_id: string;
  name: string;
  capacity_pct: number;
  demand_pct: number;
  gap_pct: number;
  resources: number;
  overloaded: number;
  color: CapacityColor;
};

export type CapacitySummaryResponse = {
  window: string;
  start: string;
  end: string;
  thresholds?: CapacityThresholds;
  resources: CapacityResource[];
  by_discipline: CapacityDisciplineAgg[];
  by_area: CapacityAreaAgg[];
  by_team: CapacityTeamAgg[];
};

export type CapacityConflictProject = {
  project_id: string;
  name: string;
  folio: string;
  health: string | null;
  allocation_pct: number | null;
  is_critical: boolean;
  start_date: string | null;
  end_date: string | null;
};

export type CapacityConflict = CapacityResource & {
  projects: CapacityConflictProject[];
  recommendation: string;
};

export type CapacityConflictsResponse = {
  window: string;
  start?: string;
  end?: string;
  conflicts: CapacityConflict[];
};

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function getCapacitySummary(
  params: CapacityParams = {},
): Promise<CapacitySummaryResponse> {
  return apiFetch<CapacitySummaryResponse>(`/api/v1/capacity/summary${qs(params)}`);
}

// --- US-208: carga semanal (heatmap persona × semana) ----------------------

export type SemanaDeCarga = {
  /** El número de semana ISO, como lo dibuja el mockup: `s33`. */
  label: string;
  start: string;
  end: string;
};

export type AsignacionDeCarga = {
  project_id: string;
  project_name: string;
  project_folio: string;
  /** `null` cuando la participación no tiene FTE capturado. */
  allocation_pct: number | null;
  start_date: string | null;
  end_date: string | null;
  is_critical: boolean;
};

export type FilaDeCarga = {
  /**
   * `actor` es una persona; `team`, la fila que agrega a sus miembros. La fila
   * de equipo es el **promedio** de los suyos, no la suma: sumar seis daría
   * 720 %, que no significa nada. `members` dice cuántos.
   */
  kind: "actor" | "team";
  id: string;
  name: string;
  discipline: string | null;
  area: string;
  team_id: string | null;
  team: string;
  members?: number;
  capacity_pct: number;
  /** Un valor por semana, en el mismo orden que `weeks`. */
  per_week: number[];
  peak_pct: number;
  projects_count: number;
  is_key_resource: boolean;
  is_shared_resource: boolean;
  /** Vacío en las filas de equipo. Es el desglose de la celda al hacer clic. */
  assignments: AsignacionDeCarga[];
};

export type CapacidadVsDemanda = {
  label: string;
  /** En FTE y no en porcentaje: «38.6 de 35 personas» se entiende sin convertir. */
  demand_fte: number;
  capacity_fte: number;
};

export type CriticoCompartido = {
  actor_id: string;
  name: string;
  discipline: string | null;
  projects_count: number;
  projects: string[];
  peak_pct: number;
};

export type CargaSemanalResponse = {
  weeks: SemanaDeCarga[];
  rows: FilaDeCarga[];
  capacity_vs_demand: CapacidadVsDemanda[];
  shared_critical: CriticoCompartido[];
  /** Derivadas del propio corte: nombran recurso y semanas concretas. */
  suggested: string[];
  /**
   * Recursos con participaciones activas y **sin** `%` capturado. No entran en
   * el heatmap: una fila en cero para quien sí está asignado se lee como
   * «libre», cuando lo que pasa es que no se sabe cuánto pesa. Se cuentan
   * porque es accionable — hay que capturar el FTE.
   */
  unquantified_resources: number;
};

export function getCargaSemanal(
  params: { weeks?: number; organization_id?: string } = {},
): Promise<CargaSemanalResponse> {
  return apiFetch<CargaSemanalResponse>(`/api/v1/capacity/weekly-load${qs(params)}`);
}

export function getCapacityConflicts(
  params: CapacityParams = {},
): Promise<CapacityConflictsResponse> {
  return apiFetch<CapacityConflictsResponse>(`/api/v1/capacity/conflicts${qs(params)}`);
}
