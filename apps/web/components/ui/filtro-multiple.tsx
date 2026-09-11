"use client";

/**
 * FASE-5 (revamp v2, US-A) — dropdown con checkmarks, selección múltiple.
 * Wireframe W6: "filtros como dropdown con checkmarks" en vez de los `Chip`
 * sueltos que usaba `/pmo/projects`.
 */
import { useEffect, useRef, useState } from "react";

import { Checkbox } from "@/components/ui/checkbox";
import { Icono } from "@/components/ui/icono";
import { cn } from "@/lib/cn";

export function FiltroMultiple({
  label,
  opciones,
  seleccion,
  onChange,
  className,
}: {
  label: string;
  opciones: { value: string; label: string }[];
  seleccion: string[];
  onChange: (values: string[]) => void;
  className?: string;
}) {
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    function onMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setAbierto(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setAbierto(false);
    }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [abierto]);

  function toggle(value: string) {
    onChange(
      seleccion.includes(value)
        ? seleccion.filter((v) => v !== value)
        : [...seleccion, value],
    );
  }

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={abierto}
        className={cn(
          "flex h-9 items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border-strong)]",
          "bg-[var(--color-surface)] px-3 text-[13px] text-[var(--color-primary)] shadow-[var(--hundido)]",
        )}
      >
        {label}
        {seleccion.length > 0 ? (
          <span className="font-mono text-[11.5px] text-[var(--color-accent)]">
            · {seleccion.length}
          </span>
        ) : null}
        <Icono nombre="chevron-down" size={14} className="text-[var(--text-faint)]" />
      </button>
      {abierto ? (
        <div
          role="listbox"
          aria-multiselectable
          aria-label={label}
          className="absolute left-0 top-[calc(100%+4px)] z-20 min-w-[200px] max-h-[280px] overflow-y-auto rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] py-1.5 shadow-[var(--relieve-isla)]"
        >
          <div className="flex items-center justify-between px-3 pb-1.5 text-[11px] text-[var(--text-tertiary)]">
            <button
              type="button"
              className="hover:text-[var(--color-accent)]"
              onClick={() => onChange(opciones.map((o) => o.value))}
            >
              Todos
            </button>
            <button
              type="button"
              className="hover:text-[var(--color-accent)]"
              onClick={() => onChange([])}
            >
              Ninguno
            </button>
          </div>
          {opciones.map((o) => (
            <label
              key={o.value}
              role="option"
              aria-selected={seleccion.includes(o.value)}
              className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-[13px] text-[var(--color-primary)] hover:bg-[var(--color-subtle)]"
            >
              <Checkbox
                checked={seleccion.includes(o.value)}
                onChange={() => toggle(o.value)}
              />
              {o.label}
            </label>
          ))}
        </div>
      ) : null}
    </div>
  );
}
