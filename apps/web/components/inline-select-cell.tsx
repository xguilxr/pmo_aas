"use client";

// Fase 2 (UIUX-ANALYSIS-Sprint35): celda con edición inline "on-click". Muestra
// el valor como texto y, al hacer click, se convierte en un <select> enfocado
// (intenta abrir el dropdown donde el browser lo soporta). Reduce el ruido
// visual de tener selects siempre-on en cada fila.
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";

export type InlineOption = { value: string; label: string };

export function InlineSelectCell({
  value,
  options,
  onChange,
  placeholder = "—",
  title,
  ariaLabel,
}: {
  value: string;
  options: InlineOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  title?: string;
  ariaLabel?: string;
}) {
  const [editing, setEditing] = useState(false);
  const ref = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    if (!editing || !ref.current) return;
    ref.current.focus();
    // Auto-abre el dropdown donde esté disponible (Chrome 121+); si no, queda
    // enfocado y un segundo click lo abre.
    const el = ref.current as HTMLSelectElement & { showPicker?: () => void };
    try {
      el.showPicker?.();
    } catch {
      /* requiere gesto del usuario en algunos browsers — ignoramos */
    }
  }, [editing]);

  const current = options.find((o) => o.value === value);

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        title={title ? `${title} (clic para editar)` : "Clic para editar"}
        aria-label={ariaLabel}
        className="w-full max-w-full truncate rounded px-1 py-0.5 text-left hover:bg-[var(--color-subtle)] focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-strong)]"
      >
        {current && current.value !== "" ? (
          current.label
        ) : (
          <span className="text-[var(--color-tertiary)]">{placeholder}</span>
        )}
      </button>
    );
  }

  return (
    <select
      ref={ref}
      value={value}
      title={title}
      aria-label={ariaLabel}
      onChange={(e) => {
        onChange(e.target.value);
        setEditing(false);
      }}
      onBlur={() => setEditing(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          setEditing(false);
        }
      }}
      className={cn(
        "rounded border border-[var(--border-default)] bg-[var(--color-surface)] px-1 py-0.5 text-xs text-[var(--color-secondary)] focus:outline-none",
      )}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
