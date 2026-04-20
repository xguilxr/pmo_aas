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
import { ApiError } from "@/lib/api";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
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

const ALL_PHASES: ProjectPhase[] = ["planning", "execution", "support", "closed"];
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

function formatMxn(n: string | number | null): string {
  if (n === null) return "—";
  const v = typeof n === "string" ? Number(n) : n;
  if (!Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(v);
}

export default function ProjectsListPage() {
  const router = useRouter();
  const search = useSearchParams();

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
  const [q, setQ] = useState(search.get("q") ?? "");
  const [onlyMine, setOnlyMine] = useState(search.get("only_mine") === "true");
  const [view, setView] = useState<"list" | "board">(
    (search.get("view") as "list" | "board") ?? "list",
  );

  const debouncedQ = useDebounced(q, 300);

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [rows, setRows] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listOrganizations({ is_active: true })
      .then(setOrgs)
      .catch(() => {});
  }, []);

  const syncUrl = useCallback(() => {
    const usp = new URLSearchParams();
    for (const p of phases) usp.append("phase", p);
    for (const t of types) usp.append("type", t);
    for (const h of health) usp.append("health", h);
    if (orgId) usp.set("organization_id", orgId);
    if (debouncedQ.trim()) usp.set("q", debouncedQ.trim());
    if (onlyMine) usp.set("only_mine", "true");
    if (view !== "list") usp.set("view", view);
    const s = usp.toString();
    router.replace(`/admin/projects${s ? `?${s}` : ""}`, { scroll: false });
  }, [phases, types, health, orgId, debouncedQ, onlyMine, view, router]);

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
  }, [phases, types, health, orgId, debouncedQ, onlyMine]);

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
            Gestiona el portafolio: filtra por fase, organización, tipo, salud y prioridad.
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
          <Link href="/admin/projects/new">
            <Button>
              <Plus className="h-4 w-4" aria-hidden /> Nuevo proyecto
            </Button>
          </Link>
        </div>
      </header>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 sm:grid-cols-[1fr_200px_160px]">
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
          <Select value={orgId} onChange={(e) => setOrgId(e.target.value)} aria-label="Organización">
            <option value="">Todas las organizaciones</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
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
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
          <tr>
            <th className="h-10 px-4 font-medium">Proyecto</th>
            <th className="h-10 px-4 font-medium">Organización</th>
            <th className="h-10 px-4 font-medium">Fase</th>
            <th className="h-10 px-4 font-medium">Prioridad</th>
            <th className="h-10 px-4 font-medium">Avance</th>
            <th className="h-10 px-4 font-medium">Presupuesto</th>
            <th className="h-10 px-4 font-medium">Salud</th>
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
          ) : rows.length ? (
            rows.map((p) => (
              <tr
                key={p.id}
                className="h-14 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
              >
                <td className="px-4">
                  <Link
                    href={`/admin/projects/${p.id}`}
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
                  {formatMxn(p.budget)}
                </td>
                <td className="px-4">
                  <HealthDot health={p.health_status} />
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
    </div>
  );
}

function BoardView({ rows, loading }: { rows: Project[]; loading: boolean }) {
  const grouped = useMemo(() => {
    const out: Record<ProjectPhase, Project[]> = {
      planning: [],
      execution: [],
      support: [],
      closed: [],
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
      {(["planning", "execution", "support", "closed"] as ProjectPhase[]).map((phase) => (
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
                href={`/admin/projects/${p.id}`}
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
  const tone: Record<ProjectPhase, "info" | "warning" | "neutral" | "success"> = {
    planning: "info",
    execution: "success",
    support: "warning",
    closed: "neutral",
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
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] text-[var(--text-secondary)]">
      <span
        className={cn("h-2 w-2 rounded-full shadow-[inset_0_-1px_2px_oklch(0%_0_0/0.12)]", color)}
      />
      {HEALTH_LABEL[health]}
    </span>
  );
}
