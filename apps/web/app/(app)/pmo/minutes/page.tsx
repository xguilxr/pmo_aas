"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Eye, MessageSquare } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import {
  listTenantMinutes,
  type TenantMinute,
} from "@/lib/api/tenant-cross";

export default function TenantMinutesPage() {
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  const [rows, setRows] = useState<TenantMinute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<TenantMinute | null>(null);
  const { sortedRows, ctrl: sortCtrl } = useSortableRows<TenantMinute>(rows);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenantMinutes(filter)
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
    <div className="space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <MessageSquare className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Minutas · Tenant
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Minutas de reunión de todos los proyectos accesibles.
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
            Sin minutas para los filtros actuales.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <th className="w-10 px-3 py-2" />
                <SortableTh<TenantMinute> sortKey="folio" getter={(r) => r.folio} ctrl={sortCtrl}>Folio</SortableTh>
                <SortableTh<TenantMinute> sortKey="title" getter={(r) => (r as any).title ?? ""} ctrl={sortCtrl}>Minuta</SortableTh>
                <SortableTh<TenantMinute> sortKey="date" getter={(r) => (r as any).meeting_date ?? ""} ctrl={sortCtrl}>Fecha</SortableTh>
                <SortableTh<TenantMinute> sortKey="origin" getter={(r) => (r as any).source ?? ""} ctrl={sortCtrl}>Origen</SortableTh>
                <SortableTh<TenantMinute> sortKey="project" getter={(r) => (r as any).project_name ?? ""} ctrl={sortCtrl}>Proyecto</SortableTh>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((r) => (
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
                      href={`/pmo/projects/${r.project_id}/minutes/${r.id}`}
                      className="text-[var(--color-primary)] hover:underline"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {new Date(r.meeting_date).toLocaleDateString("es-MX")}
                  </td>
                  <td className="px-3 py-2">
                    {r.generated_by_ai ? <Badge variant="info">IA</Badge> : <span>Manual</span>}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/pmo/projects/${r.project_id}`}
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

      <ItemPreviewModal
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={preview?.title ?? ""}
        subtitle={preview?.folio}
        fields={
          preview
            ? [
                { label: "ID", value: preview.id, mono: true },
                {
                  label: "Proyecto",
                  value: `${preview.project_folio} — ${preview.project_name}`,
                },
                {
                  label: "Fecha",
                  value: new Date(preview.meeting_date).toLocaleDateString("es-MX"),
                },
                { label: "Participantes", value: preview.participants.length },
                { label: "Temas", value: preview.topics.length },
                { label: "Acuerdos", value: preview.agreements.length },
                { label: "Origen", value: preview.generated_by_ai ? "IA" : "Manual" },
              ]
            : []
        }
      />
    </div>
  );
}
