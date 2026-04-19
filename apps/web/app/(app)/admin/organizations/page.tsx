"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Building2, Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  listOrganizations,
  type Organization,
} from "@/lib/api/organizations";

function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export default function OrganizationsListPage() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 300);
  const [activeFilter, setActiveFilter] = useState<string>("all");

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listOrganizations({
      q: debouncedSearch.trim() || undefined,
      is_active: activeFilter === "all" ? undefined : activeFilter === "active",
    })
      .then((r) => {
        if (!cancelled) setOrgs(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudieron cargar las organizaciones",
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
    () => !loading && !error && orgs.length === 0,
    [loading, error, orgs.length],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Organizaciones</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Gestiona los clientes de tu tenant. Cada organización agrupa programas y proyectos.
          </p>
        </div>
        <Link href="/admin/organizations/new">
          <Button>
            <Plus className="h-4 w-4" aria-hidden />
            Nueva organización
          </Button>
        </Link>
      </header>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="grid gap-3 border-b border-[var(--border-default)] p-4 sm:grid-cols-[1fr_180px]">
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

        {error ? (
          <div className="p-4">
            <Banner variant="danger">{error}</Banner>
          </div>
        ) : null}

        <div className="divide-y divide-[var(--border-subtle)]">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-64" />
                  </div>
                </div>
              ))
            : orgs.map((o) => (
                <Link
                  key={o.id}
                  href={`/admin/organizations/${o.id}`}
                  className="flex items-center gap-3 px-4 py-4 hover:bg-[var(--color-subtle)]"
                >
                  <div className="flex h-10 w-10 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                    {o.logo_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={o.logo_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <Building2 className="h-5 w-5" aria-hidden />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-primary)]">
                        {o.name}
                      </span>
                      {!o.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
                    </div>
                    <div className="truncate text-xs text-[var(--color-tertiary)]">
                      {[o.industry, o.country].filter(Boolean).join(" · ") || "Sin datos"}
                    </div>
                  </div>
                  <span className="text-sm text-[var(--color-tertiary)]">Ver →</span>
                </Link>
              ))}
          {empty ? (
            <div className="px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
              Aún no hay organizaciones. Crea la primera.
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
