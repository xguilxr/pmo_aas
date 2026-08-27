"use client";

/**
 * Recursos — Catálogo y Capacidad.
 *
 * US-183 dejó aquí cuatro secciones planas: personas, roles, áreas/equipos y
 * conflictos. US-208 las mete todas bajo **Catálogo** y añade **Capacidad**, que
 * es lo que los mockups aprobados pedían y no existía: el heatmap de carga por
 * persona y semana, capacidad contra demanda, quién es cuello de botella y qué
 * hacer con eso.
 *
 * El corte entre las dos pestañas es de tiempo verbal. El catálogo contesta
 * «¿quién hay y cómo está **hoy**?» —una ventana, un número por recurso—. La
 * capacidad contesta «¿qué va a pasar?» —doce semanas, un número por recurso y
 * semana—. Son la misma tabla leída con dos preguntas distintas, y mezclarlas
 * en una lista de secciones planas era lo que hacía que ninguna de las dos se
 * leyera bien.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { healthTone } from "@/components/health-panel";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { SortableTh } from "@/components/ui/sortable-th";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { downloadGlobalOrganigrama } from "@/lib/api/analytics";
import { CapacidadSemanal } from "@/components/capacidad-semanal";
import { useOrgFiltro } from "@/components/organizacion-activa";
import {
  getCapacityConflicts,
  getCapacitySummary,
  getCargaSemanal,
  type CargaSemanalResponse,
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

/** Las dos pestañas del mockup. */
type Pestana = "catalogo" | "capacidad";

const PESTANAS: { v: Pestana; label: string }[] = [
  { v: "catalogo", label: "Catálogo" },
  { v: "capacidad", label: "Capacidad" },
];

/** Las secciones de dentro del catálogo — las cuatro de US-183. */
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
    <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--text-tertiary)]">
      Aún no hay asignaciones con FTE%. Captura allocation en el directorio
      del proyecto.
    </div>
  );
}

