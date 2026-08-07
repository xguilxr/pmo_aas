"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { LayoutGrid, List as ListIcon, Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { HealthEvaluationModal } from "@/components/health-evaluation-modal";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import {
  listOrganizations,
  listPrograms,
  type Organization,
  type Program,
} from "@/lib/api/organizations";
import {
  HEALTH_LABEL,
  PHASE_LABEL,
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
import { useOrgLabel } from "@/lib/org-label";

const ALL_PHASES: ProjectPhase[] = [
  "planning",
  "execution",
  "hypercare",
  "closed",
  "cancelled",
];
const ALL_TYPES: ProjectType[] = ["innovation", "transformation", "operation", "bau"];
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
  const orgLabel = useOrgLabel();

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

  const [phases, setPhases] = useState<ProjectPhase[]>(initialPhases);
  const [types, setTypes] = useState<ProjectType[]>(initialTypes);
  const [health, setHealth] = useState<ProjectHealth[]>(initialHealth);
  const [orgId, setOrgId] = useState(search.get("organization_id") ?? "");
  // ENH-185: cascada de programa (depende de organización) + prioridad mínima.
  const [programId, setProgramId] = useState(search.get("program_id") ?? "");
  const [noProgram, setNoProgram] = useState(search.get("no_program") === "true");
  const [priorityMin, setPriorityMin] = useState(search.get("priority_min") ?? "");
  const [q, setQ] = useState(search.get("q") ?? "");
  const [onlyMine, setOnlyMine] = useState(search.get("only_mine") === "true");
  const [view, setView] = useState<"list" | "board">(
    (search.get("view") as "list" | "board") ?? "list",
  );

  const debouncedQ = useDebounced(q, 300);

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [rows, setRows] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listOrganizations({ is_active: true })
      .then(setOrgs)
      .catch(() => {});
  }, []);

  // ENH-185: programas en cascada — dependen de la organización elegida.
  useEffect(() => {
    if (!orgId) {
      setPrograms([]);
      return;
    }
    let cancelled = false;
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

  const syncUrl = useCallback(() => {
    const usp = new URLSearchParams();
    for (const p of phases) usp.append("phase", p);
    for (const t of types) usp.append("type", t);
    for (const h of health) usp.append("health", h);
    if (orgId) usp.set("organization_id", orgId);
    if (noProgram) {
      usp.set("no_program", "true");
    } else if (programId) {
      usp.set("program_id", programId);
    }
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
    programId,
    noProgram,
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
    listProjects({
      phase: phases.length ? phases : undefined,
      type: types.length ? types : undefined,
      health: health.length ? health : undefined,
      organization_id: orgId || undefined,
      program_id: !noProgram && programId ? programId : undefined,
      no_program: noProgram || undefined,
      priority_min: priorityMin ? Number(priorityMin) : undefined,
      q: debouncedQ.trim() || undefined,
      only_mine: onlyMine || undefined,
      limit: 60,
    })
      .then((r) => {
        if (!cancelled) setRows(r);
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
  }, [phases, types, health, orgId, programId, noProgram, priorityMin, debouncedQ, onlyMine]);

  function toggleIn<T extends string>(arr: T[], val: T, setter: (v: T[]) => void) {
    setter(arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Proyectos
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Gestiona el portafolio: filtra por fase, {orgLabel.singular.toLowerCase()}, programa, tipo, salud y prioridad.
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
              <ListIcon className="h-3.5 w-3.5" aria-hidden /> Lista
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
              <LayoutGrid className="h-3.5 w-3.5" aria-hidden /> Tablero
            </button>
          </div>
          {permsCanCreate ? (
            <Link href="/pmo/projects/new">
              <Button>
                <Plus className="h-4 w-4" aria-hidden /> Nuevo proyecto
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 sm:grid-cols-[1fr_200px_200px_160px]">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]"
              aria-hidden
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
          <Select
            value={orgId}
            onChange={(e) => {
              setOrgId(e.target.value);
              // ENH-185: al cambiar de organización, el programa elegido
              // (si lo había) deja de ser válido — resetea la cascada.
              setProgramId("");
              setNoProgram(false);
            }}
            aria-label={orgLabel.singular}
          >
            <option value="">
              {orgLabel.singular === "Portafolio" ? "Todos los" : "Todas las"}{" "}
              {orgLabel.plural.toLowerCase()}
            </option>
            {/* DIS-03: un inquilino recién creado no tiene organizaciones. */}
            {orgs.length === 0 ? (
              <option value="" disabled>
                (aún no hay organizaciones)
              </option>
            ) : null}
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </Select>
          <Select
            value={noProgram ? "__no_program__" : programId}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "__no_program__") {
                setNoProgram(true);
                setProgramId("");
              } else {
                setNoProgram(false);
                setProgramId(v);
              }
            }}
            disabled={!orgId}
            aria-label="Programa"
          >
            {orgId ? (
              <>
                <option value="">Todos los programas</option>
                <option value="__no_program__">Sin programa</option>
                {/* DIS-03: la organización elegida puede no tener programas. */}
                {programs.length === 0 ? (
                  <option value="" disabled>
                    (esta organización no tiene programas)
                  </option>
                ) : null}
                {programs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </>
            ) : (
              <option value="">Selecciona {orgLabel.singularArticled}</option>
            )}
          </Select>
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

        <div className="flex flex-wrap gap-2 border-b border-[var(--border-subtle)] p-4">
          <FilterGroup label="Fase">
            {ALL_PHASES.map((p) => (
              <Chip
                key={p}
                active={phases.includes(p)}
                onClick={() => toggleIn(phases, p, setPhases)}
              >
                {PHASE_LABEL[p]}
              </Chip>
            ))}
          </FilterGroup>
          <FilterGroup label="Tipo">
            {ALL_TYPES.map((t) => (
              <Chip key={t} active={types.includes(t)} onClick={() => toggleIn(types, t, setTypes)}>
                {TYPE_LABEL[t]}
              </Chip>
            ))}
          </FilterGroup>
          <FilterGroup label="Salud">
            {ALL_HEALTH.map((h) => (
              <Chip
                key={h}
                active={health.includes(h)}
                onClick={() => toggleIn(health, h, setHealth)}
                tone={h}
              >
                {HEALTH_LABEL[h]}
              </Chip>
            ))}
          </FilterGroup>
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
        </div>

        {error ? (
          <div className="p-4">
            <Banner variant="danger">{error}</Banner>
          </div>
        ) : null}

        {view === "list" ? (
          <ListView rows={rows} loading={loading} orgs={orgs} />
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

function Chip({
  active,
  onClick,
  children,
  tone,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  tone?: "green" | "yellow" | "red";
}) {
  const activeTone =
    tone === "green"
      ? "border-[var(--color-success-border)] bg-[var(--color-success-bg)] text-[var(--color-success-fg)]"
      : tone === "yellow"
        ? "border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]"
        : tone === "red"
          ? "border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]"
          : "border-[var(--text-primary)] bg-[var(--text-primary)] text-[var(--color-inverse)]";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex h-7 items-center rounded-full border px-2.5 text-[12px] font-medium transition-colors",
        active
          ? activeTone
          : "border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]",
      )}
    >
      {children}
    </button>
  );
}

function ListView({
  rows,
  loading,
  orgs,
}: {
  rows: Project[];
  loading: boolean;
  orgs: Organization[];
}) {
  const orgsMap = useMemo(() => Object.fromEntries(orgs.map((o) => [o.id, o])), [orgs]);
  const { sortedRows, ctrl: sortCtrl } = useSortableRows<Project>(rows);
  // ENH-190: label configurable por tenant para "Organización(es)".
  const orgLabel = useOrgLabel();
  // US-192: evaluar la salud 5+1 desde el portafolio (click en el dot),
  // sin abrir cada proyecto. El override repinta el dot sin refetch.
  const [evalTarget, setEvalTarget] = useState<{ id: string; name: string } | null>(null);
  const [healthOverride, setHealthOverride] = useState<
    Record<string, Project["health_status"]>
  >({});
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
          <tr>
            <SortableTh<Project> sortKey="name" getter={(p) => p.name} ctrl={sortCtrl} className="h-10 px-4">Proyecto</SortableTh>
            <SortableTh<Project> sortKey="org" getter={(p) => orgsMap[p.organization_id]?.name ?? ""} ctrl={sortCtrl} className="h-10 px-4">{orgLabel.singular}</SortableTh>
            <SortableTh<Project> sortKey="phase" getter={(p) => p.phase ?? ""} ctrl={sortCtrl} className="h-10 px-4">Fase</SortableTh>
            <SortableTh<Project> sortKey="priority" getter={(p) => (p as any).priority ?? ""} ctrl={sortCtrl} className="h-10 px-4">Prioridad</SortableTh>
            <SortableTh<Project> sortKey="progress" getter={(p) => (p as any).progress_pct ?? 0} ctrl={sortCtrl} className="h-10 px-4">Avance</SortableTh>
            <SortableTh<Project> sortKey="budget" getter={(p) => (p as any).budget ?? 0} ctrl={sortCtrl} className="h-10 px-4">Presupuesto</SortableTh>
            <SortableTh<Project> sortKey="health" getter={(p) => (p as any).health ?? ""} ctrl={sortCtrl} className="h-10 px-4">Salud</SortableTh>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <tr key={i} className="border-b border-[var(--border-subtle)]">
                {Array.from({ length: 7 }).map((_, j) => (
                  <td key={j} className="h-14 px-4">
                    <Skeleton className="h-4 w-24" />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedRows.length ? (
            sortedRows.map((p) => (
              <tr
                key={p.id}
                className="h-14 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
              >
                <td className="px-4">
                  <Link
                    href={`/pmo/projects/${p.id}`}
                    className="font-medium text-[var(--text-primary)] hover:underline"
                  >
                    {p.name}
                  </Link>
                  <div className="font-mono text-[11px] text-[var(--text-tertiary)]">{p.folio}</div>
                </td>
                <td className="px-4 text-[var(--text-secondary)]">
                  {orgsMap[p.organization_id]?.name ?? "—"}
                </td>
                <td className="px-4">
                  <PhasePill phase={p.phase} />
                </td>
                <td className="px-4 text-[var(--text-secondary)] tabular-nums">
                  {p.priority ?? "—"}
                </td>
                <td className="px-4 w-40">
                  <ProgressBar value={p.progress} />
                </td>
                <td className="px-4 tabular-nums text-[var(--text-secondary)]">
                  {formatImporte(p.budget, p.currency)}
                </td>
                <td className="px-4">
                  {/* US-192: click = evaluar salud 5+1 sin abrir el proyecto. */}
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
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={7} className="px-4 py-16 text-center text-[var(--text-tertiary)]">
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
      planning: [],
      execution: [],
      hypercare: [],
      closed: [],
      cancelled: [],
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
      {(["planning", "execution", "hypercare", "closed"] as ProjectPhase[]).map((phase) => (
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
                <div className="mt-1 font-mono text-[11px] text-[var(--text-tertiary)]">
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
  const tone: Record<
    ProjectPhase,
    "info" | "warning" | "neutral" | "success" | "danger"
  > = {
    planning: "info",
    execution: "success",
    hypercare: "warning",
    closed: "neutral",
    // ADR-022: cancelado se distingue de cerrado a simple vista, que es el
    // punto entero de la decisión.
    cancelled: "danger",
  };
  return <Badge variant={tone[phase]}>{PHASE_LABEL[phase]}</Badge>;
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
      <span className="w-9 text-right text-[11px] tabular-nums text-[var(--text-secondary)]">
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
