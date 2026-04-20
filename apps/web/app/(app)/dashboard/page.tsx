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
import { Bars, Legend, PALETTE, Pie } from "@/components/dashboard-charts";
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
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import { getStoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

const PHASE_LABEL: Record<string, string> = {
  planning: "Planificación",
  execution: "Ejecución",
  support: "Soporte",
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
  green: PALETTE.success,
  yellow: PALETTE.warning,
  red: PALETTE.danger,
};

const PHASE_COLOR: Record<string, string> = {
  planning: PALETTE.info,
  execution: PALETTE.accent,
  support: PALETTE.warning,
  closed: PALETTE.neutral,
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
  const [loadingRows, setLoadingRows] = useState(true);

  // Sincronizar cambio de filtro con URL (US-NEW-014: estado del filtro en URL).
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
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section aria-label="Indicadores" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Proyectos activos"
          value={kpis?.active_projects ?? 0}
          loading={loadingKpis}
          icon={<Briefcase className="h-4 w-4" aria-hidden />}
          tone="accent"
          href="/admin/projects?phase=planning&phase=execution&phase=support"
        />
        <KpiCard
          label="Solicitudes en revisión"
          value={kpis?.requests_in_review ?? 0}
          loading={loadingKpis}
          icon={<ClipboardList className="h-4 w-4" aria-hidden />}
          href="/admin/requests"
        />
        <KpiCard
          label="Riesgos abiertos"
          value={kpis?.open_risks ?? 0}
          loading={loadingKpis}
          icon={<AlertTriangle className="h-4 w-4" aria-hidden />}
          tone="warning"
          href="/risks"
        />
        <KpiCard
          label="Riesgos severos"
          value={kpis?.severe_risks ?? 0}
          loading={loadingKpis}
          icon={<AlertOctagon className="h-4 w-4" aria-hidden />}
          tone="danger"
          href="/risks?severity_min=13"
        />
        <KpiCard
          label="Cambios en revisión"
          value={kpis?.change_requests_in_review ?? 0}
          loading={loadingKpis}
          icon={<GitPullRequest className="h-4 w-4" aria-hidden />}
          href="/changes"
        />
        <KpiCard
          label="AIDs abiertos"
          value={kpis?.open_issues ?? 0}
          loading={loadingKpis}
          icon={<FileWarning className="h-4 w-4" aria-hidden />}
          href="/issues"
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

      <section
        aria-label="Plan vs Real"
        className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]"
      >
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-default)] p-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
            <h2 className="text-base font-semibold text-[var(--color-primary)]">Plan vs Real</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
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
              className="inline-flex h-9 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-subtle)]"
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
                <th className="px-4 py-3 font-medium">Proyecto</th>
                <th className="px-4 py-3 font-medium">Fin plan</th>
                <th className="px-4 py-3 font-medium">Presupuesto plan</th>
                <th className="px-4 py-3 font-medium">Presupuesto real</th>
                <th className="px-4 py-3 font-medium">Avance plan</th>
                <th className="px-4 py-3 font-medium">Avance real</th>
                <th className="px-4 py-3 font-medium">Salud</th>
              </tr>
            </thead>
            <tbody>
              {loadingRows ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <Skeleton className="h-4 w-24" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : rows.length > 0 ? (
                rows.map((r) => (
                  <tr
                    key={r.project_id}
                    className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/projects/${r.project_id}`}
                        className="font-medium text-[var(--color-primary)] hover:underline"
                      >
                        {r.name}
                      </Link>
                      <div className="text-xs text-[var(--color-tertiary)]">{r.folio}</div>
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
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
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
  if (!health) return <span className="text-xs text-[var(--color-tertiary)]">—</span>;
  const style =
    health === "green"
      ? "bg-[var(--color-success-bg)] text-[var(--color-success-fg)] border-[var(--color-success-border)]"
      : health === "yellow"
        ? "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)] border-[var(--color-warning-border)]"
        : health === "red"
          ? "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)] border-[var(--color-danger-border)]"
          : "bg-[var(--color-subtle)] text-[var(--color-secondary)] border-[var(--border-default)]";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] border px-2 py-0.5 text-xs font-medium",
        style,
      )}
    >
      <span
        aria-hidden
        className={cn(
          "inline-block h-1.5 w-1.5 rounded-full",
          health === "green"
            ? "bg-[var(--color-success-fg)]"
            : health === "yellow"
              ? "bg-[var(--color-warning-fg)]"
              : "bg-[var(--color-danger-fg)]",
        )}
      />
      {HEALTH_LABEL[health] ?? health}
    </span>
  );
}
