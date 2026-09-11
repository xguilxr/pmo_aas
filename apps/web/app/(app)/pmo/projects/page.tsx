"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { FiltroMultiple } from "@/components/ui/filtro-multiple";
import { HealthEvaluationModal } from "@/components/health-evaluation-modal";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import {
  listPortfolios,
  listPrograms,
  type Organization,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import {
  HEALTH_LABEL,
  PHASE_BADGE_TONE,
  PHASE_LABEL,
  PHASE_ORDER,
  TYPE_LABEL,
  listProjects,
  type Project,
  type ProjectHealth,
  type ProjectPhase,
  type ProjectType,
} from "@/lib/api/projects";
import { cn } from "@/lib/cn";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";

// US-202 — el orden canónico vive en `lib/api/projects.ts::PHASE_ORDER`.
const ALL_PHASES: ProjectPhase[] = [...PHASE_ORDER];
const ALL_TYPES: ProjectType[] = ["transformacion", "operacion", "innovacion", "bau"];
const ALL_HEALTH: ProjectHealth[] = ["green", "yellow", "red"];

function useDebounced<T>(value: T, delayMs = 300): T {
  const [d, setD] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setD(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return d;
}

// BUG-092 — cada fila lleva la moneda de su proyecto.
function formatImporte(n: string | number | null, moneda: string): string {
  if (n === null) return "—";
  const v = typeof n === "string" ? Number(n) : n;
  if (!Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  }).format(v);
}

export default function ProjectsListPage() {
  const router = useRouter();
  const { canCreate } = useMyPermissions();
  const permsCanCreate = canCreate("projects");
  const search = useSearchParams();
  // ENH-190: label configurable por tenant para "Organización(es)".

  const initialPhases = useMemo(() => {
    const v = search.getAll("phase").filter((p): p is ProjectPhase => (ALL_PHASES as string[]).includes(p));
    return v.length ? v : [];
  }, [search]);
  const initialTypes = useMemo(() => {
    const v = search.getAll("type").filter((t): t is ProjectType => (ALL_TYPES as string[]).includes(t));
    return v;
  }, [search]);
  const initialHealth = useMemo(() => {
    const v = search.getAll("health").filter((t): t is ProjectHealth => (ALL_HEALTH as string[]).includes(t));
    return v;
  }, [search]);

  const initialPortfolioIds = useMemo(() => search.getAll("portfolio_id"), [search]);
  const initialProgramIds = useMemo(() => search.getAll("program_id"), [search]);

  const [phases, setPhases] = useState<ProjectPhase[]>(initialPhases);
  const [types, setTypes] = useState<ProjectType[]>(initialTypes);
  const [health, setHealth] = useState<ProjectHealth[]>(initialHealth);
  // US-205 — la organización viene del header, no de esta página.
  const { efectiva: orgId } = useOrganizacionActiva();
  // FASE-5 (revamp v2, US-B) — Portafolio y Programa pasan a FiltroMultiple
  // (W6): listProjects solo acepta un id escalar, así que con más de uno
  // marcado se filtra en cliente (la primera opción del runbook).
  // "__sin__" representa "sin portafolio"/"sin programa".
  const [portfolioIds, setPortfolioIds] = useState<string[]>(initialPortfolioIds);
  const [programIds, setProgramIds] = useState<string[]>(initialProgramIds);
  const [priorityMin, setPriorityMin] = useState(search.get("priority_min") ?? "");
  const [q, setQ] = useState(search.get("q") ?? "");
  const [onlyMine, setOnlyMine] = useState(search.get("only_mine") === "true");
  const [view, setView] = useState<"list" | "board">(
    (search.get("view") as "list" | "board") ?? "list",
  );

  const debouncedQ = useDebounced(q, 300);

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [rows, setRows] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ENH-185 / FASE-5 — portafolios y programas en cascada, dependen de la
  // organización elegida.
  useEffect(() => {
    if (!orgId) {
      setPortfolios([]);
      setPrograms([]);
      return;
    }
    let cancelled = false;
    listPortfolios(orgId, { is_active: true })
      .then((r) => {
        if (!cancelled) setPortfolios(r);
      })
      .catch(() => {
        if (!cancelled) setPortfolios([]);
      });
    listPrograms({ organization_id: orgId, is_active: true })
      .then((r) => {
        if (!cancelled) setPrograms(r);
      })
      .catch(() => {
        if (!cancelled) setPrograms([]);
      });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  const nombrePortafolio = useMemo(
    () => new Map(portfolios.map((p) => [p.id, p.name])),
    [portfolios],
  );
  const nombrePrograma = useMemo(
    () => new Map(programs.map((p) => [p.id, p.name])),
    [programs],
  );

  const syncUrl = useCallback(() => {
    const usp = new URLSearchParams();
    for (const p of phases) usp.append("phase", p);
    for (const t of types) usp.append("type", t);
    for (const h of health) usp.append("health", h);
    for (const id of portfolioIds) usp.append("portfolio_id", id);
    for (const id of programIds) usp.append("program_id", id);
    if (priorityMin) usp.set("priority_min", priorityMin);
    if (debouncedQ.trim()) usp.set("q", debouncedQ.trim());
    if (onlyMine) usp.set("only_mine", "true");
    if (view !== "list") usp.set("view", view);
    const s = usp.toString();
    router.replace(`/pmo/projects${s ? `?${s}` : ""}`, { scroll: false });
  }, [
    phases,
    types,
    health,
    orgId,
    portfolioIds,
    programIds,
    priorityMin,
    debouncedQ,
    onlyMine,
    view,
    router,
  ]);

  useEffect(() => {
    syncUrl();
  }, [syncUrl]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // FASE-5 — portafolio/programa son multi-select; `listProjects` solo
    // acepta un id escalar, así que con más de uno marcado se trae la
    // cartera completa y se filtra en cliente (abajo).
    const soloUnPortafolio = portfolioIds.length === 1 ? portfolioIds[0] : undefined;
    const soloUnPrograma = programIds.length === 1 ? programIds[0] : undefined;
    listProjects({
      phase: phases.length ? phases : undefined,
      type: types.length ? types : undefined,
      health: health.length ? health : undefined,
      organization_id: orgId || undefined,
      portfolio_id:
        soloUnPortafolio && soloUnPortafolio !== "__sin__" ? soloUnPortafolio : undefined,
      no_portfolio: soloUnPortafolio === "__sin__" || undefined,
      program_id: soloUnPrograma && soloUnPrograma !== "__sin__" ? soloUnPrograma : undefined,
      no_program: soloUnPrograma === "__sin__" || undefined,
      priority_min: priorityMin ? Number(priorityMin) : undefined,
      q: debouncedQ.trim() || undefined,
      only_mine: onlyMine || undefined,
      limit: portfolioIds.length > 1 || programIds.length > 1 ? 500 : 60,
    })
      .then((r) => {
        if (cancelled) return;
        const filtradas = r.filter((p) => {
          if (portfolioIds.length > 1) {
            const clave = p.portfolio_id ?? "__sin__";
            if (!portfolioIds.includes(clave)) return false;
          }
          if (programIds.length > 1) {
            const clave = p.program_id ?? "__sin__";
            if (!programIds.includes(clave)) return false;
          }
          return true;
        });
        setRows(filtradas);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudieron cargar los proyectos");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [phases, types, health, orgId, portfolioIds, programIds, priorityMin, debouncedQ, onlyMine]);

  const hayFiltro = Boolean(
    portfolioIds.length ||
      programIds.length ||
      phases.length ||
      types.length ||
      health.length ||
      priorityMin,
  );

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Proyectos
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Gestiona la cartera: filtra por fase, organización, portafolio, programa, tipo, salud y prioridad.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-[10px] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-1">
            <button
              type="button"
              onClick={() => setView("list")}
              aria-pressed={view === "list"}
              className={cn(
                "inline-flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[12px] font-medium transition-colors",
                view === "list"
                  ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icono nombre="list-check" size={14} /> Lista
            </button>
            <button
              type="button"
              onClick={() => setView("board")}
              aria-pressed={view === "board"}
              className={cn(
                "inline-flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[12px] font-medium transition-colors",
                view === "board"
                  ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icono nombre="grid-2x2" size={14} /> Tablero
            </button>
          </div>
          {permsCanCreate ? (
            <Link href="/pmo/projects/new">
              <Button>
                <Icono nombre="plus" size={15} /> Nuevo proyecto
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 sm:grid-cols-[1fr_160px]">
          <div className="relative">
            <Icono
              nombre="search"
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]"
            />
            <Input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por nombre, folio o sponsor"
              className="pl-9"
              aria-label="Buscar proyectos"
            />
          </div>
          <label className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 text-[13px] text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={onlyMine}
              onChange={(e) => setOnlyMine(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border-strong)]"
            />
            Sólo míos
          </label>
        </div>

        {/* FASE-5 (revamp v2, W6) — filtros como dropdown con checkmarks,
            selección múltiple. Portafolio y Programa reemplazan al `Select`
            único de antes; Fase/Tipo/Salud reemplazan a los `Chip` sueltos. */}
        <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] p-4">
          <FiltroMultiple
            label="Portafolio"
            opciones={
              portfolios.length === 0
                ? [{ value: "__sin__", label: "Sin portafolio" }]
                : [
                    { value: "__sin__", label: "Sin portafolio" },
                    ...portfolios.map((p) => ({ value: p.id, label: p.name })),
                  ]
            }
            seleccion={portfolioIds}
            onChange={setPortfolioIds}
          />
          <FiltroMultiple
            label="Programa"
            opciones={
              programs.length === 0
                ? [{ value: "__sin__", label: "Sin programa" }]
                : [
                    { value: "__sin__", label: "Sin programa" },
                    ...programs.map((p) => ({ value: p.id, label: p.name })),
                  ]
            }
            seleccion={programIds}
            onChange={setProgramIds}
          />
          <FiltroMultiple
            label="Fase"
            opciones={ALL_PHASES.map((p) => ({ value: p, label: PHASE_LABEL[p] }))}
            seleccion={phases}
            onChange={(v) => setPhases(v as ProjectPhase[])}
          />
          <FiltroMultiple
            label="Tipo"
            opciones={ALL_TYPES.map((t) => ({ value: t, label: TYPE_LABEL[t] }))}
            seleccion={types}
            onChange={(v) => setTypes(v as ProjectType[])}
          />
          <FiltroMultiple
            label="Salud"
            opciones={ALL_HEALTH.map((h) => ({ value: h, label: HEALTH_LABEL[h] }))}
            seleccion={health}
            onChange={(v) => setHealth(v as ProjectHealth[])}
          />
          <FilterGroup label="Prioridad mínima">
            <Select
              value={priorityMin}
              onChange={(e) => setPriorityMin(e.target.value)}
              aria-label="Prioridad mínima"
              className="h-7 w-auto rounded-full border-[var(--border-default)] bg-[var(--color-surface)] px-2.5 text-[12px] text-[var(--text-secondary)]"
            >
              <option value="">Cualquiera</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}+
                </option>
              ))}
            </Select>
          </FilterGroup>
          {hayFiltro ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setPortfolioIds([]);
                setProgramIds([]);
                setPhases([]);
                setTypes([]);
                setHealth([]);
                setPriorityMin("");
              }}
            >
              Limpiar
            </Button>
          ) : null}
        </div>

        {error ? (
          <div className="p-4">
            <Banner variant="danger">{error}</Banner>
          </div>
        ) : null}

        {view === "list" ? (
          <ListView
            rows={rows}
            loading={loading}
            nombrePortafolio={nombrePortafolio}
            nombrePrograma={nombrePrograma}
          />
        ) : (
          <BoardView rows={rows} loading={loading} />
        )}
      </section>
    </div>
  );
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}

function ListView({
  rows,
  loading,
  nombrePortafolio,
  nombrePrograma,
}: {
  rows: Project[];
  loading: boolean;
  nombrePortafolio: Map<string, string>;
  nombrePrograma: Map<string, string>;
}) {
  // FASE-5 (revamp v2, US-B) — orden por defecto portafolio → programa →
  // nombre (mismo criterio que la vista maestra de `/pmo`, fase 4);
  // `useSortableRows` lo respeta hasta que alguien haga clic en una columna.
  const ordenadas = useMemo(
    () =>
      [...rows].sort(
        (a, b) =>
          (nombrePortafolio.get(a.portfolio_id ?? "") ?? "￿").localeCompare(
            nombrePortafolio.get(b.portfolio_id ?? "") ?? "￿",
            "es",
          ) ||
          (nombrePrograma.get(a.program_id ?? "") ?? "￿").localeCompare(
            nombrePrograma.get(b.program_id ?? "") ?? "￿",
            "es",
          ) ||
          a.name.localeCompare(b.name, "es"),
      ),
    [rows, nombrePortafolio, nombrePrograma],
  );
  const { sortedRows, ctrl: sortCtrl } = useSortableRows<Project>(ordenadas);
  // ENH-190: label configurable por tenant para "Organización(es)".
  // US-192: evaluar la salud 5+1 desde el portafolio (click en el dot),
  // sin abrir cada proyecto. El override repinta el dot sin refetch.
  const [evalTarget, setEvalTarget] = useState<{ id: string; name: string } | null>(null);
  const [healthOverride, setHealthOverride] = useState<
    Record<string, Project["health_status"]>
  >({});
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed text-[13px]">
        <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
          <tr>
            <SortableTh<Project>
              sortKey="portfolio"
              getter={(p) => nombrePortafolio.get(p.portfolio_id ?? "") ?? ""}
              ctrl={sortCtrl}
              className="h-8.5 px-4 w-33"
            >
              Portafolio
            </SortableTh>
            <SortableTh<Project>
              sortKey="program"
              getter={(p) => nombrePrograma.get(p.program_id ?? "") ?? ""}
              ctrl={sortCtrl}
              className="h-8.5 px-4 w-33"
            >
              Programa
            </SortableTh>
            <SortableTh<Project> sortKey="name" getter={(p) => p.name} ctrl={sortCtrl} className="h-8.5 px-4">Proyecto</SortableTh>
            <SortableTh<Project> sortKey="phase" getter={(p) => p.phase ?? ""} ctrl={sortCtrl} className="h-8.5 px-4 w-33">Fase</SortableTh>
            <SortableTh<Project> sortKey="priority" getter={(p) => (p as any).priority ?? ""} ctrl={sortCtrl} className="h-8.5 pl-4 pr-3.5 w-23" align="right">Prioridad</SortableTh>
            <SortableTh<Project> sortKey="progress" getter={(p) => (p as any).progress_pct ?? 0} ctrl={sortCtrl} className="h-8.5 px-4 w-44">Avance</SortableTh>
            <SortableTh<Project> sortKey="budget" getter={(p) => (p as any).budget ?? 0} ctrl={sortCtrl} className="h-8.5 pl-4 pr-3.5 w-37" align="right">Presupuesto</SortableTh>
            <SortableTh<Project> sortKey="health" getter={(p) => (p as any).health ?? ""} ctrl={sortCtrl} className="h-8.5 px-4 w-19" align="center">Salud</SortableTh>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <tr key={i} className="h-11 border-b border-[var(--border-subtle)]">
                {Array.from({ length: 8 }).map((_, j) => (
                  <td key={j} className="px-4">
                    <Skeleton className="h-4 w-24" />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedRows.length ? (
            sortedRows.map((p) => (
              <tr
                key={p.id}
                className="h-11 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
              >
                <td className="min-w-0 truncate px-4 text-[var(--text-secondary)]">
                  {nombrePortafolio.get(p.portfolio_id ?? "") ?? "—"}
                </td>
                <td className="min-w-0 truncate px-4 text-[var(--text-secondary)]">
                  {nombrePrograma.get(p.program_id ?? "") ?? "—"}
                </td>
                <td className="min-w-0 px-4">
                  <div className="flex min-w-0 flex-col">
                    <Link
                      href={`/pmo/projects/${p.id}`}
                      className="block overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)] hover:underline"
                    >
                      {p.name}
                    </Link>
                    <span className="text-[12px] tracking-[0.01em] text-[var(--text-tertiary)]">
                      {p.folio}
                    </span>
                  </div>
                </td>
                <td className="px-4">
                  <PhasePill phase={p.phase} />
                </td>
                <td className="pl-4 pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                  {p.priority ?? "—"}
                </td>
                <td className="px-4">
                  <ProgressBar value={p.progress} />
                </td>
                <td className="pl-4 pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                  {formatImporte(p.budget, p.currency)}
                </td>
                <td className="px-4">
                  {/* US-192: click = evaluar salud 5+1 sin abrir el proyecto. */}
                  <div className="flex justify-center">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEvalTarget({ id: p.id, name: p.name });
                      }}
                      title="Evaluar salud (5 dimensiones + global)"
                      aria-label={`Evaluar salud de ${p.name}`}
                      className="rounded-full p-1 hover:bg-[var(--color-subtle)]"
                    >
                      <HealthDot health={healthOverride[p.id] ?? p.health_status} />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={8} className="px-4 py-16 text-center text-[var(--text-tertiary)]">
                No hay proyectos que coincidan con los filtros.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {evalTarget ? (
        <HealthEvaluationModal
          projectId={evalTarget.id}
          projectName={evalTarget.name}
          open
          onClose={() => setEvalTarget(null)}
          onSaved={(ev) =>
            setHealthOverride((m) => ({
              ...m,
              [ev.project_id]: ev.overall,
            }))
          }
        />
      ) : null}
    </div>
  );
}

function BoardView({ rows, loading }: { rows: Project[]; loading: boolean }) {
  const grouped = useMemo(() => {
    const out: Record<ProjectPhase, Project[]> = {
      preparacion: [],
      ejecucion: [],
      hypercare: [],
      cerrado: [],
      cancelado: [],
    };
    for (const r of rows) out[r.phase].push(r);
    return out;
  }, [rows]);

  if (loading) {
    return (
      <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
      {// El tablero no pinta columna de cancelados: son proyectos que no siguen.
      (PHASE_ORDER.filter((f) => f !== "cancelado") as ProjectPhase[]).map((phase) => (
        <section
          key={phase}
          className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40"
        >
          <header className="flex items-center justify-between px-3 pt-3 pb-2">
            <span className="text-[13px] font-semibold text-[var(--text-primary)]">
              {PHASE_LABEL[phase]}
            </span>
            <span className="text-[11px] text-[var(--text-tertiary)]">
              {grouped[phase].length}
            </span>
          </header>
          <div className="space-y-2 p-2">
            {grouped[phase].map((p) => (
              <Link
                key={p.id}
                href={`/pmo/projects/${p.id}`}
                className="block rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-3 hover:border-[var(--border-default)]"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[13px] font-medium text-[var(--text-primary)]">
                    {p.name}
                  </span>
                  <HealthDot health={p.health_status} compact />
                </div>
                <div className="mt-1 text-[12px] tracking-[0.01em] text-[var(--text-tertiary)]">
                  {p.folio}
                </div>
                <div className="mt-3">
                  <ProgressBar value={p.progress} />
                </div>
              </Link>
            ))}
            {grouped[phase].length === 0 ? (
              <p className="py-8 text-center text-[12px] text-[var(--text-tertiary)]">Sin proyectos</p>
            ) : null}
          </div>
        </section>
      ))}
    </div>
  );
}

function PhasePill({ phase }: { phase: ProjectPhase }) {
  return <Badge variant={PHASE_BADGE_TONE[phase]}>{PHASE_LABEL[phase]}</Badge>;
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-muted)]">
        <div
          className="h-full rounded-full bg-[var(--text-primary)] transition-[width]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-9 text-right font-mono text-[11px] text-[var(--text-secondary)]">
        {pct}%
      </span>
    </div>
  );
}

function HealthDot({
  health,
  compact,
}: {
  health: ProjectHealth | null;
  compact?: boolean;
}) {
  if (!health) return <span className="text-[12px] text-[var(--text-tertiary)]">—</span>;
  const color =
    health === "green"
      ? "bg-[var(--color-success-fg)]"
      : health === "yellow"
        ? "bg-[var(--color-warning-fg)]"
        : "bg-[var(--color-danger-fg)]";
  if (compact) {
    return (
      <span
        aria-label={HEALTH_LABEL[health]}
        className={cn("inline-block h-2 w-2 rounded-full shadow-[inset_0_-1px_2px_oklch(0%_0_0/0.12)]", color)}
      />
    );
  }
  // ENH-110: semáforo de salud = solo el color, sin la palabra (la dejamos
  // en title/aria-label). Antes mostraba el dot + HEALTH_LABEL.
  return (
    <span
      title={HEALTH_LABEL[health]}
      aria-label={HEALTH_LABEL[health]}
      role="img"
      className={cn("inline-block h-2.5 w-2.5 rounded-full shadow-[inset_0_-1px_2px_oklch(0%_0_0/0.12)]", color)}
    />
  );
}
