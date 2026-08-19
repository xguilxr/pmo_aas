"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Download, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Heatmap, TrendLines, Treemap } from "@/components/dashboard-charts";
import { HealthDimensionMatrix } from "@/components/health-panel";
import { HealthEvaluationModal } from "@/components/health-evaluation-modal";
import { ProgramModal } from "@/components/program-modal";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import { aplicarFuente, XLSX_FONT } from "@/lib/plan-template";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { useMonedaPreferida } from "@/lib/moneda-tenant";
import {
  downloadPortfolioStatusReport,
  getHealthMatrix,
  getHeatmap,
  getTrends,
  getTreemap,
  type HealthMatrixResponse,
  type HeatmapResponse,
  type TreemapResponse,
  type TrendsResponse,
} from "@/lib/api/analytics";
import {
  listOrganizationPanels,
  type OrganizationPanel,
} from "@/lib/api/organizations";

function PortfolioPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">{title}</h2>
      {children}
    </article>
  );
}

function metricSeries(trends: TrendsResponse | null, metric: string) {
  return (trends?.series ?? []).map((p) => ({
    x: p.snapshot_date,
    y: Number(p[metric] ?? 0),
  }));
}

function MiniTrend({
  label,
  data,
  color,
  fmt,
}: {
  label: string;
  data: { x: string; y: number }[];
  color: string;
  fmt?: (n: number) => string;
}) {
  const last = data.length ? data[data.length - 1].y : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
          {label}
        </span>
        <span className="text-sm font-semibold tabular-nums text-[var(--color-primary)]">
          {fmt ? fmt(last) : last}
        </span>
      </div>
      <TrendLines data={data} ariaLabel={`Tendencia de ${label}`} color={color} valueFormat={fmt} />
    </div>
  );
}

/**
 * US-068 — Landing PMO.
 *
 * Vista informativa de los paneles de las organizaciones del tenant.
 * Click en un panel → `/pmo/organizations/[id]` (programas + proyectos).
 * Es el contraparte "info" del `/admin/organizations` (gestión CRUD).
 */
