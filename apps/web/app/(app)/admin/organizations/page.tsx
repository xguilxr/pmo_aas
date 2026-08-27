"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ProgramModal } from "@/components/program-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import {
  listOrganizationPanels,
  type OrganizationPanel,
  type OrganizationPanelHealth,
} from "@/lib/api/organizations";
import { HEALTH_LABEL } from "@/lib/api/projects";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";

function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

function MetricChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col gap-0.75 rounded-[var(--radius-sm)] bg-[var(--color-muted)] p-2">
      <span className="text-[10px] text-[var(--text-tertiary)]">{label}</span>
      <span className="font-mono text-sm font-semibold text-[var(--text-primary)]">
        {value}
      </span>
    </div>
  );
}

const HEALTH_DOT_BG: Record<keyof OrganizationPanelHealth, string> = {
  green: "bg-[var(--color-success-fg)]",
  yellow: "bg-[var(--color-warning-fg)]",
  red: "bg-[var(--color-danger-fg)]",
};

function HealthDonut({ h }: { h: OrganizationPanelHealth }) {
  const total = h.green + h.yellow + h.red;
  const p1 = total > 0 ? (h.green / total) * 100 : 0;
  const p2 = total > 0 ? p1 + (h.yellow / total) * 100 : 0;
  return (
    <span
      aria-hidden
      className="h-16 w-16 flex-none rounded-full"
      style={{
        background: `conic-gradient(var(--color-success-fg) 0 ${p1}%, var(--color-warning-fg) ${p1}% ${p2}%, var(--color-danger-fg) ${p2}% 100%)`,
        mask: "radial-gradient(circle, transparent 44%, black 45%)",
        WebkitMask: "radial-gradient(circle, transparent 44%, black 45%)",
      }}
    />
  );
}

function PortfolioHealth({ h }: { h: OrganizationPanelHealth }) {
  const total = h.green + h.yellow + h.red;
  if (total === 0) {
    return (
      <div className="flex items-center justify-center gap-2 border-t border-[var(--border-subtle)] py-4.5 text-[11.5px] italic text-[var(--text-faint)] shadow-[var(--linea-surco-arriba)]">
        <Icono nombre="info" size={14} />
        Sin proyectos activos que evaluar
      </div>
    );
  }
  return (
    <div className="flex items-center gap-4 border-t border-[var(--border-subtle)] pt-2.5 shadow-[var(--linea-surco-arriba)]">
      <HealthDonut h={h} />
      <div className="flex flex-1 flex-col gap-1.25">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-[var(--text-tertiary)]">
          Salud del portafolio
        </span>
        {(Object.keys(HEALTH_DOT_BG) as Array<keyof OrganizationPanelHealth>).map((k) => (
          <span
            key={k}
            className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]"
          >
            <span className={`h-1.75 w-1.75 rounded-full ${HEALTH_DOT_BG[k]}`} />
            {HEALTH_LABEL[k]}
            <span className="ml-auto font-mono text-[var(--text-primary)]">{h[k]}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function OrgCard({ panel }: { panel: OrganizationPanel }) {
  return (
    <Link
      href={`/admin/organizations/${panel.id}`}
      className="group flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)] transition-colors hover:border-[var(--color-accent)]"
    >
      <div className="flex items-center justify-between gap-2.5">
        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          <div className="flex h-10 w-10 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] text-[var(--text-tertiary)]">
            {panel.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={panel.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <Icono nombre="building" size={19} />
            )}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-semibold text-[var(--text-primary)] group-hover:text-[var(--color-accent)]">
              {panel.name}
            </span>
            <span className="truncate text-[11.5px] text-[var(--text-tertiary)]">
              {[panel.industry, panel.country].filter(Boolean).join(" · ") ||
                "Sin datos de industria"}
            </span>
          </div>
        </div>
        {!panel.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
      </div>

      <div className="grid grid-cols-3 gap-2">
        <MetricChip label="Portafolios" value={panel.portfolio_count} />
        <MetricChip label="Programas" value={panel.program_count} />
        <MetricChip label="Proy. activos" value={panel.active_project_count} />
      </div>

      <PortfolioHealth h={panel.portfolio_health} />
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
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(panels);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showProgramModal, setShowProgramModal] = useState(false);
  // ENH-190: label configurable por tenant para "Organización(es)".

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
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Organizaciones
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Vista de paneles. Click en una organización para ver su
            detalle, programas y proyectos.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canCreateProgram ? (
            <Button variant="secondary" onClick={() => setShowProgramModal(true)}>
              <Icono nombre="folders" size={15} />
              Nuevo programa
            </Button>
          ) : null}
          {canCreateOrg ? (
            <Link href="/admin/organizations/new">
              <Button>
                <Icono nombre="plus" size={15} />
                Nueva organización
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2.5">
        <div className="relative w-full sm:w-70">
          <Icono
            nombre="search"
            size={15}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
          />
          <Input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre"
            className="pl-8"
            aria-label="Buscar organizaciones"
          />
        </div>
        <Select
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
          aria-label="Filtrar por estado"
          className="w-full sm:w-37.5"
        >
          <option value="all">Todos los estados</option>
          <option value="active">Activas</option>
          <option value="inactive">Inactivas</option>
        </Select>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52 w-full rounded-[var(--radius-xl)]" />
          ))}
        </div>
      ) : empty ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-12 text-center text-sm text-[var(--text-tertiary)]">
          Aún no hay organizaciones. Crea la primera.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
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
