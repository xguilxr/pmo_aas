"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
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
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Minutas
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Minutas de reunión de todos los proyectos accesibles.
          </p>
        </div>
        <TenantCrossFilters value={filter} onChange={setFilter} />
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="border-t border-[var(--border-default)]">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
              <tr>
                <th className="h-8.5 w-11 px-4" />
                <SortableTh<TenantMinute>
                  sortKey="folio"
                  getter={(r) => r.folio}
                  ctrl={sortCtrl}
                  className="h-8.5 w-31 px-4 font-semibold"
                >
                  Folio
                </SortableTh>
                <SortableTh<TenantMinute>
                  sortKey="title"
                  getter={(r) => (r as any).title ?? ""}
                  ctrl={sortCtrl}
                  className="h-8.5 px-4 font-semibold"
                >
                  Minuta
                </SortableTh>
                <SortableTh<TenantMinute>
                  sortKey="date"
                  getter={(r) => (r as any).meeting_date ?? ""}
                  ctrl={sortCtrl}
                  className="h-8.5 w-33 px-4 font-semibold"
                >
                  Fecha
                </SortableTh>
                <SortableTh<TenantMinute>
                  sortKey="origin"
                  getter={(r) => (r as any).source ?? ""}
                  ctrl={sortCtrl}
                  className="h-8.5 w-26 px-4 font-semibold"
                >
                  Origen
                </SortableTh>
                <SortableTh<TenantMinute>
                  sortKey="project"
                  getter={(r) => (r as any).project_name ?? ""}
                  ctrl={sortCtrl}
                  className="h-8.5 w-55 px-4 font-semibold"
                >
                  Proyecto
                </SortableTh>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="h-11 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]">
                      <td className="px-4">
                        <Skeleton className="h-4 w-4.5" />
                      </td>
                      <td className="px-4">
                        <Skeleton className="h-4 w-20" />
                      </td>
                      <td className="px-4">
                        <Skeleton className="h-4 w-48" />
                      </td>
                      <td className="px-4">
                        <Skeleton className="h-4 w-20" />
                      </td>
                      <td className="px-4">
                        <Skeleton className="h-4 w-14" />
                      </td>
                      <td className="px-4">
                        <Skeleton className="h-4 w-36" />
                      </td>
                    </tr>
                  ))
                : sortedRows.map((r) => (
                    <tr
                      key={r.id}
                      className="h-11 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] transition-colors hover:bg-[var(--color-subtle)]"
                    >
                      <td className="px-4">
                        <button
                          type="button"
                          onClick={() => setPreview(r)}
                          className="inline-flex h-6.5 w-6.5 items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] text-[var(--text-tertiary)] shadow-[var(--relieve-control)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
                          aria-label="Preview"
                        >
                          <Icono nombre="eye" size={14} />
                        </button>
                      </td>
                      <td className="px-4 text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                        {r.folio}
                      </td>
                      <td className="overflow-hidden px-4 text-ellipsis whitespace-nowrap text-[13px]">
                        <Link
                          href={`/pmo/projects/${r.project_id}/minutes/${r.id}`}
                          className="text-[var(--text-primary)] hover:underline"
                        >
                          {r.title}
                        </Link>
                      </td>
                      <td className="px-4 font-mono text-[12.5px] text-[var(--text-secondary)]">
                        {new Date(r.meeting_date).toLocaleDateString("es-MX")}
                      </td>
                      <td className="px-4">
                        {r.generated_by_ai ? (
                          <Badge variant="info">IA</Badge>
                        ) : (
                          <span className="text-[12.5px] text-[var(--text-secondary)]">Manual</span>
                        )}
                      </td>
                      <td className="overflow-hidden px-4 text-ellipsis whitespace-nowrap">
                        <Link
                          href={`/pmo/projects/${r.project_id}`}
                          className="text-[12.5px] hover:underline"
                          title={r.project_name}
                        >
                          <span className="text-[var(--text-tertiary)]">{r.project_folio}</span>
                          <span className="ml-1 text-[var(--text-secondary)]">
                            — {r.project_name}
                          </span>
                        </Link>
                      </td>
                    </tr>
                  ))}
              {!loading && sortedRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-16 text-center text-[13px] text-[var(--text-tertiary)]">
                    Sin minutas para los filtros actuales.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
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
