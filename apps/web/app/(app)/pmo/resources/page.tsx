"use client";

// US-183 — Vista ejecutiva de capacidad/saturación de recursos.
// Cross-project: saturación individual + agregados por rol/área/equipo +
// conflictos de sobreasignación con recomendación de gobernanza.

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, Gauge, KeyRound } from "lucide-react";

import { healthTone } from "@/components/health-panel";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { SortableTh } from "@/components/ui/sortable-th";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getCapacityConflicts,
  getCapacitySummary,
  type CapacityAreaAgg,
  type CapacityColor,
  type CapacityConflict,
  type CapacityFunctionAgg,
  type CapacityResource,
  type CapacityTeamAgg,
  type CapacityWindow,
} from "@/lib/api/capacity";
import type { ProjectHealth } from "@/lib/api/projects";
import { cn } from "@/lib/cn";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";

const WINDOW_OPTIONS: { v: CapacityWindow; label: string }[] = [
  { v: "today", label: "Hoy" },
  { v: "week", label: "Semana" },
  { v: "3weeks", label: "3 semanas" },
  { v: "month", label: "Mes" },
];

type Tab = "people" | "roles" | "areas" | "conflicts";

const TABS: { v: Tab; label: string }[] = [
  { v: "people", label: "Personas" },
  { v: "roles", label: "Roles" },
  { v: "areas", label: "Áreas y Equipos" },
  { v: "conflicts", label: "Conflictos" },
];

