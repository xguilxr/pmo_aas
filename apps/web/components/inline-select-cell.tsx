"use client";

// Fase 2 (docs/archive/project-management/UIUX-ANALYSIS-Sprint35.md): celda con edición inline "on-click". Muestra
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

/**
 * US-178: edición inline de texto (p.ej. título RAID). Muestra el valor;
 * al hacer click se vuelve input. Guarda en blur/Enter; Escape cancela.
 */
export function InlineTextCell({
  value,
  onChange,
  placeholder = "—",
  title,
  ariaLabel,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  title?: string;
  ariaLabel?: string;
  className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && ref.current) {
      ref.current.focus();
      ref.current.select();
    }
  }, [editing]);

  function commit() {
    setEditing(false);
    const next = draft.trim();
    if (next && next !== value) onChange(next);
    else setDraft(value);
  }

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => {
          setDraft(value);
          setEditing(true);
        }}
        title={title ? `${title} (clic para editar)` : "Clic para editar"}
        aria-label={ariaLabel}
        className={cn(
          "w-full max-w-full truncate rounded px-1 py-0.5 text-left hover:bg-[var(--color-subtle)] focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-strong)]",
          className,
        )}
      >
        {value ? (
          value
        ) : (
          <span className="text-[var(--color-tertiary)]">{placeholder}</span>
        )}
      </button>
    );
  }

  return (
    <input
      ref={ref}
      value={draft}
      title={title}
      aria-label={ariaLabel}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        } else if (e.key === "Escape") {
          e.preventDefault();
          setDraft(value);
          setEditing(false);
        }
      }}
      className="w-full rounded border border-[var(--border-default)] bg-[var(--color-surface)] px-1 py-0.5 text-sm text-[var(--color-primary)] focus:outline-none"
    />
  );
}

/**
 * US-178: edición inline de fecha (date input). null/"" = sin fecha.
 * Guarda en cada cambio; muestra "—" cuando vacío.
 */
export function InlineDateCell({
  value,
  onChange,
  title,
  ariaLabel,
}: {
  value: string | null;
  onChange: (value: string | null) => void;
  title?: string;
  ariaLabel?: string;
}) {
  const [editing, setEditing] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && ref.current) {
      ref.current.focus();
      const el = ref.current as HTMLInputElement & { showPicker?: () => void };
      try {
        el.showPicker?.();
      } catch {
        /* ignore */
      }
    }
  }, [editing]);

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        title={title ? `${title} (clic para editar)` : "Clic para editar"}
        aria-label={ariaLabel}
        className="w-full max-w-full truncate rounded px-1 py-0.5 text-left tabular-nums hover:bg-[var(--color-subtle)] focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-strong)]"
      >
        {value ? (
          value
        ) : (
          <span className="text-[var(--color-tertiary)]">—</span>
        )}
      </button>
    );
  }

  return (
    <input
      ref={ref}
      type="date"
      value={value ?? ""}
      title={title}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.value || null)}
      onBlur={() => setEditing(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape" || e.key === "Enter") {
          e.preventDefault();
          setEditing(false);
        }
      }}
      className="rounded border border-[var(--border-default)] bg-[var(--color-surface)] px-1 py-0.5 text-xs text-[var(--color-secondary)] focus:outline-none"
    />
  );
}
