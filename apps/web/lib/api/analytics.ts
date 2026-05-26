import { apiFetch } from "@/lib/api";

// US-152 — cliente de los endpoints de analytics para dashboards N1/N2.

export type ScopeType = "tenant" | "organization" | "program" | "project";

export type ScopeParams = {
  scope?: ScopeType;
  id?: string;
};

export type TrendPoint = {
  snapshot_date: string;
  [metric: string]: number | string;
};

export type TrendsResponse = {
  scope: ScopeType;
  scope_id: string;
  metric: string | null;
  series: TrendPoint[];
};

export type RiskMatrixCell = {
  probability: number;
  impact: number;
  count: number;
};

export type RiskMatrixResponse = {
  cells: RiskMatrixCell[];
  total: number;
};

export type HeatmapRow = {
  org_id: string;
  org_name: string;
  green: number;
  yellow: number;
  red: number;
  total: number;
};

export type HeatmapResponse = { rows: HeatmapRow[] };

export type TreemapProject = {
  id: string;
  name: string;
  folio: string;
  value: number;
  health: string | null;
};
export type TreemapProgram = { id: string; name: string; children: TreemapProject[] };
export type TreemapOrg = { id: string; name: string; children: TreemapProgram[] };
export type TreemapResponse = { tree: TreemapOrg[] };

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function getTrends(
  params: ScopeParams & { metric?: string; weeks?: number } = {},
): Promise<TrendsResponse> {
  return apiFetch<TrendsResponse>(`/api/v1/dashboard/trends${qs(params)}`);
}

export function getRiskMatrix(params: ScopeParams = {}): Promise<RiskMatrixResponse> {
  return apiFetch<RiskMatrixResponse>(`/api/v1/dashboard/risk-matrix${qs(params)}`);
}

export function getHeatmap(): Promise<HeatmapResponse> {
  return apiFetch<HeatmapResponse>(`/api/v1/dashboard/heatmap`);
}

export function getTreemap(params: ScopeParams = {}): Promise<TreemapResponse> {
  return apiFetch<TreemapResponse>(`/api/v1/dashboard/treemap${qs(params)}`);
}

export function captureSnapshots(): Promise<{ date: string; rows: number }> {
  return apiFetch<{ date: string; rows: number }>(
    `/api/v1/dashboard/snapshots/capture`,
    { method: "POST" },
  );
}
