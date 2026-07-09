"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, Download, FileText, FolderKanban, Layers, TrendingUp, Users } from "lucide-react";

import { BackLink } from "@/components/back-link";
import { KpiCard } from "@/components/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ScopedReportsPanel } from "@/components/reports/level2/ScopedReportsPanel";
import { Gauge, Legend, PALETTE, Pie, RiskMatrix, TrendLines } from "@/components/dashboard-charts";
import { ApiError } from "@/lib/api";
import {
  downloadProgramOrganigrama,
  downloadProgramStatusReport,
  getRiskMatrix,
  getTrends,
  type RiskMatrixResponse,
  type TrendsResponse,
} from "@/lib/api/analytics";
import { getProgramSummary, type ProgramSummary } from "@/lib/api/organizations";

type ProgramTab = "overview" | "reports";

// BUG-069: usa los mismos tokens de marca que la org page (un solo set de
// verdes/amarillos/rojos) en vez de variables CSS inexistentes.
const HEALTH_LABEL: Record<string, string> = { green: "Verde", yellow: "Amarillo", red: "Rojo" };
const HEALTH_FILL: Record<string, string> = {
  green: PALETTE.success,
  yellow: PALETTE.warning,
  red: PALETTE.danger,
};

function healthToData(health: { green: number; yellow: number; red: number }) {
  return (["green", "yellow", "red"] as const).map((k) => ({
    label: HEALTH_LABEL[k],
    value: health[k],
    color: HEALTH_FILL[k],
  }));
}

function ProgTrend({
  label,
  trends,
  metric,
  color,
  fmt,
}: {
  label: string;
  trends: TrendsResponse | null;
  metric: string;
  color: string;
  fmt?: (n: number) => string;
}) {
  const series = (trends?.series ?? []).map((p) => ({ x: p.snapshot_date, y: Number(p[metric] ?? 0) }));
  const last = series.length ? series[series.length - 1].y : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-[var(--color-primary)]">{fmt ? fmt(last) : last}</span>
      </div>
      <TrendLines data={series} ariaLabel={`Tendencia de ${label}`} color={color} valueFormat={fmt} />
    </div>
  );
}

function healthBadge(h: string | null) {
  if (!h) return null;
  // ENH-110: salud = solo el color (círculo), sin la palabra.
  const color =
    h === "green"
      ? "bg-[var(--color-success-fg)]"
      : h === "yellow"
        ? "bg-[var(--color-warning-fg)]"
        : "bg-[var(--color-danger-fg)]";
  const label = h === "green" ? "Verde" : h === "yellow" ? "Amarillo" : h === "red" ? "Rojo" : h;
  return (
    <span
      title={label}
      aria-label={label}
      role="img"
      className={`inline-block h-2.5 w-2.5 rounded-full ${color}`}
    />
  );
}

function money(n: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(n);
}

