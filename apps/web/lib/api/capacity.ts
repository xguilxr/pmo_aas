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
  portfolio_function: string | null;
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
};

export type CapacityFunctionAgg = {
  portfolio_function: string;
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
  by_function: CapacityFunctionAgg[];
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

export function getCapacityConflicts(
  params: CapacityParams = {},
): Promise<CapacityConflictsResponse> {
  return apiFetch<CapacityConflictsResponse>(`/api/v1/capacity/conflicts${qs(params)}`);
}
