"use client";

import { useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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
    <aside className="flex h-full w-72 flex-col border-r border-zinc-200 bg-zinc-50 p-3">
      <h2 className="mb-2 text-sm font-semibold text-zinc-700">Catálogo</h2>
      <div className="relative mb-2">
        <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar sección…"
          className="pl-7 text-sm"
        />
      </div>
      <div className="mb-3 flex flex-wrap gap-1">
        <button
          type="button"
          onClick={() => setActiveCat("ALL")}
          className={`rounded-full px-2 py-0.5 text-xs ${
            activeCat === "ALL"
              ? "bg-zinc-900 text-white"
              : "bg-white text-zinc-600 ring-1 ring-zinc-200"
          }`}
        >
          Todas
        </button>
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setActiveCat(c)}
            className={`rounded-full px-2 py-0.5 text-xs ${
              activeCat === c
                ? "bg-zinc-900 text-white"
                : "bg-white text-zinc-600 ring-1 ring-zinc-200"
            }`}
          >
            {CATEGORY_LABEL[c] ?? c}
          </button>
        ))}
      </div>

      <ul className="flex-1 space-y-1 overflow-y-auto">
        {filtered.map((s) => {
          const already = selectedCodes.includes(s.code);
          return (
            <li
              key={s.id}
              className="flex items-start justify-between gap-2 rounded border border-zinc-200 bg-white px-2 py-1.5"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-zinc-800">
                  <span className="text-zinc-400">{s.code}</span> · {s.name}
                </p>
                {s.description && (
                  <p className="line-clamp-2 text-xs text-zinc-500">{s.description}</p>
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
                <Plus className="h-3 w-3" />
              </Button>
            </li>
          );
        })}
        {filtered.length === 0 && (
          <li className="rounded border border-dashed border-zinc-300 p-3 text-center text-xs text-zinc-500">
            Sin resultados.
          </li>
        )}
      </ul>
    </aside>
  );
}
