"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Calendar, Network, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  listOrganizations,
  listPrograms,
  type Organization,
  type Program,
} from "@/lib/api/organizations";

/**
 * US-075 sub-bloque B — Vista informativa del catálogo de programas
 * del tenant. Cards agrupan programa + org + fechas + estado. Click
 * lleva al resumen `/pmo/programs/{id}` (US-034) que ya tiene KPIs y
 * top risks. El CRUD de programas sigue en `/admin/organizations/{id}`
 * y se accede desde el ADMIN_NAV.
 */

function fmtDate(v: string | null): string {
  if (!v) return "—";
  try {
    return new Date(v).toLocaleDateString("es-MX");
  } catch {
    return v;
  }
}

export default function ProgramsListPage() {
  const [search, setSearch] = useState("");
  const [orgFilter, setOrgFilter] = useState<string>("all");
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listOrganizations({ is_active: true })
      .then((rows) => {
        if (!cancelled) setOrgs(rows);
      })
      .catch(() => {
        /* non-fatal: filter will just be empty */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listPrograms({
      organization_id: orgFilter === "all" ? undefined : orgFilter,
      is_active: activeFilter === "all" ? undefined : activeFilter === "active",
    })
      .then((rows) => {
        if (!cancelled) setPrograms(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudieron cargar los programas",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgFilter, activeFilter]);

  const orgNameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const o of orgs) m.set(o.id, o.name);
    return m;
  }, [orgs]);

  const filteredPrograms = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return programs;
    return programs.filter((p) => p.name.toLowerCase().includes(q));
  }, [programs, search]);

  const totalCount = programs.length;
  const activeCount = programs.filter((p) => p.is_active).length;

  const empty = !loading && !error && filteredPrograms.length === 0;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="space-y-1">
        <nav className="text-[11px] text-[var(--color-tertiary)]">
          <Link href="/pmo" className="hover:underline">
            PMO
          </Link>
          <span className="mx-1">/</span>
          <span>Programas</span>
        </nav>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Programas
        </h1>
        <p className="text-sm text-[var(--color-tertiary)]">
          Catálogo informativo de programas del tenant. Click en un programa
          para ver KPIs y top risks. La creación/edición se hace desde el
          panel de cada organización en `/admin`.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <KpiCard label="Programas totales" value={loading ? "…" : totalCount} />
        <KpiCard label="Activos" value={loading ? "…" : activeCount} />
        <KpiCard
          label="Inactivos"
          value={loading ? "…" : totalCount - activeCount}
        />
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <div className="grid gap-3 sm:grid-cols-[1fr_200px_180px]">
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
              aria-label="Buscar programas"
            />
          </div>
          <Select
            value={orgFilter}
            onChange={(e) => setOrgFilter(e.target.value)}
            aria-label="Filtrar por organización"
          >
            <option value="all">Todas las organizaciones</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </Select>
          <Select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value)}
            aria-label="Filtrar por estado"
          >
            <option value="all">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
          </Select>
        </div>
      </section>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-[var(--radius-xl)]" />
          ))}
        </div>
      ) : empty ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
          {orgFilter === "all"
            ? "No hay programas todavía. Se crean desde el panel de una organización en /admin."
            : "Esta organización no tiene programas."}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filteredPrograms.map((p) => (
            <ProgramCard
              key={p.id}
              program={p}
              orgName={orgNameById.get(p.organization_id) ?? "Organización"}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
      <div className="text-xs text-[var(--color-tertiary)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-[var(--color-primary)]">
        {value}
      </div>
    </div>
  );
}

function ProgramCard({
  program,
  orgName,
}: {
  program: Program;
  orgName: string;
}) {
  return (
    <Link
      href={`/pmo/programs/${program.id}`}
      className="flex flex-col gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-subtle)]"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
            <Network className="h-4 w-4" aria-hidden />
          </div>
          <h3 className="min-w-0 truncate text-sm font-semibold text-[var(--color-primary)]">
            {program.name}
          </h3>
        </div>
        {!program.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
      </div>
      {program.description ? (
        <p className="line-clamp-2 text-[12px] text-[var(--color-secondary)]">
          {program.description}
        </p>
      ) : null}
      <div className="mt-auto flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-[var(--color-tertiary)]">
        <span className="truncate">{orgName}</span>
        <span className="inline-flex items-center gap-1">
          <Calendar className="h-3 w-3" aria-hidden />
          {fmtDate(program.start_date)} → {fmtDate(program.end_date)}
        </span>
      </div>
    </Link>
  );
}
