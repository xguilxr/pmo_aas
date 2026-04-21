"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Eye, GitPullRequest } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Banner } from "@/components/ui/banner";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { type ChangeRequest } from "@/lib/api/modules";
import { listTenantChanges } from "@/lib/api/tenant-cross";

const STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "draft", label: "Borrador" },
  { value: "proposed", label: "Propuesto" },
  { value: "in_review", label: "En revisión" },
  { value: "approved", label: "Aprobado" },
  { value: "rejected", label: "Rechazado" },
];

function TenantChangesInner() {
  const searchParams = useSearchParams();
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  // ENH-009: ?status=in_review llega desde el KPI "Cambios en revisión"
  // del dashboard para abrir la vista con el filtro pre-aplicado.
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [rows, setRows] = useState<ChangeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ChangeRequest | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenantChanges({ ...filter, status: status || undefined })
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
  }, [filter, status]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <GitPullRequest className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Cambios · Tenant
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Solicitudes de cambio de todos los proyectos accesibles.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <TenantCrossFilters
          value={filter}
          onChange={setFilter}
          extras={
            <Select
              aria-label="Estado"
              className="h-9 min-w-[160px]"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          }
        />
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
            Sin registros para los filtros actuales.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <th className="w-10 px-3 py-2" />
                <th className="px-3 py-2 font-medium">Folio</th>
                <th className="px-3 py-2 font-medium">Título</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium">Proyecto</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => setPreview(r)}
                      className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                      aria-label="Preview"
                    >
                      <Eye className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
                    {r.folio}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/admin/projects/${r.project_id}/changes`}
                      className="text-[var(--color-primary)] hover:underline"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">{r.status}</td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.type ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/admin/projects/${r.project_id}`}
                      className="font-mono text-xs text-[var(--color-accent)] hover:underline"
                    >
                      {r.project_id.slice(0, 8)}…
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <ItemPreviewModal
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={preview?.title ?? ""}
        subtitle={preview?.folio}
        fields={
          preview
            ? [
                { label: "ID", value: preview.id, mono: true },
                { label: "Proyecto", value: preview.project_id, mono: true },
                { label: "Tipo", value: preview.type ?? "—" },
                { label: "Estado", value: preview.status },
                { label: "Impacto", value: preview.impact ?? "—" },
              ]
            : []
        }
        description={preview?.description ?? null}
      />
    </div>
  );
}

export default function TenantChangesPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-[var(--color-tertiary)]">Cargando…</div>}>
      <TenantChangesInner />
    </Suspense>
  );
}
