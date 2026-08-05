"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  BarChart3,
  Briefcase,
  CircleDollarSign,
  ClipboardList,
  Download,
  FileWarning,
  GitPullRequest,
  TrendingUp,
} from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Bars,
  Heatmap,
  Legend,
  PALETTE,
  Pie,
  RiskMatrix,
  TrendLines,
  Treemap,
} from "@/components/dashboard-charts";
import { KpiCard } from "@/components/kpi-card";
import { ApiError } from "@/lib/api";
import {
  getDashboardCharts,
  getDashboardKpis,
  getPlanVsActual,
  planVsActualCsvUrl,
  type DashboardCharts as ChartsData,
  type DashboardKpis,
  type PlanVsActualRow,
} from "@/lib/api/dashboard";
import {
  captureSnapshots,
  getHeatmap,
  getRiskMatrix,
  getTreemap,
  getTrends,
  type HeatmapResponse,
  type RiskMatrixResponse,
  type TreemapResponse,
  type TrendsResponse,
} from "@/lib/api/analytics";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import { getStoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";

const PHASE_LABEL: Record<string, string> = {
  planning: "Planificación",
  execution: "Ejecución",
  hypercare: "Hypercare",
  closed: "Cerrado",
};

const TYPE_LABEL: Record<string, string> = {
  innovation: "Innovación",
  transformation: "Transformación",
  operation: "Operación",
  bau: "BAU",
  unspecified: "Sin especificar",
};

const HEALTH_LABEL: Record<string, string> = {
  green: "Verde",
  yellow: "Amarillo",
  red: "Rojo",
};

const HEALTH_COLOR: Record<string, string> = {
  green: "var(--color-success-fg)",
  yellow: "var(--color-warning-fg)",
  red: "var(--color-danger-fg)",
};

// ADR-023: la fase es ORDINAL —planificación → ejecución → hypercare → cerrado
// es una secuencia—, así que va con la rampa de un solo tono, no con cuatro
// colores sueltos. `cancelled` se sale de la secuencia y va al neutro, igual
// que en su insignia.
//
// De paso: esta tabla seguía diciendo `support`, que D-2 renombró. No fallaba
// —es una clave suelta— simplemente dejaba la fase sin color.
const PHASE_COLOR: Record<string, string> = {
  planning: PALETTE.scale[0],
  execution: PALETTE.scale[2],
  hypercare: PALETTE.scale[3],
  closed: PALETTE.scale[4],
  cancelled: PALETTE.neutral,
};

function toEntries<T>(obj: Record<string, T>): [string, T][] {
  return Object.keys(obj).map((k) => [k, obj[k]]);
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <DashboardInner />
    </Suspense>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-48" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    </div>
  );
}

