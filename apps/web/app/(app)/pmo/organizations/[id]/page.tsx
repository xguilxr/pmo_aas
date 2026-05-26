"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Building2, FileText, FolderKanban, Network, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProgramModal } from "@/components/program-modal";
import { ScopedReportsPanel } from "@/components/reports/level2/ScopedReportsPanel";
import { Legend, PALETTE, Pie, RiskMatrix, TrendLines } from "@/components/dashboard-charts";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import {
  getRiskMatrix,
  getTrends,
  type RiskMatrixResponse,
  type TrendsResponse,
} from "@/lib/api/analytics";
import {
  getOrganizationPanel,
  type OrganizationPanelDetail,
  type OrgPanelProgram,
  type OrgPanelProject,
} from "@/lib/api/organizations";

type OrgTab = "overview" | "reports";

const HEALTH_LABEL: Record<string, string> = { green: "Verde", yellow: "Amarillo", red: "Rojo" };
const HEALTH_FILL: Record<string, string> = {
  green: PALETTE.success,
  yellow: PALETTE.warning,
  red: PALETTE.danger,
};

/**
 * US-068 — Página PMO de organización.
 *
 * Vista informativa del portafolio de una organización: panel de
 * programas (cards) + lista de proyectos. Separada de
 * `/admin/organizations/[id]` (gestión CRUD). El sidebar del PMO
 * lleva aquí al click en el panel de la organización.
 *
 * ENH-037 — botón "Nuevo Programa" con permission gate
 * (`programs:create`). Reutiliza `<ProgramModal>` con la organización
 * preseleccionada y deshabilitada (estamos en su contexto).
 */