export default function PmoHome() {
  // BUG-092 — el treemap agrega cartera: la moneda es la del inquilino.
  const monedaDeCartera = useMonedaPreferida();
  const router = useRouter();
  const [panels, setPanels] = useState<OrganizationPanel[]>([]);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(panels);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // US-155 — analítica de portafolio (admin-equivalente; detección por capacidad).
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [treemap, setTreemap] = useState<TreemapResponse | null>(null);
  // US-181: matriz Proyecto × Dimensión de salud.
  const [healthMatrix, setHealthMatrix] = useState<HealthMatrixResponse | null>(null);
  // US-192: evaluación 5+1 desde el portafolio (sin abrir el proyecto).
  const [evalTarget, setEvalTarget] = useState<{ id: string; name: string } | null>(null);
  const [healthReportBusy, setHealthReportBusy] = useState(false);

  async function downloadHealthReport() {
    if (healthReportBusy || !healthMatrix) return;
    setHealthReportBusy(true);
    try {
      const [{ getPortfolioHealthEvaluations }, ExcelJS] = await Promise.all([
        import("@/lib/api/analytics"),
        import("exceljs").then((m) => m.default),
      ]);
      const evals = await getPortfolioHealthEvaluations().catch(() => ({ rows: [] }));
      const nameById = new Map(
        healthMatrix.rows.map((r) => [r.project_id, `${r.folio} · ${r.name}`]),
      );
      const wb = new ExcelJS.Workbook();
      wb.creator = "PMO aaS";
      const RAG = (v: string | null | undefined) =>
        v === "green" ? "Verde" : v === "yellow" ? "Amarillo" : v === "red" ? "Rojo" : "—";
      const ws = wb.addWorksheet("Salud del portafolio");
      ws.columns = [
        { header: "Proyecto", key: "p", width: 44 },
        { header: "Organización", key: "o", width: 22 },
        { header: "Salud", key: "h", width: 10 },
        { header: "Fuente", key: "src", width: 12 },
        { header: "Cronograma", key: "schedule", width: 12 },
        { header: "Presupuesto", key: "budget", width: 12 },
        { header: "Riesgos", key: "risks", width: 12 },
        { header: "Decisiones", key: "decisions", width: 12 },
        { header: "Recursos", key: "resources", width: 12 },
      ];
      ws.getRow(1).font = { name: XLSX_FONT, bold: true };
      for (const r of healthMatrix.rows) {
        ws.addRow({
          p: `${r.folio} · ${r.name}`,
          o: r.organization_name ?? "",
          h: RAG(r.health_status),
          src: r.health_source === "manual" ? "PM" : "Auto",
          schedule: RAG(r.dims["schedule"]),
          budget: RAG(r.dims["budget"]),
          risks: RAG(r.dims["risks"]),
          decisions: RAG(r.dims["decisions"]),
          resources: RAG(r.dims["resources"]),
        });
      }
      const wh = wb.addWorksheet("Historial de evaluaciones");
      wh.columns = [
        { header: "Proyecto", key: "p", width: 44 },
        { header: "Fecha", key: "d", width: 12 },
        { header: "Global", key: "g", width: 10 },
        { header: "Cronograma", key: "schedule", width: 12 },
        { header: "Presupuesto", key: "budget", width: 12 },
        { header: "Riesgos", key: "risks", width: 12 },
        { header: "Decisiones", key: "decisions", width: 12 },
        { header: "Recursos", key: "resources", width: 12 },
        { header: "Nota", key: "n", width: 60 },
      ];
      wh.getRow(1).font = { name: XLSX_FONT, bold: true };
      for (const e of evals.rows) {
        wh.addRow({
          p: nameById.get(e.project_id) ?? e.project_id,
          d: e.evaluated_at,
          g: RAG(e.overall),
          schedule: RAG(e.schedule),
          budget: RAG(e.budget),
          risks: RAG(e.risks),
          decisions: RAG(e.decisions),
          resources: RAG(e.resources),
          n: e.note ?? "",
        });
      }
      // ENH-202: las filas de datos no llevan `font` propia y saldrían en
      // Calibri; el barrido las deja en Helvetica como las cabeceras.
      aplicarFuente(ws);
      aplicarFuente(wh);
      const buf = await wb.xlsx.writeBuffer();
      const url = URL.createObjectURL(
        new Blob([buf], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "reporte-salud-portafolio.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      alert("No se pudo generar el reporte de salud");
    } finally {
      setHealthReportBusy(false);
    }
  }
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [isAdminView, setIsAdminView] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  // ENH-142: creación directa de org / programa / proyecto desde el portafolio.
  const { canCreate, loading: permsLoading } = useMyPermissions();
  const [showProgramModal, setShowProgramModal] = useState(false);
  // ENH-190: label configurable por tenant para "Organización(es)".

  async function handleDownloadReport() {
    setDownloading(true);
    setReportError(null);
    try {
      await downloadPortfolioStatusReport();
    } catch (err) {
      setReportError(err instanceof Error ? err.message : "No se pudo generar el reporte");
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listOrganizationPanels({ is_active: true })
      .then((r) => {
        if (!cancelled) setPanels(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudieron cargar las organizaciones",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
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
    getTreemap({ scope: "tenant" })
      .then((r) => !cancelled && setTreemap(r))
      .catch(() => !cancelled && setTreemap(null));
    getHealthMatrix()
      .then((r) => !cancelled && setHealthMatrix(r))
      .catch(() => !cancelled && setHealthMatrix(null));
    getTrends({ scope: "tenant", weeks: 12 })
      .then((r) => !cancelled && setTrends(r))
      .catch(() => !cancelled && setTrends(null));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            PMO
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Vista informativa del portafolio. Selecciona una organización para
            ver sus programas y proyectos. La gestión (CRUD) vive en{" "}
            <Link href="/admin/organizations" className="text-[var(--color-accent)] hover:underline">
              Admin → Organizaciones
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canCreate("organizations") ? (
            <Link href="/admin/organizations/new">
              <Button variant="secondary" size="sm">
                <Plus className="mr-1 h-3.5 w-3.5" aria-hidden />
                Nueva organización
              </Button>
            </Link>
          ) : null}
          {canCreate("programs") ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowProgramModal(true)}
              disabled={permsLoading}
            >
              <Plus className="mr-1 h-3.5 w-3.5" aria-hidden />
              Nuevo programa
            </Button>
          ) : null}
          {canCreate("projects") ? (
            <Link href="/pmo/projects/new">
              <Button variant="primary" size="sm">
                <Plus className="mr-1 h-3.5 w-3.5" aria-hidden />
                Nuevo proyecto
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      <ProgramModal
        open={showProgramModal}
        onClose={() => setShowProgramModal(false)}
        onSaved={() => {
          setShowProgramModal(false);
          router.refresh();
        }}
      />

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {reportError ? <Banner variant="danger">{reportError}</Banner> : null}

      {isAdminView ? (
        <section aria-label="Analítica de portafolio" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[var(--color-primary)]">
              Analítica del portafolio
            </h2>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleDownloadReport}
              disabled={downloading}
            >
              <Download className="mr-1 h-3.5 w-3.5" aria-hidden />
              {downloading ? "Generando…" : "Descargar status PMO (PDF)"}
            </Button>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <PortfolioPanel title="Salud por organización">
              <Heatmap
                rows={heatmap?.rows ?? []}
                ariaLabel="Mapa de calor de salud por organización"
                onCellClick={(orgId) => router.push(`/pmo/organizations/${orgId}`)}
              />
            </PortfolioPanel>
            <PortfolioPanel title="Portafolio (presupuesto × salud)">
              <Treemap tree={treemap?.tree ?? []} ariaLabel="Treemap del portafolio" moneda={monedaDeCartera} />
            </PortfolioPanel>
          </div>
          <PortfolioPanel title="Salud por dimensión (proyectos activos)">
            {/* US-192: reporte de salud del portafolio + evaluación 5+1
                por proyecto sin abrir cada uno. */}
            <div className="mb-2 flex justify-end">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={downloadHealthReport}
                disabled={healthReportBusy || !healthMatrix}
              >
                <Download className="mr-1 h-3.5 w-3.5" aria-hidden />
                {healthReportBusy ? "Generando…" : "Reporte de salud (XLSX)"}
              </Button>
            </div>
            <HealthDimensionMatrix
              rows={healthMatrix?.rows ?? []}
              onRowClick={(pid) => router.push(`/pmo/projects/${pid}`)}
              onEvaluate={(pid, name) => setEvalTarget({ id: pid, name })}
            />
          </PortfolioPanel>

          {evalTarget ? (
            <HealthEvaluationModal
              projectId={evalTarget.id}
              projectName={evalTarget.name}
              open
              onClose={() => setEvalTarget(null)}
              onSaved={() => {
                getHealthMatrix()
                  .then((r) => setHealthMatrix(r))
                  .catch(() => {});
              }}
            />
          ) : null}
          <PortfolioPanel title="Tendencias del tenant (12 semanas)">
            {(trends?.series.length ?? 0) > 0 ? (
              <div className="grid gap-4 sm:grid-cols-3">
                <MiniTrend
                  label="Avance promedio"
                  data={metricSeries(trends, "avg_progress")}
                  color="var(--color-success-fg)"
                  fmt={(n) => `${Math.round(n)}%`}
                />
                <MiniTrend
                  label="Riesgos abiertos"
                  data={metricSeries(trends, "open_risks")}
                  color="var(--color-warning-fg)"
                />
                <MiniTrend
                  label="Proyectos activos"
                  data={metricSeries(trends, "projects_active")}
                  color="var(--color-accent)"
                />
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
                Aún no hay historia de snapshots. Captura el primer punto desde el{" "}
                <Link href="/dashboard" className="text-[var(--color-accent)] hover:underline">
                  tablero
                </Link>
                .
              </p>
            )}
          </PortfolioPanel>
        </section>
      ) : null}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-[var(--radius-xl)]" />
          ))}
        </div>
      ) : panels.length === 0 ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
          No hay organizaciones activas. Pide a un admin que cree una en{" "}
          <Link
            href="/admin/organizations"
            className="text-[var(--color-accent)] hover:underline"
          >
            Admin → Organizaciones
          </Link>
          .
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {panels.map((p) => (
            <Link
              key={p.id}
              href={`/pmo/organizations/${p.id}`}
              className="group flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--color-accent)]"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                  {p.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.logo_url} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <Building2 className="h-5 w-5" aria-hidden />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-[var(--color-primary)] group-hover:text-[var(--color-accent)]">
                      {p.name}
                    </span>
                  </div>
                  <div className="truncate text-xs text-[var(--color-tertiary)]">
                    {[p.industry, p.country].filter(Boolean).join(" · ") ||
                      "Sin datos de industria"}
                  </div>
                </div>
              </div>
              <div className="flex gap-3 text-[11px]">
                <Badge variant="neutral">
                  {p.program_count} programas
                </Badge>
                <Badge variant="neutral">
                  {p.active_project_count} proyectos activos
                </Badge>
              </div>
              <div className="flex gap-3 text-[11px] text-[var(--color-tertiary)]">
                <span>🟢 {p.portfolio_health.green}</span>
                <span>🟡 {p.portfolio_health.yellow}</span>
                <span>🔴 {p.portfolio_health.red}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