function DashboardInner() {
  const user = getStoredUser();
  const router = useRouter();
  const searchParams = useSearchParams();
  const orgFromUrl = searchParams.get("org_id") ?? "";

  const [kpis, setKpis] = useState<DashboardKpis | null>(null);
  const [charts, setCharts] = useState<ChartsData | null>(null);
  const [loadingKpis, setLoadingKpis] = useState(true);
  const [loadingCharts, setLoadingCharts] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgFilter, setOrgFilter] = useState(orgFromUrl);
  const [phaseFilter, setPhaseFilter] = useState("");

  const [rows, setRows] = useState<PlanVsActualRow[]>([]);
  const { sortedRows: sortedDashRows, ctrl: dashCtrl } = useSortableRows<PlanVsActualRow>(rows);
  const [loadingRows, setLoadingRows] = useState(true);

  // US-154 — analíticas ricas (tendencias, matriz de riesgos, heatmap, treemap).
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrixResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [treemap, setTreemap] = useState<TreemapResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  // El heatmap/treemap/trends agregados son admin-equivalente; si la primera
  // llamada 403ea, ocultamos esas secciones (detección por capacidad).
  const [isAdminView, setIsAdminView] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [captureMsg, setCaptureMsg] = useState<string | null>(null);

  const analyticsScope = orgFilter ? ("organization" as const) : ("tenant" as const);

  useEffect(() => {
    let cancelled = false;
    const scopeParams = { scope: analyticsScope, id: orgFilter || undefined };

    // Matriz de riesgos: disponible para todos los roles (scoped por proyecto).
    getRiskMatrix(scopeParams)
      .then((r) => !cancelled && setRiskMatrix(r))
      .catch(() => !cancelled && setRiskMatrix(null));

    // Vistas agregadas (admin-equivalente).
    getHeatmap()
      .then((r) => {
        if (cancelled) return;
        setHeatmap(r);
        setIsAdminView(true);
      })
      .catch(() => {
        if (cancelled) return;
        setHeatmap(null);
        setIsAdminView(false);
      });
    getTreemap(scopeParams)
      .then((r) => !cancelled && setTreemap(r))
      .catch(() => !cancelled && setTreemap(null));
    getTrends({ ...scopeParams, weeks: 12 })
      .then((r) => !cancelled && setTrends(r))
      .catch(() => !cancelled && setTrends(null));

    return () => {
      cancelled = true;
    };
  }, [orgFilter, analyticsScope]);

  async function handleCapture() {
    setCapturing(true);
    setCaptureMsg(null);
    try {
      const res = await captureSnapshots();
      setCaptureMsg(`Snapshot capturado (${res.rows} filas).`);
      const refreshed = await getTrends({
        scope: analyticsScope,
        id: orgFilter || undefined,
        weeks: 12,
      });
      setTrends(refreshed);
    } catch (err) {
      setCaptureMsg(
        err instanceof ApiError ? err.message : "No se pudo capturar el snapshot",
      );
    } finally {
      setCapturing(false);
    }
  }

  // Sincronizar cambio de filtro con URL (US-014: estado del filtro en URL).
  function changeOrgFilter(next: string) {
    setOrgFilter(next);
    const params = new URLSearchParams(searchParams.toString());
    if (next) params.set("org_id", next);
    else params.delete("org_id");
    const qs = params.toString();
    router.replace(qs ? `/dashboard?${qs}` : "/dashboard");
  }

  useEffect(() => {
    let cancelled = false;
    listOrganizations({ is_active: true })
      .then((r) => {
        if (!cancelled) setOrgs(r);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // KPIs + Charts se refetchean al cambiar el filtro de organización.
  useEffect(() => {
    let cancelled = false;
    setLoadingKpis(true);
    setLoadingCharts(true);
    const filter = { organization_id: orgFilter || undefined };
    getDashboardKpis(filter)
      .then((r) => {
        if (!cancelled) setKpis(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudo cargar el tablero",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingKpis(false);
      });
    getDashboardCharts(filter)
      .then((r) => {
        if (!cancelled) setCharts(r);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingCharts(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgFilter]);

  useEffect(() => {
    let cancelled = false;
    setLoadingRows(true);
    getPlanVsActual({
      organization_id: orgFilter || undefined,
      phase: phaseFilter || undefined,
    })
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingRows(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgFilter, phaseFilter]);

  const phasesData = useMemo(() => {
    const entries = charts ? toEntries(charts.projects_by_phase) : [];
    return entries.map(([k, v]) => ({
      label: PHASE_LABEL[k] ?? k,
      value: Number(v) || 0,
      color: PHASE_COLOR[k] ?? PALETTE.accent,
    }));
  }, [charts]);

  const progressData = useMemo(() => {
    const entries = charts ? toEntries(charts.progress_by_phase) : [];
    return entries.map(([k, v]) => ({
      label: PHASE_LABEL[k] ?? k,
      value: Math.round(Number(v) || 0),
      color: PHASE_COLOR[k] ?? PALETTE.accent,
    }));
  }, [charts]);

  const budgetData = useMemo(() => {
    const entries = charts ? toEntries(charts.budget_by_type) : [];
    return entries.map(([k, v]) => ({
      label: TYPE_LABEL[k] ?? k,
      value: Number(v) || 0,
      color: PALETTE.accent,
    }));
  }, [charts]);

  const healthData = useMemo(() => {
    const entries = charts ? toEntries(charts.portfolio_health) : [];
    return entries.map(([k, v]) => ({
      label: HEALTH_LABEL[k] ?? k,
      value: Number(v) || 0,
      color: HEALTH_COLOR[k] ?? PALETTE.neutral,
    }));
  }, [charts]);

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
  const csvHref = planVsActualCsvUrl(apiBase, {
    organization_id: orgFilter || undefined,
    phase: phaseFilter || undefined,
  });

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Tablero, {user?.full_name || user?.username || "usuario"}
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            KPIs, salud del portafolio y Plan vs Real.
            {orgFilter
              ? ` · Filtrando por: ${orgs.find((o) => o.id === orgFilter)?.name ?? "organización"}`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label
            htmlFor="org-filter"
            className="text-xs font-medium text-[var(--color-tertiary)]"
          >
            Organización
          </label>
          <Select
            id="org-filter"
            value={orgFilter}
            onChange={(e) => changeOrgFilter(e.target.value)}
            aria-label="Filtrar por organización"
            className="min-w-[220px]"
          >
            <option value="">Todas las organizaciones</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </Select>
          {orgFilter ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => changeOrgFilter("")}
            >
              Limpiar
            </Button>
          ) : null}
          {isAdminView ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleCapture}
              disabled={capturing}
              title="Captura el snapshot de hoy para alimentar las tendencias"
            >
              {capturing ? "Capturando…" : "Capturar snapshot"}
            </Button>
          ) : null}
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {captureMsg ? <Banner variant="info">{captureMsg}</Banner> : null}

      <section aria-label="Indicadores" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Proyectos activos"
          value={kpis?.active_projects ?? 0}
          loading={loadingKpis}
          icon={<Briefcase className="h-4 w-4" aria-hidden />}
          tone="accent"
          href="/pmo/projects?phase=planning&phase=execution&phase=support"
        />
        <KpiCard
          label="Solicitudes en revisión"
          value={kpis?.requests_in_review ?? 0}
          loading={loadingKpis}
          icon={<ClipboardList className="h-4 w-4" aria-hidden />}
          href="/pmo/requests"
        />
        <KpiCard
          label="Riesgos abiertos"
          value={kpis?.open_risks ?? 0}
          loading={loadingKpis}
          icon={<AlertTriangle className="h-4 w-4" aria-hidden />}
          tone="warning"
          href="/pmo/raid?kind=risks"
        />
        <KpiCard
          label="Riesgos severos"
          value={kpis?.severe_risks ?? 0}
          loading={loadingKpis}
          icon={<AlertOctagon className="h-4 w-4" aria-hidden />}
          tone="danger"
          href="/pmo/raid?kind=risks&severity_min=13"
        />
        <KpiCard
          label="Cambios en revisión"
          value={kpis?.change_requests_in_review ?? 0}
          loading={loadingKpis}
          icon={<GitPullRequest className="h-4 w-4" aria-hidden />}
          href="/pmo/changes?status=in_review"
        />
        <KpiCard
          label="AIDs abiertos"
          value={kpis?.open_issues ?? 0}
          loading={loadingKpis}
          icon={<FileWarning className="h-4 w-4" aria-hidden />}
          href="/pmo/raid?kind=issues"
        />
        <KpiCard
          label="Presupuesto total"
          value={kpis?.budget_total ?? 0}
          loading={loadingKpis}
          format="currency-mxn"
          icon={<CircleDollarSign className="h-4 w-4" aria-hidden />}
        />
        <KpiCard
          label="Avance promedio"
          value={kpis?.progress_avg ?? 0}
          loading={loadingKpis}
          format="percent"
          icon={<TrendingUp className="h-4 w-4" aria-hidden />}
          tone="success"
        />
      </section>

      <section aria-label="Gráficos" className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Proyectos por fase" loading={loadingCharts}>
          <div className="flex items-center gap-4">
            <Pie data={phasesData} ariaLabel="Proyectos por fase" />
            <div className="flex-1">
              <Legend data={phasesData} />
            </div>
          </div>
        </ChartCard>
        <ChartCard title="Salud del portafolio" loading={loadingCharts}>
          <div className="flex items-center gap-4">
            <Pie data={healthData} ariaLabel="Salud del portafolio" />
            <div className="flex-1">
              <Legend data={healthData} />
            </div>
          </div>
        </ChartCard>
        <ChartCard title="Avance promedio por fase" loading={loadingCharts}>
          <Bars
            data={progressData}
            ariaLabel="Avance promedio por fase"
            valueFormat={(n) => `${n}%`}
          />
        </ChartCard>
        <ChartCard title="Presupuesto por tipo" loading={loadingCharts}>
          <Bars
            data={budgetData}
            ariaLabel="Presupuesto por tipo"
            valueFormat={(n) =>
              new Intl.NumberFormat("es-MX", {
                style: "currency",
                currency: "MXN",
                maximumFractionDigits: 0,
              }).format(n)
            }
          />
        </ChartCard>
      </section>

      <section aria-label="Riesgos y salud" className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Matriz de riesgos (probabilidad × impacto)">
          {riskMatrix && riskMatrix.total > 0 ? (
            <RiskMatrix cells={riskMatrix.cells} ariaLabel="Matriz de riesgos" />
          ) : (
            <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
              Sin riesgos abiertos con probabilidad e impacto definidos.
            </p>
          )}
        </ChartCard>
        {isAdminView ? (
          <ChartCard title="Salud por organización">
            <Heatmap
              rows={heatmap?.rows ?? []}
              ariaLabel="Mapa de calor de salud por organización"
              onCellClick={(orgId) => changeOrgFilter(orgId)}
            />
          </ChartCard>
        ) : null}
      </section>

      {isAdminView ? (
        <section aria-label="Tendencias y portafolio" className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="Tendencias (últimas 12 semanas)">
            {(trends?.series.length ?? 0) > 0 ? (
              <div className="grid gap-4 sm:grid-cols-3">
                <TrendMini
                  label="Avance promedio"
                  trends={trends}
                  metric="avg_progress"
                  color="var(--color-success-fg)"
                  valueFormat={(n) => `${Math.round(n)}%`}
                />
                <TrendMini
                  label="Riesgos abiertos"
                  trends={trends}
                  metric="open_risks"
                  color="var(--color-warning-fg)"
                />
                <TrendMini
                  label="Proyectos activos"
                  trends={trends}
                  metric="projects_active"
                  color={PALETTE.accent}
                />
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
                Aún no hay historia. Usa “Capturar snapshot” para sembrar el primer
                punto; el job semanal llena el resto.
              </p>
            )}
          </ChartCard>
          <ChartCard title="Portafolio (presupuesto × salud)">
            <Treemap tree={treemap?.tree ?? []} ariaLabel="Treemap del portafolio" />
          </ChartCard>
        </section>
      ) : null}

      <section
        aria-label="Plan vs Real"
        className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]"
      >
        <header className="flex flex-col gap-3 border-b border-[var(--border-default)] p-4 sm:flex-row sm:flex-nowrap sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
            <h2 className="text-base font-semibold text-[var(--color-primary)]">Plan vs Real</h2>
          </div>
          <div className="flex flex-nowrap items-center gap-2">
            <Select
              aria-label="Filtrar por organización"
              value={orgFilter}
              onChange={(e) => changeOrgFilter(e.target.value)}
              className="h-9"
            >
              <option value="">Todas las organizaciones</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Filtrar por fase"
              value={phaseFilter}
              onChange={(e) => setPhaseFilter(e.target.value)}
              className="h-9"
            >
              <option value="">Todas las fases</option>
              {Object.entries(PHASE_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
            <a
              href={csvHref}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-subtle)]"
            >
              <Download className="h-4 w-4" aria-hidden />
              Exportar CSV
            </a>
          </div>
        </header>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <SortableTh<PlanVsActualRow> sortKey="project" getter={(r) => (r as any).project_name ?? ""} ctrl={dashCtrl} className="px-4 py-3">Proyecto</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="pm" getter={(r) => (r as any).pm_name ?? ""} ctrl={dashCtrl} className="px-4 py-3">PM asignado</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="end_plan" getter={(r) => (r as any).end_plan ?? ""} ctrl={dashCtrl} className="px-4 py-3">Fin plan</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="budget_plan" getter={(r) => (r as any).budget_plan ?? 0} ctrl={dashCtrl} className="px-4 py-3">Presupuesto plan</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="budget_actual" getter={(r) => (r as any).budget_actual ?? 0} ctrl={dashCtrl} className="px-4 py-3">Presupuesto real</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="progress_plan" getter={(r) => (r as any).progress_plan ?? 0} ctrl={dashCtrl} className="px-4 py-3">Avance plan</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="progress_actual" getter={(r) => (r as any).progress_actual ?? 0} ctrl={dashCtrl} className="px-4 py-3">Avance real</SortableTh>
                <SortableTh<PlanVsActualRow> sortKey="health" getter={(r) => (r as any).health ?? ""} ctrl={dashCtrl} className="px-4 py-3">Salud</SortableTh>
              </tr>
            </thead>
            <tbody>
              {loadingRows ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <Skeleton className="h-4 w-24" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : sortedDashRows.length > 0 ? (
                sortedDashRows.map((r) => (
                  <tr
                    key={r.project_id}
                    className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/pmo/projects/${r.project_id}`}
                        className="font-medium text-[var(--color-primary)] hover:underline"
                      >
                        {r.name}
                      </Link>
                      <div className="text-xs text-[var(--color-tertiary)]">{r.folio}</div>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      {r.pm_id && r.pm_name ? (
                        <Link
                          href={`/admin/users/${r.pm_id}`}
                          className="text-[var(--color-primary)] hover:underline"
                        >
                          {r.pm_name}
                        </Link>
                      ) : (
                        <span className="text-[var(--color-tertiary)]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      {r.end_date ? new Date(r.end_date).toLocaleDateString("es-MX") : "—"}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)] tabular-nums">
                      {new Intl.NumberFormat("es-MX", {
                        style: "currency",
                        currency: "MXN",
                        maximumFractionDigits: 0,
                      }).format(r.budget_plan)}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)] tabular-nums">
                      {new Intl.NumberFormat("es-MX", {
                        style: "currency",
                        currency: "MXN",
                        maximumFractionDigits: 0,
                      }).format(r.budget_actual)}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      <ProgressBar value={r.progress_plan} />
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      <ProgressBar value={r.progress_actual} tone="accent" />
                    </td>
                    <td className="px-4 py-3">
                      <HealthDot health={r.health} />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
                    No hay proyectos que coincidan con los filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <table className="sr-only" aria-label="Datos Plan vs Real en tabla accesible">
        <thead>
          <tr>
            <th>Proyecto</th>
            <th>Folio</th>
            <th>Presupuesto plan</th>
            <th>Presupuesto real</th>
            <th>Avance plan %</th>
            <th>Avance real %</th>
            <th>Salud</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`sr-${r.project_id}`}>
              <td>{r.name}</td>
              <td>{r.folio}</td>
              <td>{r.budget_plan}</td>
              <td>{r.budget_actual}</td>
              <td>{r.progress_plan}</td>
              <td>{r.progress_actual}</td>
              <td>{r.health ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TrendMini({
  label,
  trends,
  metric,
  color,
  valueFormat,
}: {
  label: string;
  trends: TrendsResponse | null;
  metric: string;
  color: string;
  valueFormat?: (n: number) => string;
}) {
  const data = (trends?.series ?? []).map((p) => ({
    x: p.snapshot_date,
    y: Number(p[metric] ?? 0),
  }));
  const last = data.length ? data[data.length - 1].y : 0;
  const prev = data.length > 1 ? data[data.length - 2].y : last;
  const delta = last - prev;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
          {label}
        </span>
        <span className="text-sm font-semibold tabular-nums text-[var(--color-primary)]">
          {valueFormat ? valueFormat(last) : last}
        </span>
      </div>
      <TrendLines data={data} ariaLabel={`Tendencia de ${label}`} color={color} valueFormat={valueFormat} />
      <p className="text-[11px] tabular-nums text-[var(--color-tertiary)]">
        {delta === 0 ? "Sin cambio" : `${delta > 0 ? "▲" : "▼"} ${valueFormat ? valueFormat(Math.abs(delta)) : Math.abs(delta)} vs. semana previa`}
      </p>
    </div>
  );
}

function ChartCard({
  title,
  children,
  loading,
}: {
  title: string;
  children: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">{title}</h2>
      {loading ? <Skeleton className="h-[180px] w-full" /> : children}
    </article>
  );
}

function ProgressBar({ value, tone }: { value: number; tone?: "accent" }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-muted)]">
        <div
          className={cn(
            "h-full rounded-full transition-[width]",
            tone === "accent" ? "bg-[var(--color-accent)]" : "bg-[var(--color-secondary)]",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-xs tabular-nums text-[var(--color-secondary)]">
        {pct}%
      </span>
    </div>
  );
}

function HealthDot({ health }: { health: string | null }) {
  // ENH-110: semáforo de salud = solo el color (círculo), sin la palabra.
  // El estado se preserva en title/aria-label para accesibilidad.
  if (!health) return <span className="text-xs text-[var(--color-tertiary)]">—</span>;
  const dotColor =
    health === "green"
      ? "bg-[var(--color-success-fg)]"
      : health === "yellow"
        ? "bg-[var(--color-warning-fg)]"
        : health === "red"
          ? "bg-[var(--color-danger-fg)]"
          : "bg-[var(--color-tertiary)]";
  const label = HEALTH_LABEL[health] ?? health;
  return (
    <span
      title={label}
      aria-label={label}
      role="img"
      className={cn("inline-block h-2.5 w-2.5 rounded-full", dotColor)}
    />
  );
}