export default function ProgramSummaryPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const ctx = searchParams.get("ctx") === "admin" ? "admin" : "pmo";
  // US-137: tabs "Resumen" | "Reportes" via ?tab=.
  const activeTab: ProgramTab =
    searchParams.get("tab") === "reports" ? "reports" : "overview";
  const orgHref = (orgId: string) =>
    ctx === "admin" ? `/admin/organizations/${orgId}` : `/pmo/organizations/${orgId}`;
  const portfolioHref = ctx === "admin" ? "/admin" : "/pmo";
  const portfolioLabel = ctx === "admin" ? "Admin" : "Portafolio";
  const [data, setData] = useState<ProgramSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // US-157 — analítica program-scoped.
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrixResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [downloadingReport, setDownloadingReport] = useState(false);

  // US-187 — organigrama con utilización (XLSX), scope programa.
  const [downloadingOrganigrama, setDownloadingOrganigrama] = useState(false);
  const [organigramaError, setOrganigramaError] = useState<string | null>(null);

  async function handleDownloadReport() {
    setDownloadingReport(true);
    try {
      await downloadProgramStatusReport(params.id);
    } catch {
      /* silencioso */
    } finally {
      setDownloadingReport(false);
    }
  }

  async function handleDownloadOrganigrama() {
    setDownloadingOrganigrama(true);
    setOrganigramaError(null);
    try {
      await downloadProgramOrganigrama(params.id);
    } catch (err) {
      setOrganigramaError(
        err instanceof ApiError ? err.message : "No se pudo generar el organigrama",
      );
    } finally {
      setDownloadingOrganigrama(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProgramSummary(params.id)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el programa");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  useEffect(() => {
    let cancelled = false;
    getRiskMatrix({ scope: "program", id: params.id })
      .then((r) => !cancelled && setRiskMatrix(r))
      .catch(() => !cancelled && setRiskMatrix(null));
    getTrends({ scope: "program", id: params.id, weeks: 12 })
      .then((r) => !cancelled && setTrends(r))
      .catch(() => !cancelled && setTrends(null));
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error && !data) {
    return (
      <div className="mx-auto max-w-4xl">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center gap-2">
        <BackLink
          fallbackHref={
            data.organization_id ? orgHref(data.organization_id) : portfolioHref
          }
        />
        <Breadcrumb
          items={[
            { href: portfolioHref, label: portfolioLabel },
            data.organization_name
              ? {
                  href: orgHref(data.organization_id),
                  label: data.organization_name,
                }
              : { label: "Organización" },
            { label: data.name },
          ]}
        />
      </div>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
            <Layers className="h-6 w-6" aria-hidden />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              {data.name}
            </h1>
            <div className="mt-1 flex items-center gap-2 text-xs text-[var(--color-tertiary)]">
              {data.organization_name ?? ""}
              {!data.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
            </div>
            {data.description ? (
              <p className="mt-1 max-w-xl text-sm text-[var(--color-secondary)]">
                {data.description}
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {trends !== null ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDownloadReport}
              disabled={downloadingReport}
              title="Descarga el reporte de status del programa en PDF"
            >
              <Download className="mr-1 h-3.5 w-3.5" aria-hidden />
              {downloadingReport ? "Generando…" : "Status (PDF)"}
            </Button>
          ) : null}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleDownloadOrganigrama}
            disabled={downloadingOrganigrama}
            title="Descarga el organigrama con utilización del programa en XLSX"
          >
            <Users className="mr-1 h-3.5 w-3.5" aria-hidden />
            {downloadingOrganigrama ? "Generando…" : "Organigrama (XLSX)"}
          </Button>
        </div>
      </header>

      {organigramaError ? <Banner variant="danger">{organigramaError}</Banner> : null}

      {/* US-137: tabs Resumen / Reportes */}
      <div
        role="tablist"
        aria-label="Vistas del programa"
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
      >
        {(
          [
            { v: "overview" as const, label: "Resumen", icon: <Layers className="h-3.5 w-3.5" aria-hidden /> },
            { v: "reports" as const, label: "Reportes", icon: <FileText className="h-3.5 w-3.5" aria-hidden /> },
          ]
        ).map((opt) => {
          const active = activeTab === opt.v;
          const sp = new URLSearchParams(searchParams.toString());
          if (opt.v === "overview") sp.delete("tab");
          else sp.set("tab", "reports");
          const href = `/pmo/programs/${params.id}${sp.toString() ? `?${sp.toString()}` : ""}`;
          return (
            <Link
              key={opt.v}
              href={href}
              role="tab"
              aria-selected={active}
              className={`inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] px-4 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]"
              }`}
            >
              {opt.icon}
              {opt.label}
            </Link>
          );
        })}
      </div>

      {activeTab === "reports" ? (
        <section className="space-y-3">
          <p className="text-sm text-[var(--text-secondary)]">
            Plantillas Nivel 2 aplicadas con scope filtrado a este programa.
          </p>
          <ScopedReportsPanel scope={{ kind: "program", id: params.id }} />
        </section>
      ) : (
        <>
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Proyectos" value={data.project_total} tone="accent" />
        <KpiCard label="Activos" value={data.project_active} />
        <KpiCard label="En riesgo" value={data.project_at_risk} tone={data.project_at_risk > 0 ? "warning" : "neutral"} />
        <KpiCard label="Cerrados" value={data.project_closed} />
      </section>

      <section className="grid gap-3 md:grid-cols-[auto_1fr]">
        <div className="flex flex-col items-center gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
          <div className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Salud del portafolio
          </div>
          <Pie data={healthToData(data.health)} ariaLabel="Salud del portafolio" size={140} />
          <div className="w-full max-w-[180px]">
            <Legend data={healthToData(data.health)} />
          </div>
        </div>

        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
            <TrendingUp className="h-4 w-4" aria-hidden /> Presupuesto agregado
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-[var(--color-tertiary)]">Plan</dt>
              <dd className="text-xl font-semibold tabular-nums">
                {money(data.budget_planned)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-tertiary)]">Real</dt>
              <dd className="text-xl font-semibold tabular-nums">
                {money(data.budget_actual)}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-xs text-[var(--color-tertiary)]">Desviación</dt>
              <dd className="text-sm tabular-nums">
                {data.budget_planned > 0
                  ? `${(((data.budget_actual - data.budget_planned) / data.budget_planned) * 100).toFixed(1)}%`
                  : "—"}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section aria-label="Analítica del programa" className="grid gap-3 lg:grid-cols-3">
        {(() => {
          const projects = data.projects ?? [];
          const avgProgress = projects.length
            ? Math.round(projects.reduce((a, p) => a + (p.progress ?? 0), 0) / projects.length)
            : 0;
          const consumedRaw =
            data.budget_planned > 0 ? (data.budget_actual / data.budget_planned) * 100 : 0;
          const consumedTone =
            consumedRaw > 100 ? "danger" : consumedRaw >= 80 ? "warning" : "success";
          return (
            <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
              <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">Indicadores</h2>
              <div className="flex items-center justify-around gap-3">
                <div className="flex flex-col items-center gap-1">
                  <Gauge value={avgProgress} ariaLabel="Avance promedio" tone="accent" />
                  <span className="text-xs text-[var(--color-tertiary)]">Avance</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <Gauge value={consumedRaw} ariaLabel="Presupuesto consumido" tone={consumedTone} />
                  <span className="text-xs text-[var(--color-tertiary)]">Presupuesto</span>
                </div>
              </div>
            </article>
          );
        })()}
        <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
          <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">Matriz de riesgos</h2>
          {riskMatrix && riskMatrix.total > 0 ? (
            <RiskMatrix cells={riskMatrix.cells} ariaLabel="Matriz de riesgos del programa" />
          ) : (
            <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
              Sin riesgos abiertos con probabilidad e impacto.
            </p>
          )}
        </article>
        <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
          <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">Tendencias (12 semanas)</h2>
          {(trends?.series.length ?? 0) > 0 ? (
            <div className="space-y-3">
              {/* BUG-069: el avance ya se muestra como Gauge en "Indicadores";
                  aquí solo dejamos las series que NO se repiten en otra tarjeta. */}
              <ProgTrend label="Riesgos abiertos" trends={trends} metric="open_risks" color={PALETTE.warning} />
              <ProgTrend label="Riesgos severos" trends={trends} metric="severe_risks" color={PALETTE.danger} />
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
              Sin historia de snapshots todavía.
            </p>
          )}
        </article>
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <AlertTriangle className="h-4 w-4" aria-hidden /> Riesgos top del programa
        </div>
        {data.top_risks.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Sin riesgos críticos (severidad ≥ 13) abiertos.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="py-2">Folio</th>
                <th className="py-2">Riesgo</th>
                <th className="py-2">Proyecto</th>
                <th className="py-2">Estado</th>
                <th className="py-2 text-right">Severidad</th>
              </tr>
            </thead>
            <tbody>
              {data.top_risks.map((r) => (
                <tr key={r.id} className="border-t border-[var(--border-subtle)]">
                  <td className="py-2 font-mono text-xs">{r.folio ?? "—"}</td>
                  <td className="py-2">{r.title}</td>
                  <td className="py-2">
                    <Link
                      href={`/pmo/projects/${r.project_id}`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      {r.project_name ?? "—"}
                    </Link>
                  </td>
                  <td className="py-2">{r.status}</td>
                  <td className="py-2 text-right font-semibold tabular-nums">
                    {r.severity}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <FolderKanban className="h-4 w-4" aria-hidden /> Proyectos del programa
        </div>
        {data.projects.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Este programa aún no tiene proyectos.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="py-2">Folio</th>
                <th className="py-2">Nombre</th>
                <th className="py-2">Fase</th>
                <th className="py-2">Salud</th>
                <th className="py-2">PM</th>
                <th className="py-2 text-right">Avance</th>
                <th className="py-2 text-right">Plan / Real</th>
              </tr>
            </thead>
            <tbody>
              {data.projects.map((p) => (
                <tr key={p.id} className="border-t border-[var(--border-subtle)]">
                  <td className="py-2 font-mono text-xs">{p.folio ?? "—"}</td>
                  <td className="py-2">
                    <Link
                      href={`/pmo/projects/${p.id}`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      {p.name}
                    </Link>
                  </td>
                  <td className="py-2">{p.phase ?? "—"}</td>
                  <td className="py-2">{healthBadge(p.health_status)}</td>
                  <td className="py-2">{p.pm_name ?? "—"}</td>
                  <td className="py-2 text-right tabular-nums">{p.progress}%</td>
                  <td className="py-2 text-right tabular-nums text-xs">
                    {money(p.budget)} / {money(p.actual_budget)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
        </>
      )}
    </div>
  );
}
