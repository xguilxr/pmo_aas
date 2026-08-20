"use client";

// US-183 — Vista ejecutiva de capacidad/saturación de recursos.
// Cross-project: saturación individual + agregados por rol/área/equipo +
// conflictos de sobreasignación con recomendación de gobernanza.

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Gauge, KeyRound, Users } from "lucide-react";

import { healthTone } from "@/components/health-panel";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { SortableTh } from "@/components/ui/sortable-th";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { downloadGlobalOrganigrama } from "@/lib/api/analytics";
import {
  getCapacityConflicts,
  getCapacitySummary,
  type CapacityAreaAgg,
  type CapacityColor,
  type CapacityConflict,
  type CapacityDisciplineAgg,
  type CapacityResource,
  type CapacityTeamAgg,
  type CapacityWindow,
} from "@/lib/api/capacity";
import type { ProjectHealth } from "@/lib/api/projects";
import { cn } from "@/lib/cn";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";

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
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(resources);
  const [byDiscipline, setByDiscipline] = useState<CapacityDisciplineAgg[]>([]);
  const [byArea, setByArea] = useState<CapacityAreaAgg[]>([]);
  const [byTeam, setByTeam] = useState<CapacityTeamAgg[]>([]);
  const [conflicts, setConflicts] = useState<CapacityConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // US-187 — organigrama global con utilización (XLSX), scope tenant.
  const [downloadingOrganigrama, setDownloadingOrganigrama] = useState(false);
  const [organigramaError, setOrganigramaError] = useState<string | null>(null);

  async function handleDownloadOrganigrama() {
    setDownloadingOrganigrama(true);
    setOrganigramaError(null);
    try {
      await downloadGlobalOrganigrama();
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
    setError(null);
    Promise.all([getCapacitySummary({ window: win }), getCapacityConflicts({ window: win })])
      .then(([summary, conflictsRes]) => {
        if (cancelled) return;
        setResources(summary.resources);
        setByDiscipline(summary.by_discipline);
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
    <div className="space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <Gauge className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Recursos
          </h1>
          {leido && <MarcaDeDatos periodo="ventana" detalle={`ventana de ${win}`} actualizado={leido} />}
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Saturación de capacidad por persona, rol, área y equipo — y los
          conflictos de sobreasignación a resolver.
        </p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
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
        <Button
          variant="secondary"
          size="sm"
          onClick={handleDownloadOrganigrama}
          disabled={downloadingOrganigrama}
          title="Descarga el organigrama global con utilización (todo el tenant) en XLSX"
        >
          <Users className="mr-1 h-3.5 w-3.5" aria-hidden />
          {downloadingOrganigrama ? "Generando…" : "Organigrama global (XLSX)"}
        </Button>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {organigramaError ? <Banner variant="danger">{organigramaError}</Banner> : null}

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
          rows={byDiscipline}
          labelKey="discipline"
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
  // ENH-198: filtro por área y sub-área (equipo) sobre la lista de
  // personas — "ver por área (ej. IT, o sub-área IT Arquitectura)".
  const [areaFilter, setAreaFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");
  const areas = useMemo(
    () =>
      Array.from(
        new Set(resources.map((r) => r.area_name).filter(Boolean) as string[]),
      ).sort(),
    [resources],
  );
  const teams = useMemo(
    () =>
      Array.from(
        new Set(
          resources
            .filter((r) => !areaFilter || r.area_name === areaFilter)
            .map((r) => r.team_name)
            .filter(Boolean) as string[],
        ),
      ).sort(),
    [resources, areaFilter],
  );
  const filtered = useMemo(
    () =>
      resources.filter(
        (r) =>
          (!areaFilter || r.area_name === areaFilter) &&
          (!teamFilter || r.team_name === teamFilter),
      ),
    [resources, areaFilter, teamFilter],
  );
  const { sortedRows, ctrl } = useSortableRows<CapacityResource>(filtered);
  return (
    <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2 text-xs">
        <span className="font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
          Filtrar
        </span>
        <Select
          value={areaFilter}
          onChange={(e) => {
            setAreaFilter(e.target.value);
            setTeamFilter("");
          }}
          aria-label="Filtrar por área"
          className="h-7 w-auto text-xs"
        >
          <option value="">Todas las áreas</option>
          {areas.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </Select>
        <Select
          value={teamFilter}
          onChange={(e) => setTeamFilter(e.target.value)}
          aria-label="Filtrar por sub-área (equipo)"
          className="h-7 w-auto text-xs"
        >
          <option value="">Todas las sub-áreas</option>
          {teams.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        {areaFilter || teamFilter ? (
          <span className="text-[var(--color-tertiary)]">
            {filtered.length} de {resources.length} recursos
          </span>
        ) : null}
      </div>
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            <SortableTh<CapacityResource> sortKey="name" getter={(r) => r.name} ctrl={ctrl}>
              Nombre
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="function"
              getter={(r) => r.discipline ?? ""}
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
            {/* ENH-198: uso = FTE asignado / capacidad teórica. */}
            <SortableTh<CapacityResource>
              sortKey="usage"
              getter={(r) => r.usage_pct ?? -1}
              ctrl={ctrl}
              align="right"
            >
              % Uso
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
                {r.discipline ?? "—"}
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
              <td className="px-3 py-2 text-right">
                {r.usage_pct != null ? (
                  <span
                    className={cn(
                      "font-medium tabular-nums",
                      r.usage_pct > 100
                        ? "text-[var(--color-danger-fg)]"
                        : r.usage_pct >= 80
                          ? "text-[var(--color-warning-fg)]"
                          : "text-[var(--color-secondary)]",
                    )}
                  >
                    {r.usage_pct}%
                  </span>
                ) : (
                  <span className="text-[var(--color-tertiary)]">—</span>
                )}
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
              {c.discipline ? (
                <span className="text-xs text-[var(--color-tertiary)]">
                  · {c.discipline}
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