export default function ResourcesPage() {
  // US-205 — la organización sale del header. El catálogo es por organización
  // (lo dice el mockup: «catálogo por organización»); la carga de una persona
  // suma todos sus proyectos, y eso lo resuelve el servidor.
  const orgFiltro = useOrgFiltro();
  const [pestana, setPestana] = useState<Pestana>("catalogo");
  const [win, setWin] = useState<CapacityWindow>("week");
  const [tab, setTab] = useState<Tab>("people");
  const [semanas, setSemanas] = useState(12);
  const [carga, setCarga] = useState<CargaSemanalResponse | null>(null);
  const [cargandoCarga, setCargandoCarga] = useState(true);
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
    Promise.all([
      getCapacitySummary({ window: win, organization_id: orgFiltro }),
      getCapacityConflicts({ window: win, organization_id: orgFiltro }),
    ])
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
  }, [win, orgFiltro]);

  // La carga semanal se pide aparte y solo cuando su pestaña está a la vista:
  // es la respuesta más pesada de la pantalla —una serie por recurso— y traerla
  // para el catálogo sería pagarla sin mirarla.
  useEffect(() => {
    if (pestana !== "capacidad") return;
    let cancelled = false;
    setCargandoCarga(true);
    getCargaSemanal({ weeks: semanas, organization_id: orgFiltro })
      .then((r) => !cancelled && setCarga(r))
      .catch(() => !cancelled && setCarga(null))
      .finally(() => {
        if (!cancelled) setCargandoCarga(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pestana, semanas, orgFiltro]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
              Recursos
            </h1>
            {leido && <MarcaDeDatos periodo="ventana" detalle={`ventana de ${win}`} actualizado={leido} />}
          </div>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            {pestana === "catalogo"
              ? "Quién hay y cómo está su carga hoy: por persona, rol, área y equipo, con los conflictos de sobreasignación a resolver."
              : "Qué va a pasar: carga por persona y semana, capacidad contra demanda y quién es el cuello de botella."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Las dos pestañas del mockup. El corte es de tiempo verbal: el
              catálogo es «hoy», la capacidad es «las próximas doce semanas». */}
          <div
            role="tablist"
            aria-label="Vistas de recursos"
            className="inline-flex h-8 items-center gap-0.5 rounded-[9px] border border-[var(--border-default)] bg-[var(--color-subtle)] p-0.75 shadow-[var(--hundido)]"
          >
            {PESTANAS.map((opt) => {
              const activa = pestana === opt.v;
              return (
                <button
                  key={opt.v}
                  type="button"
                  role="tab"
                  aria-selected={activa}
                  onClick={() => setPestana(opt.v)}
                  className={cn(
                    "inline-flex h-6.5 items-center justify-center rounded-[7px] px-3.5 text-[12.5px] font-medium transition-colors",
                    activa
                      ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                      : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>

          {pestana === "catalogo" ? (
            <div
              role="tablist"
              aria-label="Ventana de tiempo"
              className="inline-flex h-8 items-center gap-0.5 rounded-[9px] border border-[var(--border-default)] bg-[var(--color-subtle)] p-0.75 shadow-[var(--hundido)]"
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
                      "inline-flex h-6.5 items-center justify-center rounded-[7px] px-2.5 text-xs font-medium transition-colors",
                      active
                        ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--relieve-control)]"
                        : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
                    )}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>

      {pestana === "capacidad" ? (
        <CapacidadSemanal
          datos={carga}
          cargando={cargandoCarga}
          semanas={semanas}
          onSemanas={setSemanas}
        />
      ) : (
      <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleDownloadOrganigrama}
          disabled={downloadingOrganigrama}
          title="Descarga el organigrama global con utilización (todo el tenant) en XLSX"
        >
          <Icono nombre="download" size={15} />
          {downloadingOrganigrama ? "Generando…" : "Organigrama global (XLSX)"}
        </Button>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {organigramaError ? <Banner variant="danger">{organigramaError}</Banner> : null}

      <div
        role="tablist"
        aria-label="Secciones de recursos"
        className="flex items-center gap-1 border-b border-[var(--border-default)] shadow-[var(--linea-surco)]"
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
                "inline-flex h-9 items-center gap-1.5 border-b-2 px-2.5 text-[13px] transition-colors",
                active
                  ? "border-[var(--text-primary)] font-semibold text-[var(--text-primary)]"
                  : "border-transparent font-medium text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              {opt.label}
              {opt.v === "conflicts" && conflicts.length > 0 ? (
                <Badge variant="neutral">{conflicts.length}</Badge>
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
            <h2 className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Áreas
            </h2>
            <AggTable rows={byArea} labelKey="name" labelHeader="Área" />
          </section>
          <section className="space-y-2">
            <h2 className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Equipos
            </h2>
            <AggTable rows={byTeam} labelKey="name" labelHeader="Equipo" />
          </section>
        </div>
      ) : (
        <ConflictsView conflicts={conflicts} />
      )}
      </div>
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
    <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2 shadow-[var(--linea-surco)]">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
          Filtrar
        </span>
        <Select
          value={areaFilter}
          onChange={(e) => {
            setAreaFilter(e.target.value);
            setTeamFilter("");
          }}
          aria-label="Filtrar por área"
          className="h-7 w-[150px] text-[12.5px]"
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
          className="h-7 w-[160px] text-[12.5px]"
        >
          <option value="">Todas las sub-áreas</option>
          {teams.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        {areaFilter || teamFilter ? (
          <span className="text-[11px] text-[var(--text-tertiary)]">
            {filtered.length} de {resources.length} recursos
          </span>
        ) : null}
      </div>
      <table className="w-full table-fixed text-sm">
        <colgroup>
          <col />
          <col style={{ width: 132 }} />
          <col style={{ width: 104 }} />
          <col style={{ width: 96 }} />
          <col style={{ width: 96 }} />
          <col style={{ width: 84 }} />
          <col style={{ width: 100 }} />
          <col style={{ width: 104 }} />
          <col style={{ width: 90 }} />
          <col style={{ width: 84 }} />
        </colgroup>
        <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
          <tr>
            <SortableTh<CapacityResource> sortKey="name" getter={(r) => r.name} ctrl={ctrl} className="h-8.5">
              Nombre
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="function"
              getter={(r) => r.discipline ?? ""}
              ctrl={ctrl}
              className="h-8.5"
            >
              Función
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="type"
              getter={(r) => r.resource_type ?? ""}
              ctrl={ctrl}
              className="h-8.5"
            >
              Tipo
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="capacity"
              getter={(r) => r.capacity_pct}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              Capacidad
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="demand"
              getter={(r) => r.demand_pct}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              Demanda
            </SortableTh>
            {/* ENH-198: uso = FTE asignado / capacidad teórica. */}
            <SortableTh<CapacityResource>
              sortKey="usage"
              getter={(r) => r.usage_pct ?? -1}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              % Uso
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="tentative"
              getter={(r) => r.tentative_pct}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              Tentativa
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="gap"
              getter={(r) => r.gap_pct}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              Gap
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="projects"
              getter={(r) => r.projects_count}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              Proyectos
            </SortableTh>
            <SortableTh<CapacityResource>
              sortKey="unquantified"
              getter={(r) => r.unquantified_count}
              ctrl={ctrl}
              align="right"
              className="h-8.5 pr-3.5"
            >
              Sin FTE
            </SortableTh>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((r) => (
            <tr
              key={r.actor_id}
              className="h-10.5 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] even:bg-[var(--color-subtle)] hover:bg-[var(--color-subtle)]"
            >
              <td className="px-3">
                <div className="flex min-w-0 items-center gap-1.5">
                  <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)]">
                    {r.name}
                  </span>
                  {r.is_key_resource ? (
                    <span className="shrink-0" role="img" aria-label="Recurso clave">
                      <Icono nombre="lock" size={13} className="text-[var(--color-warning-fg)]" />
                    </span>
                  ) : null}
                </div>
              </td>
              <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[var(--text-secondary)]">
                {r.discipline ?? "—"}
              </td>
              <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[var(--text-secondary)]">
                {r.resource_type ?? "—"}
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {fmtPct(r.capacity_pct)}
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {fmtPct(r.demand_pct)}
              </td>
              <td className="pr-3.5 text-right">
                {r.usage_pct != null ? (
                  <span
                    className={cn(
                      "font-mono text-[12.5px] tabular-nums",
                      r.usage_pct > 100
                        ? "font-semibold text-[var(--color-danger-fg)]"
                        : r.usage_pct >= 80
                          ? "font-semibold text-[var(--color-warning-fg)]"
                          : "text-[var(--text-secondary)]",
                    )}
                  >
                    {r.usage_pct}%
                  </span>
                ) : (
                  <span className="font-mono text-[12.5px] text-[var(--text-faint)]">—</span>
                )}
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {fmtPct(r.tentative_pct)}
              </td>
              <td className="pr-3.5 text-right">
                <span className="inline-flex items-center justify-end gap-1.75">
                  <GapDot color={r.color} />
                  <span className="font-mono text-[12.5px] text-[var(--text-primary)]">
                    {r.gap_pct > 0 ? `+${fmtPct(r.gap_pct)}` : fmtPct(r.gap_pct)}
                  </span>
                </span>
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {r.projects_count}
              </td>
              <td className="pr-3.5 text-right">
                {r.unquantified_count > 0 ? (
                  <span className="inline-flex justify-end">
                    <Badge variant="warning" className="font-mono">
                      {r.unquantified_count}
                    </Badge>
                  </span>
                ) : (
                  <span className="font-mono text-[12.5px] text-[var(--text-faint)]">0</span>
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
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-8 text-center text-sm text-[var(--text-tertiary)]">
        Sin datos para esta agrupación en la ventana seleccionada.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <table className="w-full table-fixed text-sm">
        <colgroup>
          <col />
          <col style={{ width: 90 }} />
          <col style={{ width: 104 }} />
          <col style={{ width: 104 }} />
          <col style={{ width: 104 }} />
          <col style={{ width: 130 }} />
        </colgroup>
        <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
          <tr>
            <SortableTh<T> sortKey="label" getter={(r) => String(r[labelKey] ?? "")} ctrl={ctrl} className="h-8.5">
              {labelHeader}
            </SortableTh>
            <SortableTh<T> sortKey="resources" getter={(r) => r.resources} ctrl={ctrl} align="right" className="h-8.5 pr-3.5">
              Recursos
            </SortableTh>
            <SortableTh<T> sortKey="capacity" getter={(r) => r.capacity_pct} ctrl={ctrl} align="right" className="h-8.5 pr-3.5">
              Capacidad
            </SortableTh>
            <SortableTh<T> sortKey="demand" getter={(r) => r.demand_pct} ctrl={ctrl} align="right" className="h-8.5 pr-3.5">
              Demanda
            </SortableTh>
            <SortableTh<T> sortKey="gap" getter={(r) => r.gap_pct} ctrl={ctrl} align="right" className="h-8.5 pr-3.5">
              Gap
            </SortableTh>
            <SortableTh<T> sortKey="overloaded" getter={(r) => r.overloaded} ctrl={ctrl} align="right" className="h-8.5 pr-3.5">
              Sobrecargados
            </SortableTh>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((r, i) => (
            <tr
              key={`${String(r[labelKey])}-${i}`}
              className="h-10.5 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] even:bg-[var(--color-subtle)] hover:bg-[var(--color-subtle)]"
            >
              <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)]">
                {String(r[labelKey] ?? "—")}
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {r.resources}
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {fmtPct(r.capacity_pct)}
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                {fmtPct(r.demand_pct)}
              </td>
              <td className="pr-3.5 text-right">
                <span className="inline-flex items-center justify-end gap-1.75">
                  <GapDot color={r.color} />
                  <span className="font-mono text-[12.5px] text-[var(--text-primary)]">
                    {r.gap_pct > 0 ? `+${fmtPct(r.gap_pct)}` : fmtPct(r.gap_pct)}
                  </span>
                </span>
              </td>
              <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
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
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--text-tertiary)]">
        Sin conflictos de sobreasignación en la ventana seleccionada.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
        Conflicto a resolver
      </span>
      {conflicts.map((c) => (
        <article
          key={c.actor_id}
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <GapDot color={c.color} />
              <span className="text-[15px] font-semibold text-[var(--text-primary)]">
                {c.name}
              </span>
              {c.is_key_resource ? (
                <span role="img" aria-label="Recurso clave">
                  <Icono nombre="lock" size={13} className="text-[var(--color-warning-fg)]" />
                </span>
              ) : null}
              {c.discipline ? (
                <span className="text-xs text-[var(--text-tertiary)]">
                  · {c.discipline}
                </span>
              ) : null}
            </div>
            <div className="text-[12.5px] text-[var(--text-secondary)]">
              Demanda{" "}
              <span className="font-mono font-semibold text-[var(--color-danger-fg)]">
                {fmtPct(c.demand_pct)}
              </span>{" "}
              vs capacidad <span className="font-mono">{fmtPct(c.capacity_pct)}</span> (
              <span className="font-mono font-medium">+{fmtPct(c.over_pct)}</span> sobre
              capacidad)
            </div>
          </div>

          <ul className="mt-3">
            {c.projects.map((p) => (
              <li
                key={p.project_id}
                className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-subtle)] py-2 text-[12.5px] shadow-[var(--linea-surco-arriba)]"
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
                    <span className="text-[12px] tracking-[0.01em]">{p.folio}</span>{" "}
                    <span className="text-[var(--text-primary)]">{p.name}</span>
                  </Link>
                  {p.is_critical ? <Badge variant="danger">Crítico</Badge> : null}
                </div>
                <span className="font-mono text-[var(--text-secondary)]">
                  {p.allocation_pct !== null ? fmtPct(p.allocation_pct) : "Sin FTE%"}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-3 flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] px-3 py-2.5 text-[12.5px] leading-[1.5] text-[var(--color-warning-fg)]">
            <Icono nombre="triangle-alert" size={15} className="mt-0.5 shrink-0" />
            <span>{c.recommendation}</span>
          </div>
        </article>
      ))}
    </div>
  );
}