export default function PmoOrganizationPage() {
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  // US-136: tabs "Resumen" | "Reportes" via ?tab=.
  const activeTab: OrgTab =
    search?.get("tab") === "reports" ? "reports" : "overview";
  const { canCreate, loading: permsLoading } = useMyPermissions();
  const [panel, setPanel] = useState<OrganizationPanelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [showProgramModal, setShowProgramModal] = useState(false);

  // US-156 — analítica org-scoped.
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrixResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRiskMatrix({ scope: "organization", id })
      .then((r) => !cancelled && setRiskMatrix(r))
      .catch(() => !cancelled && setRiskMatrix(null));
    getTrends({ scope: "organization", id, weeks: 12 })
      .then((r) => !cancelled && setTrends(r))
      .catch(() => !cancelled && setTrends(null));
    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  const healthData = useMemo(() => {
    const counts: Record<string, number> = { green: 0, yellow: 0, red: 0 };
    for (const pj of panel?.projects ?? []) {
      if (pj.health_status && pj.health_status in counts) counts[pj.health_status] += 1;
    }
    return (["green", "yellow", "red"] as const).map((k) => ({
      label: HEALTH_LABEL[k],
      value: counts[k],
      color: HEALTH_FILL[k],
    }));
  }, [panel]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getOrganizationPanel(id)
      .then((p) => {
        if (!cancelled) setPanel(p);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.status === 404
                ? "Esta organización no existe o no tienes permiso para verla."
                : err.message
              : "No se pudo cargar la organización",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  const projectCountByProgram = useMemo(() => {
    const map: Record<string, number> = {};
    if (!panel) return map;
    for (const pj of panel.projects) {
      const key = pj.program_id ?? "__sin_programa__";
      map[key] = (map[key] ?? 0) + 1;
    }
    return map;
  }, [panel]);

  const buCount = panel?.business_units.length ?? 0;
  const deptCount = useMemo(
    () =>
      panel?.business_units.reduce((acc, bu) => acc + bu.departments.length, 0) ??
      0,
    [panel],
  );
  const programsActive = useMemo(
    () => panel?.programs.filter((p) => p.is_active).length ?? 0,
    [panel],
  );
  const projectsActive = useMemo(
    () =>
      panel?.projects.filter((p) => p.phase !== "closed").length ?? 0,
    [panel],
  );

  const canCreateProgram = canCreate("programs");

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-6">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-6">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }
  if (!panel) return null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <nav className="text-[11px] text-[var(--text-tertiary)]">
        <Link href="/pmo" className="hover:underline">
          PMO
        </Link>
        <span className="mx-1">/</span>
        <span>{panel.name}</span>
      </nav>

      <header className="flex items-start gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
        <div className="flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
          {panel.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={panel.logo_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <Building2 className="h-6 w-6" aria-hidden />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">
            {panel.name}
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            {[panel.industry, panel.country].filter(Boolean).join(" · ") ||
              "Sin datos de industria"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowProgramModal(true)}
            disabled={!canCreateProgram || permsLoading}
            title={
              canCreateProgram
                ? undefined
                : "No tienes permiso para crear programas"
            }
          >
            <Plus className="mr-1 h-3.5 w-3.5" aria-hidden />
            Nuevo programa
          </Button>
          <Link
            href={`/admin/organizations/${panel.id}`}
            className="text-[12px] text-[var(--color-accent)] hover:underline"
          >
            Administrar →
          </Link>
        </div>
      </header>

      {/* US-136: tabs Resumen / Reportes */}
      <div
        role="tablist"
        aria-label="Vistas de la organización"
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
      >
        {(
          [
            { v: "overview" as const, label: "Resumen", icon: <Building2 className="h-3.5 w-3.5" aria-hidden /> },
            { v: "reports" as const, label: "Reportes", icon: <FileText className="h-3.5 w-3.5" aria-hidden /> },
          ]
        ).map((opt) => {
          const active = activeTab === opt.v;
          const href =
            opt.v === "overview"
              ? `/pmo/organizations/${id}`
              : `/pmo/organizations/${id}?tab=reports`;
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
            Plantillas Nivel 2 aplicadas con scope filtrado a esta organización.
          </p>
          <ScopedReportsPanel scope={{ kind: "organization", id }} />
        </section>
      ) : (
        <>
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Business Units" value={buCount} />
        <KpiCard label="Departamentos" value={deptCount} />
        <KpiCard
          label="Programas"
          value={programsActive}
          hint={`${panel.programs.length} total`}
        />
        <KpiCard
          label="Proyectos"
          value={projectsActive}
          hint={`${panel.projects.length} total`}
        />
      </section>

      <section aria-label="Analítica de la organización" className="grid gap-4 lg:grid-cols-3">
        <AnalyticsCard title="Salud de proyectos">
          <div className="flex items-center gap-4">
            <Pie data={healthData} ariaLabel="Salud de proyectos" size={140} />
            <div className="flex-1">
              <Legend data={healthData} />
            </div>
          </div>
        </AnalyticsCard>
        <AnalyticsCard title="Matriz de riesgos">
          {riskMatrix && riskMatrix.total > 0 ? (
            <RiskMatrix cells={riskMatrix.cells} ariaLabel="Matriz de riesgos de la organización" />
          ) : (
            <p className="py-8 text-center text-sm text-[var(--color-tertiary)]">
              Sin riesgos abiertos con probabilidad e impacto.
            </p>
          )}
        </AnalyticsCard>
        <AnalyticsCard title="Tendencias (12 semanas)">
          {(trends?.series.length ?? 0) > 0 ? (
            <div className="space-y-3">
              <OrgTrend label="Avance promedio" trends={trends} metric="avg_progress" color={PALETTE.success} fmt={(n) => `${Math.round(n)}%`} />
              <OrgTrend label="Riesgos abiertos" trends={trends} metric="open_risks" color={PALETTE.warning} />
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-[var(--color-tertiary)]">
              Sin historia de snapshots todavía.
            </p>
          )}
        </AnalyticsCard>
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Programas
          </h2>
          <Badge variant="neutral">{panel.programs.length}</Badge>
        </div>
        {panel.programs.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-tertiary)]">
            Esta organización no tiene programas registrados.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {panel.programs.map((program) => (
              <ProgramCard
                key={program.id}
                program={program}
                projectCount={
                  projectCountByProgram[program.id] ?? program.active_project_count
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <FolderKanban
            className="h-4 w-4 text-[var(--color-tertiary)]"
            aria-hidden
          />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Proyectos
          </h2>
          <Badge variant="neutral">{panel.projects.length}</Badge>
        </div>
        {panel.projects.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-tertiary)]">
            Sin proyectos registrados en esta organización.
          </div>
        ) : (
          <div className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <tr>
                  <th className="px-3 py-2 font-medium">Folio</th>
                  <th className="px-3 py-2 font-medium">Nombre</th>
                  <th className="px-3 py-2 font-medium">Programa</th>
                  <th className="px-3 py-2 font-medium">Fase</th>
                  <th className="px-3 py-2 font-medium">Salud</th>
                  <th className="px-3 py-2 font-medium">PM</th>
                </tr>
              </thead>
              <tbody>
                {panel.projects.map((pj) => {
                  const program = panel.programs.find(
                    (pg) => pg.id === pj.program_id,
                  );
                  return (
                    <ProjectRow key={pj.id} project={pj} programName={program?.name ?? "—"} />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
        </>
      )}

      <ProgramModal
        open={showProgramModal}
        onClose={() => setShowProgramModal(false)}
        onSaved={() => {
          setShowProgramModal(false);
          setReloadKey((k) => k + 1);
        }}
        initialOrgId={panel.id}
      />
    </div>
  );
}

function AnalyticsCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">{title}</h2>
      {children}
    </article>
  );
}

function OrgTrend({
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
  const data = (trends?.series ?? []).map((p) => ({ x: p.snapshot_date, y: Number(p[metric] ?? 0) }));
  const last = data.length ? data[data.length - 1].y : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-[var(--color-primary)]">{fmt ? fmt(last) : last}</span>
      </div>
      <TrendLines data={data} ariaLabel={`Tendencia de ${label}`} color={color} valueFormat={fmt} />
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
      <div className="text-xs text-[var(--color-tertiary)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-[var(--color-primary)]">
        {value}
      </div>
      {hint ? (
        <div className="mt-0.5 text-[11px] text-[var(--color-tertiary)]">
          {hint}
        </div>
      ) : null}
    </div>
  );
}

function ProgramCard({
  program,
  projectCount,
}: {
  program: OrgPanelProgram;
  projectCount: number;
}) {
  return (
    <Link
      href={`/pmo/programs/${program.id}`}
      className="flex flex-col gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)] transition hover:border-[var(--color-accent)] hover:shadow-[var(--shadow-md)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 truncate text-sm font-semibold text-[var(--color-primary)]">
          {program.name}
        </h3>
        {!program.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
      </div>
      {program.description ? (
        <p className="line-clamp-2 text-[12px] text-[var(--color-secondary)]">
          {program.description}
        </p>
      ) : null}
      <div className="flex gap-3 text-[11px] text-[var(--color-tertiary)]">
        <span>
          <strong className="text-[var(--color-secondary)]">{projectCount}</strong>{" "}
          proyectos
        </span>
      </div>
    </Link>
  );
}

function ProjectRow({
  project,
  programName,
}: {
  project: OrgPanelProject;
  programName: string;
}) {
  const healthColor =
    project.health_status === "green"
      ? "var(--color-success-fg)"
      : project.health_status === "yellow"
        ? "var(--color-warning-fg)"
        : project.health_status === "red"
          ? "var(--color-danger-fg)"
          : "var(--color-tertiary)";
  return (
    <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
      <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
        <Link
          href={`/pmo/projects/${project.id}`}
          className="hover:text-[var(--color-accent)] hover:underline"
        >
          {project.folio ?? "—"}
        </Link>
      </td>
      <td className="px-3 py-2">
        <Link
          href={`/pmo/projects/${project.id}`}
          className="text-[var(--color-primary)] hover:text-[var(--color-accent)] hover:underline"
        >
          {project.name}
        </Link>
      </td>
      <td className="px-3 py-2 text-[var(--color-secondary)]">{programName}</td>
      <td className="px-3 py-2 text-[var(--color-secondary)]">
        {project.phase ?? "—"}
      </td>
      <td className="px-3 py-2">
        <span
          className="inline-flex h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: healthColor }}
          aria-label={project.health_status ?? ""}
        />
      </td>
      <td className="px-3 py-2 text-[var(--color-secondary)]">
        {project.pm_name ?? "—"}
      </td>
    </tr>
  );
}
