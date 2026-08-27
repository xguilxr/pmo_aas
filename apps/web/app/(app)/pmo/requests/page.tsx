"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useOrgFiltro } from "@/components/organizacion-activa";
import {
  listRequests,
  REQUEST_STATUS_LABEL,
  type ProjectRequest,
  type RequestStatus,
} from "@/lib/api/requests";
import { cn } from "@/lib/cn";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";

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

// BUG-092 — cada solicitud lleva la moneda de su importe.
function formatImporte(n: string | number | null | undefined, moneda: string): string {
  if (n === null || n === undefined || n === "") return "—";
  const v = typeof n === "string" ? Number(n) : n;
  if (!Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: moneda }).format(v);
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
  const { sortedRows: sortedReqRows, ctrl: reqCtrl } = useSortableRows<ProjectRequest>(rows);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // US-205 — la organización la elige el header.
  const orgId = useOrgFiltro();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listRequests({
      status: tab,
      // US-205 — la solicitud pertenece a una organización, y la vista opera
      // dentro de la activa como todas las demás.
      organization_id: orgId,
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
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Solicitudes
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Bandeja de solicitudes de nuevos proyectos. Revisa, aprueba y convierte en proyecto.
          </p>
        </div>
        <Link href="/pmo/requests/new">
          <Button>
            <Icono nombre="plus" size={15} />
            Nueva solicitud
          </Button>
        </Link>
      </header>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        {/* Bandeja con pestañas de estado — filete inferior 2px en la activa,
            conteo en pastilla --color-muted, nunca botón con fondo. */}
        <div
          role="tablist"
          aria-label="Estado"
          className="flex items-center gap-1 border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]"
        >
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
                  "flex h-9 items-center gap-1.75 border-b-2 px-2.5 text-[13px] transition-colors",
                  active
                    ? "border-[var(--text-primary)] font-semibold text-[var(--text-primary)]"
                    : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
                )}
              >
                {t.label}
                {active && !loading ? (
                  <span className="inline-flex h-4.5 items-center rounded-[5px] bg-[var(--color-muted)] px-1.5 font-mono text-[11px] text-[var(--text-secondary)]">
                    {rows.length}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>

        <div className="border-b border-[var(--border-subtle)] p-4">
          <div className="relative max-w-md">
            <Icono
              nombre="search"
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]"
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
          <table className="w-full table-fixed text-[13px]">
            <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
              <tr>
                <SortableTh<ProjectRequest> sortKey="folio" getter={(r) => r.folio} ctrl={reqCtrl} className="h-8.5 px-4 w-33">Folio</SortableTh>
                <SortableTh<ProjectRequest> sortKey="title" getter={(r) => r.title} ctrl={reqCtrl} className="h-8.5 px-4">Título</SortableTh>
                <SortableTh<ProjectRequest> sortKey="date" getter={(r) => r.requested_at ?? (r as any).created_at ?? ""} ctrl={reqCtrl} className="h-8.5 px-4 w-44">Fecha</SortableTh>
                <SortableTh<ProjectRequest> sortKey="budget" getter={(r) => (r as any).budget ?? 0} ctrl={reqCtrl} className="h-8.5 pl-4 pr-3.5 w-38" align="right">Presupuesto</SortableTh>
                <SortableTh<ProjectRequest> sortKey="status" getter={(r) => r.status} ctrl={reqCtrl} className="h-8.5 px-4 w-33">Estado</SortableTh>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="h-11 border-b border-[var(--border-subtle)]">
                    <td className="px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-4"><Skeleton className="h-4 w-56" /></td>
                    <td className="px-4"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="px-4"><Skeleton className="h-4 w-20" /></td>
                  </tr>
                ))
              ) : sortedReqRows.length > 0 ? (
                sortedReqRows.map((r) => (
                  <tr
                    key={r.id}
                    className="h-11 cursor-pointer border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]"
                    onClick={() => { window.location.href = `/pmo/requests/${r.id}`; }}
                  >
                    <td className="overflow-hidden px-4 text-ellipsis whitespace-nowrap text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                      <Link href={`/pmo/requests/${r.id}`} className="hover:underline">
                        {r.folio}
                      </Link>
                    </td>
                    <td className="min-w-0 px-4">
                      <div className="overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)]">
                        {r.title}
                      </div>
                      <div className="overflow-hidden text-ellipsis whitespace-nowrap text-[11.5px] text-[var(--text-tertiary)]">
                        {r.sponsor}
                      </div>
                    </td>
                    <td className="overflow-hidden px-4 text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-secondary)]">
                      {formatDate(r.requested_at)}
                    </td>
                    <td className="pl-4 pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-primary)]">
                      {formatImporte(r.budget, r.currency)}
                    </td>
                    <td className="px-4">
                      <StatusBadge status={r.status} />
                    </td>
                  </tr>
                ))
              ) : null}
              {empty ? (
                <tr>
                  <td colSpan={5} className="px-4 py-16 text-center text-[13px] text-[var(--text-tertiary)]">
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
