"use client";

import { X } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { cn } from "@/lib/cn";

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
};

const SIZES = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

export function Modal({ open, onClose, title, description, children, footer, size = "md" }: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      <button
        type="button"
        aria-label="Cerrar"
        onClick={onClose}
        className="absolute inset-0 bg-[oklch(0%_0_0_/_0.4)]"
      />
      {/* ENH-178: el diálogo se limita al alto del viewport y el cuerpo
          hace scroll interno; header y footer quedan fijos. Antes los
          formularios largos (editar tarea, matching de columnas) se salían
          de la pantalla sin forma de verlos completos. */}
      <div
        className={cn(
          "relative z-10 flex max-h-[calc(100dvh-2rem)] w-full flex-col rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-lg)]",
          SIZES[size],
        )}
      >
        <div className="flex shrink-0 items-start justify-between border-b border-[var(--border-default)] px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-[var(--color-primary)]">{title}</h2>
            {description ? (
              <p className="mt-0.5 text-xs text-[var(--color-tertiary)]">{description}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer ? (
          <div className="flex shrink-0 justify-end gap-2 border-t border-[var(--border-default)] px-5 py-3">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
