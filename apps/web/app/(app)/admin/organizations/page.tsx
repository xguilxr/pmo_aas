"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  FolderKanban,
  Layers,
  Plus,
  Search,
  Users,
  Workflow,
} from "lucide-react";

import { ProgramModal } from "@/components/program-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import {
  listOrganizationPanels,
  type OrganizationPanel,
} from "@/lib/api/organizations";

function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

function MetricTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-2 rounded-[var(--radius-md)] bg-[var(--color-subtle)] px-2.5 py-1.5">
      <span className="text-[var(--color-tertiary)]">{icon}</span>
      <div className="leading-tight">
        <div className="text-[11px] text-[var(--color-tertiary)]">{label}</div>
        <div className="text-sm font-semibold text-[var(--color-primary)]">
          {value}
        </div>
      </div>
    </div>
  );
}

function HealthStrip({ h }: { h: OrganizationPanel["portfolio_health"] }) {
  const total = h.green + h.yellow + h.red;
  if (total === 0) {
    return (
      <div className="text-[11px] italic text-[var(--color-tertiary)]">
        Sin proyectos activos
      </div>
    );
  }
  const pct = (n: number) => `${(n / total) * 100}%`;
  return (
    <div className="space-y-1">
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-subtle)]">
        {h.green > 0 ? (
          <span
            className="bg-emerald-500"
            style={{ width: pct(h.green) }}
            aria-label={`${h.green} verde`}
          />
        ) : null}
        {h.yellow > 0 ? (
          <span
            className="bg-amber-400"
            style={{ width: pct(h.yellow) }}
            aria-label={`${h.yellow} ámbar`}
          />
        ) : null}
        {h.red > 0 ? (
          <span
            className="bg-rose-500"
            style={{ width: pct(h.red) }}
            aria-label={`${h.red} rojo`}
          />
        ) : null}
      </div>
      <div className="flex gap-3 text-[11px] text-[var(--color-tertiary)]">
        <span>🟢 {h.green}</span>
        <span>🟡 {h.yellow}</span>
        <span>🔴 {h.red}</span>
      </div>
    </div>
  );
}

function OrgCard({ panel }: { panel: OrganizationPanel }) {
  return (
    <Link
      href={`/admin/organizations/${panel.id}`}
      className="group flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--color-accent)]"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
          {panel.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={panel.logo_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <Building2 className="h-5 w-5" aria-hidden />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-[var(--color-primary)] group-hover:text-[var(--color-accent)]">
              {panel.name}
            </span>
            {!panel.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
          </div>
          <div className="truncate text-xs text-[var(--color-tertiary)]">
            {[panel.industry, panel.country].filter(Boolean).join(" · ") ||
              "Sin datos de industria"}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricTile
          icon={<Workflow className="h-4 w-4" aria-hidden />}
          label="Unidades"
          value={panel.business_unit_count}
        />
        <MetricTile
          icon={<Users className="h-4 w-4" aria-hidden />}
          label="Departamentos"
          value={panel.department_count}
        />
        <MetricTile
          icon={<Layers className="h-4 w-4" aria-hidden />}
          label="Programas"
          value={panel.program_count}
        />
        <MetricTile
          icon={<FolderKanban className="h-4 w-4" aria-hidden />}
          label="Proyectos activos"
          value={panel.active_project_count}
        />
      </div>

      <div>
        <div className="mb-1 text-[11px] font-medium text-[var(--color-tertiary)]">
          Salud del portafolio
        </div>
        <HealthStrip h={panel.portfolio_health} />
      </div>
    </Link>
  );
}

export default function OrganizationsListPage() {
  const { canCreate } = useMyPermissions();
  const canCreateOrg = canCreate("organizations");
  const canCreateProgram = canCreate("programs");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 300);
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const [panels, setPanels] = useState<OrganizationPanel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showProgramModal, setShowProgramModal] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listOrganizationPanels({
      q: debouncedSearch.trim() || undefined,
      is_active: activeFilter === "all" ? undefined : activeFilter === "active",
    })
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
  }, [debouncedSearch, activeFilter]);

  const empty = useMemo(
    () => !loading && !error && panels.length === 0,
    [loading, error, panels.length],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Organizaciones
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Vista de paneles. Click en una organización para ver su detalle,
            programas y proyectos.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canCreateProgram ? (
            <Button variant="secondary" onClick={() => setShowProgramModal(true)}>
              <Layers className="h-4 w-4" aria-hidden />
              Nuevo programa
            </Button>
          ) : null}
          {canCreateOrg ? (
            <Link href="/admin/organizations/new">
              <Button>
                <Plus className="h-4 w-4" aria-hidden />
                Nueva organización
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-tertiary)]"
              aria-hidden
            />
            <Input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre"
              className="pl-9"
              aria-label="Buscar organizaciones"
            />
          </div>
          <Select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value)}
            aria-label="Filtrar por estado"
          >
            <option value="all">Todos los estados</option>
            <option value="active">Activas</option>
            <option value="inactive">Inactivas</option>
          </Select>
        </div>
      </section>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52 w-full rounded-[var(--radius-xl)]" />
          ))}
        </div>
      ) : empty ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
          Aún no hay organizaciones. Crea la primera.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {panels.map((p) => (
            <OrgCard key={p.id} panel={p} />
          ))}
        </div>
      )}

      <ProgramModal
        open={showProgramModal}
        onClose={() => setShowProgramModal(false)}
        onSaved={async () => {
          setShowProgramModal(false);
          await new Promise((r) => setTimeout(r, 500));
          window.location.reload();
        }}
      />
    </div>
  );
}
