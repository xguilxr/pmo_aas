import { apiFetch } from "@/lib/api";

export type DashboardKpis = {
  active_projects: number;
  requests_in_review: number;
  open_risks: number;
  severe_risks: number;
  change_requests_in_review: number;
  open_issues: number;
  // `null` = no hay nada que promediar ni que sumar, y NO cero (DAT-12).
  // `KpiCard` lo pinta «—». El tipo tiene que decirlo: con `number` a secas,
  // TypeScript dejaba pasar cualquier `?? 0` y el hueco volvía a leerse como
  // una cartera parada.
  budget_total: number | null;
  progress_avg: number | null;
};

export type DashboardCharts = {
  projects_by_phase: Record<string, number>;
  progress_by_phase: Record<string, number>;
  budget_by_type: Record<string, number>;
  portfolio_health: Record<string, number>;
};

export type PlanVsActualRow = {
  project_id: string;
  folio: string;
  name: string;
  end_date: string | null;
  budget_plan: number;
  budget_actual: number;
  progress_plan: number;
  progress_actual: number;
  health: string | null;
  pm_id: string | null;
  pm_name: string | null;
};

export type PlanVsActualParams = {
  organization_id?: string;
  program_id?: string;
  phase?: string;
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

export type DashboardFilter = { organization_id?: string };

export function getDashboardKpis(
  params: DashboardFilter = {},
): Promise<DashboardKpis> {
  return apiFetch<DashboardKpis>(`/api/v1/dashboard/kpis${qs(params)}`);
}

export function getDashboardCharts(
  params: DashboardFilter = {},
): Promise<DashboardCharts> {
  return apiFetch<DashboardCharts>(`/api/v1/dashboard/charts${qs(params)}`);
}

export function getPlanVsActual(
  params: PlanVsActualParams = {},
): Promise<PlanVsActualRow[]> {
  return apiFetch<PlanVsActualRow[]>(`/api/v1/dashboard/plan-vs-actual${qs(params)}`);
}

export function planVsActualCsvUrl(
  apiBase: string,
  params: PlanVsActualParams = {},
): string {
  return `${apiBase.replace(/\/+$/, "")}/api/v1/dashboard/plan-vs-actual/export.csv${qs(params)}`;
}
