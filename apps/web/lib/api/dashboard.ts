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
  /**
   * BUG-092 — `null` cuando la cartera mezcla monedas: ahí no hay un total.
   * El dato bueno es `budget_by_currency`; esto se conserva mientras haya una
   * sola moneda en juego y se retira cuando ningún consumidor lo lea.
   */
  budget_total: number | null;
  /** Un importe por moneda. Vacío cuando no hay presupuesto que sumar. */
  budget_by_currency: Record<string, number>;
  progress_avg: number | null;
  /**
   * US-206 — el avance **esperado por calendario** de los mismos proyectos que
   * `progress_avg`. La tarjeta enfrenta los dos y la resta solo significa algo
   * porque los dos lados cubren el mismo conjunto. `null` por lo mismo que el
   * otro: sin proyectos activos no hay avance del que hablar.
   */
  plan_progress_avg: number | null;
  /** US-206 — lo consumido, por moneda. Vacío cuando no hay nada gastado. */
  budget_consumed_by_currency: Record<string, number>;
  /**
   * US-206 — de los severos, los que no tiene nadie: ni `owner_id` ni
   * `owner_actor_id`. Siete severos es un estado; dos sin dueño es una tarea.
   */
  severe_risks_unassigned: number;
};

export type DashboardCharts = {
  projects_by_phase: Record<string, number>;
  progress_by_phase: Record<string, number>;
  budget_by_type: Record<string, number>;
  portfolio_health: Record<string, number>;
  /**
   * US-206 — las dos distribuciones del mockup que faltaban. La clave `""` es
   * «sin programa» y «sin sponsor»: la API no manda la etiqueta porque el
   * rótulo es vocabulario de interfaz, y el grupo existe de verdad — son los
   * proyectos que cuelgan del portafolio sin que nadie los coordine (DEC-030).
   */
  projects_by_program: Record<string, number>;
  projects_by_sponsor: Record<string, number>;
};

/** US-206 — un proyecto en la lista «top en riesgo». */
export type TopPorRiesgo = {
  project_id: string;
  folio: string;
  name: string;
  health: string | null;
  severe_risks: number;
};

/** US-206 — un proyecto en la lista «top con atraso». */
export type TopPorAtraso = {
  project_id: string;
  folio: string;
  name: string;
  health: string | null;
  progress_plan: number;
  progress_actual: number;
  /** Negativo: puntos por debajo del avance esperado por calendario. */
  delta_pts: number;
};

export type DashboardTops = {
  by_risk: TopPorRiesgo[];
  by_delay: TopPorAtraso[];
};

export type PlanVsActualRow = {
  project_id: string;
  folio: string;
  /** BUG-092 — la moneda del proyecto, ya resuelta por la API. */
  currency: string;
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
  /** US-201 — el nivel nuevo de la cascada. */
  portfolio_id?: string;
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

/** US-201 — la cascada completa. Los tres se acumulan en el servidor: una
 *  combinación que no se cruza devuelve vacío, no un error, porque quien
 *  combina dos filtros ajenos está explorando. */
export type DashboardFilter = {
  organization_id?: string;
  portfolio_id?: string;
  program_id?: string;
};

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

/**
 * US-206 — las dos listas cortas del tablero.
 *
 * La tercera del mockup —sobrecarga de recursos— no sale de aquí: viene de
 * `/capacity/summary`, que ya ordena por holgura y conoce los umbrales del
 * inquilino.
 */
export function getDashboardTops(
  params: DashboardFilter & { limite?: number } = {},
): Promise<DashboardTops> {
  return apiFetch<DashboardTops>(`/api/v1/dashboard/tops${qs(params)}`);
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
