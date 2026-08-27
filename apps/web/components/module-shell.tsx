"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";

type Props<T extends { id: string; folio: string }> = {
  projectId: string;
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  records: T[];
  loading: boolean;
  error?: string | null;
  columns: { key: string; label: string; render: (r: T) => ReactNode; width?: number; align?: "left" | "right" }[];
  filters?: ReactNode;
  onRowClick?: (r: T) => void;
  newButtonLabel?: string;
  newButtonVariant?: "primary" | "secondary" | "ghost" | "danger";
  newModalTitle?: string;
  newModalForm?: (close: () => void) => ReactNode;
  newModalFooter?: (close: () => void) => ReactNode;
  newModalOpen?: boolean;
  setNewModalOpen?: (open: boolean) => void;
  emptyLabel?: string;
  footer?: ReactNode;
  /** Acciones adicionales al lado del botón "Nuevo" (ej. "Generar con IA"). */
  headerExtras?: ReactNode;
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
  newButtonVariant,
  newModalTitle,
  newModalForm,
  newModalFooter,
  newModalOpen: newModalOpenProp,
  setNewModalOpen: setNewModalOpenProp,
  emptyLabel = "Sin registros.",
  footer,
  headerExtras,
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
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/pmo/projects/${projectId}`} className="hover:underline">
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
          <div className="flex flex-wrap items-center gap-2">
            {headerExtras}
            {newModalForm ? (
              <Button onClick={() => setOpen(true)} variant={newButtonVariant}>
                <Icono nombre="plus" size={15} /> {newButtonLabel}
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="border-t border-[var(--border-default)]">
        {filters ? (
          <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] py-3 shadow-[var(--linea-surco)]">
            {filters}
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead
              className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]"
            >
              <tr>
                <th className="h-8.5 w-24 px-4 font-semibold">Folio</th>
                {columns.map((c) => (
                  <th
                    key={c.key}
                    className={cn("h-8.5 px-4 font-semibold", c.align === "right" && "pr-3.5 text-right")}
                    style={c.width ? { width: c.width } : undefined}
                  >
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]">
                      <td className="h-11 px-4">
                        <Skeleton className="h-4 w-16" />
                      </td>
                      {columns.map((c) => (
                        <td key={c.key} className="h-11 px-4">
                          <Skeleton className="h-4 w-24" />
                        </td>
                      ))}
                    </tr>
                  ))
                : records.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => onRowClick?.(r)}
                      className="h-11 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] transition-colors hover:bg-[var(--color-subtle)]"
                      style={{ cursor: onRowClick ? "pointer" : undefined }}
                    >
                      <td className="overflow-hidden px-4 text-ellipsis whitespace-nowrap text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                        {r.folio}
                      </td>
                      {columns.map((c) => (
                        <td
                          key={c.key}
                          className={cn(
                            "overflow-hidden px-4 text-ellipsis whitespace-nowrap text-[var(--text-primary)]",
                            c.align === "right" && "pr-3.5 text-right",
                          )}
                          style={c.width ? { width: c.width, maxWidth: c.width } : undefined}
                        >
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
