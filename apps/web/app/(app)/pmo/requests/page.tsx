"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import {
  listRequests,
  REQUEST_STATUS_LABEL,
  type ProjectRequest,
  type RequestStatus,
} from "@/lib/api/requests";
import { cn } from "@/lib/cn";

const TABS: { key: RequestStatus; label: string }[] = [
  { key: "in_review", label: REQUEST_STATUS_LABEL.in_review },
  { key: "needs_info", label: REQUEST_STATUS_LABEL.needs_info },
  { key: "approved", label: REQUEST_STATUS_LABEL.approved },
  { key: "rejected", label: REQUEST_STATUS_LABEL.rejected },
];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function formatMxn(n: string | number | null | undefined): string {
  if (n === null || n === undefined || n === "") return "—";
  const v = typeof n === "string" ? Number(n) : n;
  if (!Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v);
}

function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export default function RequestsListPage() {
  const [tab, setTab] = useState<RequestStatus>("in_review");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 300);

  const [rows, setRows] = useState<ProjectRequest[]>([]);
  const [orgs, setOrgs] = useState<Record<string, Organization>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listOrganizations()
      .then((list) => {
        if (cancelled) return;
        const map: Record<string, Organization> = {};
        for (const o of list) map[o.id] = o;
        setOrgs(map);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listRequests({
      status: tab,
      q: debouncedSearch.trim() || undefined,
      limit: 50,
    })
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudieron cargar las solicitudes",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, debouncedSearch]);

  const empty = useMemo(() => !loading && !error && rows.length === 0, [loading, error, rows.length]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Solicitudes</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Bandeja de solicitudes de nuevos proyectos. Revisa, aprueba y convierte en proyecto.
          </p>
        </div>
        <Link href="/pmo/requests/new">
          <Button>
            <Plus className="h-4 w-4" aria-hidden />
            Nueva solicitud
          </Button>
        </Link>
      </header>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div role="tablist" aria-label="Estado" className="flex flex-wrap gap-1 border-b border-[var(--border-default)] p-2">
          {TABS.map((t) => {
            const active = t.key === tab;
            return (
              <button
                key={t.key}
                role="tab"
                aria-selected={active}
                type="button"
                onClick={() => setTab(t.key)}
                className={cn(
                  "rounded-[var(--radius-md)] px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-[var(--color-subtle)] font-medium text-[var(--color-primary)]"
                    : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
                )}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="border-b border-[var(--border-default)] p-4">
          <div className="relative max-w-md">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-tertiary)]"
              aria-hidden
            />
            <Input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por título"
              className="pl-9"
              aria-label="Buscar solicitudes"
            />
          </div>
        </div>

        {error ? (
          <div className="p-4">
            <Banner variant="danger">{error}</Banner>
          </div>
        ) : null}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <th className="px-4 py-3 font-medium">Folio</th>
                <th className="px-4 py-3 font-medium">Título</th>
                <th className="px-4 py-3 font-medium">Organización</th>
                <th className="px-4 py-3 font-medium">Fecha</th>
                <th className="px-4 py-3 font-medium">Presupuesto</th>
                <th className="px-4 py-3 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-56" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  </tr>
                ))
              ) : rows.length > 0 ? (
                rows.map((r) => (
                  <tr
                    key={r.id}
                    className="cursor-pointer border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                    onClick={() => { window.location.href = `/pmo/requests/${r.id}`; }}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-[var(--color-secondary)]">
                      <Link href={`/pmo/requests/${r.id}`} className="hover:underline">
                        {r.folio}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-[var(--color-primary)]">{r.title}</div>
                      <div className="truncate text-xs text-[var(--color-tertiary)]">{r.sponsor}</div>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      {orgs[r.organization_id]?.name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      {formatDate(r.requested_at)}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      {formatMxn(r.budget)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                  </tr>
                ))
              ) : null}
              {empty ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
                    No hay solicitudes en este estado.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function StatusBadge({ status }: { status: RequestStatus }) {
  const variant =
    status === "approved"
      ? "success"
      : status === "rejected"
        ? "danger"
        : status === "needs_info"
          ? "warning"
          : "info";
  return <Badge variant={variant}>{REQUEST_STATUS_LABEL[status]}</Badge>;
}
