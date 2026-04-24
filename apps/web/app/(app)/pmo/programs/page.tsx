"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Calendar, Network, Plus, Search } from "lucide-react";

import { ProgramModal } from "@/components/program-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
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
  const [showProgramModal, setShowProgramModal] = useState(false);

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

  const empty = !loading && !error && filteredPrograms.length === 0;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Programas
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Agrupa proyectos bajo iniciativas estratégicas. Selecciona una
            organización para crear un programa.
          </p>
        </div>
        <Button variant="secondary" onClick={() => setShowProgramModal(true)}>
          <Plus className="h-4 w-4" aria-hidden />
          Nuevo programa
        </Button>
      </header>

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

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="divide-y divide-[var(--border-subtle)]">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-4">
                  <Skeleton className="h-9 w-9 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-72" />
                  </div>
                </div>
              ))
            : filteredPrograms.map((p) => (
                <Link
                  key={p.id}
                  href={`/admin/organizations/${p.organization_id}`}
                  className="flex items-center gap-3 px-4 py-4 hover:bg-[var(--color-subtle)]"
                >
                  <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                    <Network className="h-4 w-4" aria-hidden />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-primary)]">
                        {p.name}
                      </span>
                      {!p.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
                    </div>
                    <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--color-tertiary)]">
                      <span>
                        {orgNameById.get(p.organization_id) ?? "Organización"}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="h-3 w-3" aria-hidden />
                        {fmtDate(p.start_date)} → {fmtDate(p.end_date)}
                      </span>
                    </div>
                  </div>
                  <Link
                    href={`/pmo/projects?program_id=${p.id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs text-[var(--color-accent)] hover:underline"
                  >
                    Ver proyectos →
                  </Link>
                </Link>
              ))}
          {empty ? (
            <div className="px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
              {orgFilter === "all"
                ? "No hay programas todavía. Créalos desde el detalle de una organización."
                : "Esta organización no tiene programas."}
            </div>
          ) : null}
        </div>
      </section>

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
