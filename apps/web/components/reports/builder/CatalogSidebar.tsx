"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import type { ReportSection, SectionCategory } from "@/lib/api/report-builder";

const CATEGORY_LABEL: Record<SectionCategory, string> = {
  HDR: "Header",
  EST: "Estado",
  AVN: "Avance",
  PLN: "Plan",
  RAID: "RAID",
  EQP: "Equipo",
  NAR: "Narrativa",
  KPI: "KPI",
  PRT: "Portafolio",
};

type Props = {
  sections: ReportSection[];
  /** Códigos ya agregados al canvas, para deshabilitar/marcar. */
  selectedCodes: string[];
  onAdd: (code: string) => void;
};

/** US-124 — catálogo lateral filtrable por categoría y texto libre. */
export function CatalogSidebar({ sections, selectedCodes, onAdd }: Props) {
  const [query, setQuery] = useState("");
  const [activeCat, setActiveCat] = useState<SectionCategory | "ALL">("ALL");

  const categories = useMemo(
    () => Array.from(new Set(sections.map((s) => s.category))) as SectionCategory[],
    [sections]
  );

  const filtered = sections.filter((s) => {
    if (activeCat !== "ALL" && s.category !== activeCat) return false;
    if (query) {
      const q = query.toLowerCase();
      if (!s.name.toLowerCase().includes(q) && !s.code.toLowerCase().includes(q)) {
        return false;
      }
    }
    return true;
  });

  return (
    <aside className="flex h-full w-72 flex-col border-r border-[var(--border-default)] bg-[var(--color-subtle)] p-3.5">
      <h2 className="mb-2.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
        Catálogo
      </h2>
      <div className="relative mb-2.5">
        <Icono
          nombre="search"
          size={14}
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
        />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar sección…"
          className="pl-7.5"
        />
      </div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => setActiveCat("ALL")}
          className={cn(
            "inline-flex h-6 items-center rounded-full border px-2.5 text-[11.5px] font-medium transition-colors",
            activeCat === "ALL"
              ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-inverse)]"
              : "border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]",
          )}
        >
          Todas
        </button>
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setActiveCat(c)}
            className={cn(
              "inline-flex h-6 items-center rounded-full border px-2.5 text-[11.5px] font-medium transition-colors",
              activeCat === c
                ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-inverse)]"
                : "border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]",
            )}
          >
            {CATEGORY_LABEL[c] ?? c}
          </button>
        ))}
      </div>

      <ul className="flex-1 space-y-1.5 overflow-y-auto">
        {filtered.map((s) => {
          const already = selectedCodes.includes(s.code);
          return (
            <li
              key={s.id}
              className="flex items-start justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] px-2.5 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                  <span className="text-[var(--text-faint)]">{s.code}</span> · {s.name}
                </p>
                {s.description && (
                  <p className="line-clamp-2 text-[11.5px] text-[var(--text-tertiary)]">{s.description}</p>
                )}
              </div>
              <Button
                type="button"
                size="sm"
                variant={already ? "ghost" : "secondary"}
                onClick={() => onAdd(s.code)}
                disabled={already}
                title={already ? "Ya está en el canvas" : "Agregar al canvas"}
              >
                <Icono nombre="plus" size={14} />
              </Button>
            </li>
          );
        })}
        {filtered.length === 0 && (
          <li className="rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] p-3 text-center text-[12px] text-[var(--text-tertiary)]">
            Sin resultados.
          </li>
        )}
      </ul>
    </aside>
  );
}