function fmtPct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${Number.isInteger(n) ? n : n.toFixed(1)}%`;
}

function GapDot({ color }: { color: CapacityColor }) {
  return (
    <span
      className={cn("h-2 w-2 shrink-0 rounded-full", healthTone(color))}
      aria-hidden
    />
  );
}

function EmptyState() {
  return (
    <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--color-tertiary)]">
      Aún no hay asignaciones con FTE%. Captura allocation en el directorio
      del proyecto.
    </div>
  );
}

export default function ResourcesPage() {
  const [win, setWin] = useState<CapacityWindow>("week");
  const [tab, setTab] = useState<Tab>("people");
  const [resources, setResources] = useState<CapacityResource[]>([]);
  const [byFunction, setByFunction] = useState<CapacityFunctionAgg[]>([]);
  const [byArea, setByArea] = useState<CapacityAreaAgg[]>([]);
  const [byTeam, setByTeam] = useState<CapacityTeamAgg[]>([]);
  const [conflicts, setConflicts] = useState<CapacityConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getCapacitySummary({ window: win }), getCapacityConflicts({ window: win })])
      .then(([summary, conflictsRes]) => {
        if (cancelled) return;
        setResources(summary.resources);
        setByFunction(summary.by_function);
        setByArea(summary.by_area);
        setByTeam(summary.by_team);
        setConflicts(conflictsRes.conflicts);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.message
            : "No se pudo cargar la capacidad de recursos",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [win]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <Gauge className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Recursos
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Saturación de capacidad por persona, rol, área y equipo — y los
          conflictos de sobreasignación a resolver.
        </p>
      </header>

      <div
        role="tablist"
        aria-label="Ventana de tiempo"
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
      >
        {WINDOW_OPTIONS.map((opt) => {
          const active = win === opt.v;
          return (
            <button
              key={opt.v}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setWin(opt.v)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] px-4 py-1.5 text-xs font-medium transition-colors",
                active
                  ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <div
        role="tablist"
        aria-label="Secciones de recursos"
        className="flex flex-wrap gap-1 border-b border-[var(--border-default)]"
      >
        {TABS.map((opt) => {
          const active = tab === opt.v;
          return (
            <button
              key={opt.v}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setTab(opt.v)}
              className={cn(
                "inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
              )}
            >
              {opt.label}
              {opt.v === "conflicts" && conflicts.length > 0 ? (
                <Badge variant="danger">{conflicts.length}</Badge>
              ) : null}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : resources.length === 0 ? (
        <EmptyState />
      ) : tab === "people" ? (
        <PeopleTable resources={resources} />
      ) : tab === "roles" ? (
        <AggTable
          rows={byFunction}
          labelKey="portfolio_function"
          labelHeader="Función"
        />
      ) : tab === "areas" ? (
        <div className="space-y-5">
          <section className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
              Áreas
            </h2>
            <AggTable rows={byArea} labelKey="name" labelHeader="Área" />
          </section>
          <section className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
              Equipos
            </h2>
            <AggTable rows={byTeam} labelKey="name" labelHeader="Equipo" />
          </section>
        </div>
      ) : (
        <ConflictsView conflicts={conflicts} />
      )}
    </div>
  );
}

function PeopleTable({ resources }: { resources: CapacityResource[] }) {
  const { sortedRows, ctrl } = useSortableRows<CapacityResource>(resources);
  return (
    <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            <SortableTh<CapacityResource> sortKey="name" getter={(r) => r.name} ctrl={ctrl}>
              Nombre
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="function"
              getter={(r) => r.portfolio_function ?? ""}
              ctrl={ctrl}
            >
              Función
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="type"
              getter={(r) => r.resource_type ?? ""}
              ctrl={ctrl}
            >
              Tipo
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="capacity"
              getter={(r) => r.capacity_pct}
              ctrl={ctrl}
              align="right"
            >
              Capacidad %
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="demand"
              getter={(r) => r.demand_pct}
              ctrl={ctrl}
              align="right"
            >
              Demanda %
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="tentative"
              getter={(r) => r.tentative_pct}
              ctrl={ctrl}
              align="right"
            >
              Tentativa %
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="gap"
              getter={(r) => r.gap_pct}
              ctrl={ctrl}
              align="right"
            >
              Gap
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="projects"
              getter={(r) => r.projects_count}
              ctrl={ctrl}
              align="right"
            >
              Proyectos
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="unquantified"
              getter={(r) => r.unquantified_count}
              ctrl={ctrl}
              align="right"
            >
              Sin FTE
            </SortableTh>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((r) => (
            <tr
              key={r.actor_id}
              className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
            >
              <td className="px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-[var(--color-primary)]">
                    {r.name}
                  </span>
                  {r.is_key_resource ? (
                    <KeyRound
                      className="h-3.5 w-3.5 text-[var(--color-warning-fg)]"
                      aria-label="Recurso clave"
                    />
                  ) : null}
                </div>
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {r.portfolio_function ?? "—"}
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {r.resource_type ?? "—"}
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {fmtPct(r.capacity_pct)}
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {fmtPct(r.demand_pct)}
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {fmtPct(r.tentative_pct)}
              </td>
              <td className="px-3 py-2 text-right">
                <span className="inline-flex items-center justify-end gap-1.5">
                  <GapDot color={r.color} />
                  <span>{r.gap_pct > 0 ? `+${fmtPct(r.gap_pct)}` : fmtPct(r.gap_pct)}</span>
                </span>
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {r.projects_count}
              </td>
              <td className="px-3 py-2 text-right">
                {r.unquantified_count > 0 ? (
                  <Badge variant="warning">{r.unquantified_count}</Badge>
                ) : (
                  <span className="text-[var(--color-tertiary)]">0</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type AggRow = {
  capacity_pct: number;
  demand_pct: number;
  gap_pct: number;
  resources: number;
  overloaded: number;
  color: CapacityColor;
  [key: string]: unknown;
};

function AggTable<T extends AggRow>({
  rows,
  labelKey,
  labelHeader,
}: {
  rows: T[];
  labelKey: keyof T;
  labelHeader: string;
}) {
  const { sortedRows, ctrl } = useSortableRows<T>(rows);
  if (rows.length === 0) {
    return (
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-8 text-center text-sm text-[var(--color-tertiary)]">
        Sin datos para esta agrupación en la ventana seleccionada.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            <SortableTh<T> sortKey="label" getter={(r) => String(r[labelKey] ?? "")} ctrl={ctrl}>
              {labelHeader}
            </SortableTh>
            <SortableTh<T> sortKey="resources" getter={(r) => r.resources} ctrl={ctrl} align="right">
              Recursos
            </SortableTh>
            <SortableTh<T> sortKey="capacity" getter={(r) => r.capacity_pct} ctrl={ctrl} align="right">
              Capacidad %
            </SortableTh>
            <SortableTh<T> sortKey="demand" getter={(r) => r.demand_pct} ctrl={ctrl} align="right">
              Demanda %
            </SortableTh>
            <SortableTh<T> sortKey="gap" getter={(r) => r.gap_pct} ctrl={ctrl} align="right">
              Gap
            </SortableTh>
            <SortableTh<T> sortKey="overloaded" getter={(r) => r.overloaded} ctrl={ctrl} align="right">
              Sobrecargados
            </SortableTh>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((r, i) => (
            <tr
              key={`${String(r[labelKey])}-${i}`}
              className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
            >
              <td className="px-3 py-2 font-medium text-[var(--color-primary)]">
                {String(r[labelKey] ?? "—")}
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {r.resources}
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {fmtPct(r.capacity_pct)}
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {fmtPct(r.demand_pct)}
              </td>
              <td className="px-3 py-2 text-right">
                <span className="inline-flex items-center justify-end gap-1.5">
                  <GapDot color={r.color} />
                  <span>{r.gap_pct > 0 ? `+${fmtPct(r.gap_pct)}` : fmtPct(r.gap_pct)}</span>
                </span>
              </td>
              <td className="px-3 py-2 text-right text-[var(--color-secondary)]">
                {r.overloaded}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConflictsView({ conflicts }: { conflicts: CapacityConflict[] }) {
  if (conflicts.length === 0) {
    return (
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--color-tertiary)]">
        Sin conflictos de sobreasignación en la ventana seleccionada.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {conflicts.map((c) => (
        <article
          key={c.actor_id}
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <GapDot color={c.color} />
              <span className="text-base font-semibold text-[var(--color-primary)]">
                {c.name}
              </span>
              {c.is_key_resource ? (
                <KeyRound
                  className="h-3.5 w-3.5 text-[var(--color-warning-fg)]"
                  aria-label="Recurso clave"
                />
              ) : null}
              {c.portfolio_function ? (
                <span className="text-xs text-[var(--color-tertiary)]">
                  · {c.portfolio_function}
                </span>
              ) : null}
            </div>
            <div className="text-sm text-[var(--color-secondary)]">
              Demanda{" "}
              <span className="font-semibold text-[var(--color-danger-fg)]">
                {fmtPct(c.demand_pct)}
              </span>{" "}
              vs capacidad {fmtPct(c.capacity_pct)} (
              <span className="font-medium">+{fmtPct(c.over_pct)}</span> sobre
              capacidad)
            </div>
          </div>

          <ul className="mt-3 divide-y divide-[var(--border-subtle)]">
            {c.projects.map((p) => (
              <li
                key={p.project_id}
                className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2 w-2 shrink-0 rounded-full",
                      healthTone(p.health as ProjectHealth | null),
                    )}
                    aria-hidden
                  />
                  <Link
                    href={`/pmo/projects/${p.project_id}`}
                    className="text-[var(--color-accent)] hover:underline"
                  >
                    <span className="font-mono text-xs">{p.folio}</span>{" "}
                    <span className="text-[var(--color-primary)]">{p.name}</span>
                  </Link>
                  {p.is_critical ? <Badge variant="danger">Crítico</Badge> : null}
                </div>
                <span className="font-medium text-[var(--color-secondary)]">
                  {p.allocation_pct !== null ? fmtPct(p.allocation_pct) : "Sin FTE%"}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-3 flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] px-3 py-2 text-sm text-[var(--color-warning-fg)]">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{c.recommendation}</span>
          </div>
        </article>
      ))}
    </div>
  );
}
