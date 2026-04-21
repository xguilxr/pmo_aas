"use client";

import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * Preview rápido tipo Jira (US-053). Se usa desde tablas de RAID,
 * Lecciones, Minutas, Reportes y Recursos: el usuario hace click en un
 * ícono "ojito" y se abre este panel con id/title/fecha/asignado/desc
 * sin navegar a la página de edición completa.
 *
 * Elegí un modal overlay en vez de un <Sheet> lateral para no duplicar
 * un componente nuevo de layout; reutiliza el patrón de overlay +
 * panel derecho (max-width) y respeta el theme.
 */

export type PreviewField = {
  label: string;
  value: ReactNode;
  mono?: boolean;
};

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  fields: PreviewField[];
  description?: string | null;
  footer?: ReactNode;
};

export function ItemPreviewModal({
  open,
  onClose,
  title,
  subtitle,
  fields,
  description,
  footer,
}: Props) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-stretch justify-end bg-[oklch(0%_0_0_/_0.35)]"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <aside
        className="flex h-full w-full max-w-md flex-col overflow-y-auto bg-[var(--color-surface)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-[var(--border-default)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-[var(--color-primary)]">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-0.5 truncate text-[11px] font-mono text-[var(--color-tertiary)]">
                {subtitle}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </header>
        <div className="flex-1 space-y-4 px-5 py-4">
          <dl className="grid grid-cols-[120px_1fr] gap-x-3 gap-y-2 text-sm">
            {fields.map((f, i) => (
              <div key={i} className="contents">
                <dt className="text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                  {f.label}
                </dt>
                <dd
                  className={
                    f.mono
                      ? "break-all font-mono text-xs text-[var(--color-secondary)]"
                      : "text-[var(--color-primary)]"
                  }
                >
                  {f.value ?? (
                    <span className="text-[var(--color-tertiary)]">—</span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
          {description ? (
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                Descripción
              </div>
              <p className="whitespace-pre-wrap text-sm text-[var(--color-primary)]">
                {description}
              </p>
            </div>
          ) : null}
        </div>
        <footer className="flex items-center justify-end gap-2 border-t border-[var(--border-default)] px-5 py-3">
          {footer}
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cerrar
          </Button>
        </footer>
      </aside>
    </div>
  );
}
