"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileText } from "lucide-react";

import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { listTenantReports, type TenantReport } from "@/lib/api/tenant-cross";

export default function TenantReportsPage() {
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  const [rows, setRows] = useState<TenantReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenantReports(filter)
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Reportes · Tenant
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Reportes de todos los proyectos accesibles.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <TenantCrossFilters value={filter} onChange={setFilter} />
      </section>

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin reportes para los filtros actuales.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <th className="px-3 py-2 font-medium">Folio</th>
                <th className="px-3 py-2 font-medium">Título</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium">Período</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2 font-medium">Proyecto</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
                  <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
                    {r.folio}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/admin/projects/${r.project_id}/reports`}
                      className="text-[var(--color-primary)] hover:underline"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.report_type ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.period ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.status}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/admin/projects/${r.project_id}`}
                      className="text-xs text-[var(--color-accent)] hover:underline"
                      title={r.project_name}
                    >
                      <span className="font-mono">{r.project_folio}</span>
                      <span className="ml-1 text-[var(--color-secondary)]">
                        — {r.project_name}
                      </span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
