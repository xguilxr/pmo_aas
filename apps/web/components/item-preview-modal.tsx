"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ExternalLink, X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * ENH-088 — preview "tarjeta flotante" centrada sobre la página actual.
 *
 * Reemplaza el side-panel original (US-053). Solo quick view: id, título,
 * status, severidad/prioridad, owner, fechas y descripción truncada. NO
 * incluye edición, comentarios ni historial — esos viven en la página
 * dedicada del item, accesible vía el botón "Abrir ficha completa".
 *
 * Cierre con `Esc`, click en el backdrop o el botón ×.
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
  /** ENH-088 CA4: link a la ficha completa del item. */
  openHref?: string;
  openLabel?: string;
  footer?: ReactNode;
};

export function ItemPreviewModal({
  open,
  onClose,
  title,
  subtitle,
  fields,
  description,
  openHref,
  openLabel,
  footer,
}: Props) {
  // ENH-088 CA5: cerrar con Esc.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  // ENH-088 CA1: tarjeta centrada con backdrop semi-transparente,
  // animación fade-in simple via CSS.
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[oklch(0%_0_0_/_0.4)] px-4 py-6 animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-[var(--border-default)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-[var(--color-primary)]">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-0.5 truncate font-mono text-[11px] text-[var(--color-tertiary)]">
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
        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
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
              <p className="line-clamp-6 whitespace-pre-wrap text-sm text-[var(--color-primary)]">
                {description}
              </p>
            </div>
          ) : null}
        </div>
        <footer className="flex items-center justify-end gap-2 border-t border-[var(--border-default)] px-5 py-3">
          {footer}
          {openHref ? (
            <Link href={openHref} onClick={onClose}>
              <Button size="sm" variant="primary">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                {openLabel ?? "Abrir ficha completa"}
              </Button>
            </Link>
          ) : null}
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cerrar
          </Button>
        </footer>
      </div>
    </div>
  );
}
