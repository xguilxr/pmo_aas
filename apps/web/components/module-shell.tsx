"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { Plus } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";

type Props<T extends { id: string; folio: string }> = {
  projectId: string;
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  records: T[];
  loading: boolean;
  error?: string | null;
  columns: { key: string; label: string; render: (r: T) => ReactNode }[];
  filters?: ReactNode;
  onRowClick?: (r: T) => void;
  newButtonLabel?: string;
  newModalTitle?: string;
  newModalForm?: (close: () => void) => ReactNode;
  newModalFooter?: (close: () => void) => ReactNode;
  newModalOpen?: boolean;
  setNewModalOpen?: (open: boolean) => void;
  emptyLabel?: string;
  footer?: ReactNode;
};

export function ModuleShell<T extends { id: string; folio: string }>({
  projectId,
  title,
  subtitle,
  icon,
  records,
  loading,
  error,
  columns,
  filters,
  onRowClick,
  newButtonLabel = "Nuevo",
  newModalTitle,
  newModalForm,
  newModalFooter,
  newModalOpen: newModalOpenProp,
  setNewModalOpen: setNewModalOpenProp,
  emptyLabel = "Sin registros.",
  footer,
}: Props<T>) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = newModalOpenProp ?? internalOpen;
  const setOpen = setNewModalOpenProp ?? setInternalOpen;

  useEffect(() => {
    if (!newModalForm) setInternalOpen(false);
  }, [newModalForm]);

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="space-y-2">
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/admin/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/admin/projects/${projectId}`} className="hover:underline">
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <span>{title}</span>
        </nav>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex items-start gap-3">
            {icon ? (
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--text-secondary)]">
                {icon}
              </span>
            ) : null}
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                  {title}
                </h1>
                <span className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-[11px] tabular-nums text-[var(--text-secondary)]">
                  {records.length}
                </span>
              </div>
              {subtitle ? (
                <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">{subtitle}</p>
              ) : null}
            </div>
          </div>
          {newModalForm ? (
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden /> {newButtonLabel}
            </Button>
          ) : null}
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        {filters ? (
          <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] p-4">
            {filters}
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
              <tr>
                <th className="h-10 w-24 px-4 font-medium">Folio</th>
                {columns.map((c) => (
                  <th key={c.key} className="h-10 px-4 font-medium">
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-[var(--border-subtle)]">
                      <td className="h-14 px-4">
                        <Skeleton className="h-4 w-16" />
                      </td>
                      {columns.map((c) => (
                        <td key={c.key} className="h-14 px-4">
                          <Skeleton className="h-4 w-24" />
                        </td>
                      ))}
                    </tr>
                  ))
                : records.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => onRowClick?.(r)}
                      className="h-14 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
                      style={{ cursor: onRowClick ? "pointer" : undefined }}
                    >
                      <td className="px-4 font-mono text-[11px] text-[var(--text-secondary)]">
                        {r.folio}
                      </td>
                      {columns.map((c) => (
                        <td key={c.key} className="px-4 text-[var(--text-primary)]">
                          {c.render(r)}
                        </td>
                      ))}
                    </tr>
                  ))}
              {!loading && records.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length + 1}
                    className="px-4 py-16 text-center text-[var(--text-tertiary)]"
                  >
                    {emptyLabel}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {footer}
      </section>

      {newModalForm ? (
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title={newModalTitle ?? newButtonLabel}
          size="lg"
          footer={newModalFooter ? newModalFooter(() => setOpen(false)) : null}
        >
          {newModalForm(() => setOpen(false))}
        </Modal>
      ) : null}
    </div>
  );
}
