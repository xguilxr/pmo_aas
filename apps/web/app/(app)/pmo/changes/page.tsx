"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import { CHANGE_STATUS_LABEL, CHANGE_TYPE_LABEL } from "@/lib/api/modules";
import {
  listTenantChanges,
  type TenantChange,
} from "@/lib/api/tenant-cross";

const STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "draft", label: "Borrador" },
  { value: "proposed", label: "Propuesto" },
  { value: "in_review", label: "En revisión" },
  { value: "approved", label: "Aprobado" },
  { value: "rejected", label: "Rechazado" },
];

// ENH-186 (mismo patrón que el detalle de proyecto): tono de badge por
// estado. `draft`/`proposed` no están en `ChangeStatus` pero el filtro los
// admite (ver STATUS_OPTIONS); el fallback "neutral" los cubre.
const CHANGE_STATUS_VARIANT: Record<string, "warning" | "success" | "danger" | "neutral"> = {
  in_review: "warning",
  approved: "success",
  rejected: "danger",
  implemented: "success",
  cancelled: "neutral",
};

function TenantChangesInner() {
  const searchParams = useSearchParams();
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  // ENH-009: ?status=in_review llega desde el KPI "Cambios en revisión"
  // del dashboard para abrir la vista con el filtro pre-aplicado.
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [rows, setRows] = useState<TenantChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<TenantChange | null>(null);
  const { sortedRows, ctrl: sortCtrl } = useSortableRows<TenantChange>(rows);

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
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Cambios · Tenant
        </h1>
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Solicitudes de cambio de todos los proyectos accesibles.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
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

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--text-tertiary)]">
            Sin registros para los filtros actuales.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-[13px]">
              <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
                <tr>
                  <th className="h-8.5 w-10 px-3" />
                  <SortableTh<TenantChange> sortKey="folio" getter={(r) => r.folio} ctrl={sortCtrl} className="h-8.5 w-24">Folio</SortableTh>
                  <SortableTh<TenantChange> sortKey="title" getter={(r) => r.title} ctrl={sortCtrl} className="h-8.5">Título</SortableTh>
                  <SortableTh<TenantChange> sortKey="status" getter={(r) => r.status} ctrl={sortCtrl} className="h-8.5 w-32">Estado</SortableTh>
                  <SortableTh<TenantChange> sortKey="type" getter={(r) => r.type ?? ""} ctrl={sortCtrl} className="h-8.5 w-28">Tipo</SortableTh>
                  <SortableTh<TenantChange> sortKey="project" getter={(r) => r.project_name ?? ""} ctrl={sortCtrl} className="h-8.5 w-56">Proyecto</SortableTh>
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((r) => (
                  <tr key={r.id} className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] hover:bg-[var(--color-subtle)]">
                    <td className="h-11 px-3 align-middle">
                      <button
                        type="button"
                        onClick={() => setPreview(r)}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
                        aria-label="Preview"
                      >
                        <Icono nombre="eye" size={15} />
                      </button>
                    </td>
                    <td className="h-11 px-3 align-middle text-[12px] tracking-[0.01em] text-[var(--text-tertiary)]">
                      {r.folio}
                    </td>
                    <td className="h-11 px-3 align-middle">
                      <Link
                        href={`/pmo/projects/${r.project_id}/changes`}
                        className="block overflow-hidden text-ellipsis whitespace-nowrap text-[var(--text-primary)] hover:underline"
                        title={r.title}
                      >
                        {r.title}
                      </Link>
                    </td>
                    <td className="h-11 px-3 align-middle">
                      <Badge variant={CHANGE_STATUS_VARIANT[r.status] ?? "neutral"}>
                        {CHANGE_STATUS_LABEL[r.status] ?? r.status}
                      </Badge>
                    </td>
                    <td className="h-11 px-3 align-middle text-[12.5px] text-[var(--text-secondary)]">
                      {r.type ? (CHANGE_TYPE_LABEL[r.type] ?? r.type) : "—"}
                    </td>
                    <td className="h-11 px-3 align-middle">
                      <Link
                        href={`/pmo/projects/${r.project_id}`}
                        className="block overflow-hidden text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--color-accent)] hover:underline"
                        title={r.project_name}
                      >
                        <span className="text-[12px] tracking-[0.01em]">{r.project_folio}</span>
                        <span className="ml-1 text-[var(--text-secondary)]">
                          — {r.project_name}
                        </span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
                { label: "Tipo", value: preview.type ? (CHANGE_TYPE_LABEL[preview.type] ?? preview.type) : "—" },
                { label: "Estado", value: CHANGE_STATUS_LABEL[preview.status] ?? preview.status },
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
    <Suspense fallback={<div className="p-8 text-sm text-[var(--text-tertiary)]">Cargando…</div>}>
      <TenantChangesInner />
    </Suspense>
  );
}
