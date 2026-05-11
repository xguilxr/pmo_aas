"use client";

// ENH-080 — rediseño post-US-116. Solo 2 toggles: Directorio (US-116)
// y Áreas y Equipos (catálogos tenant: áreas, equipos, roles).

import { useParams } from "next/navigation";
import { useState } from "react";

import { DirectoryView } from "@/components/directory/DirectoryView";
import { AreasAndTeamsPanel } from "@/components/directory/AreasAndTeamsPanel";
import { cn } from "@/lib/cn";

type View = "directory" | "catalog";

export default function ProjectAreasPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [view, setView] = useState<View>("directory");

  return (
    <div className="space-y-4 p-4">
      <header>
        <h1 className="text-xl font-semibold text-[var(--color-primary)]">
          Áreas del proyecto
        </h1>
        <p className="text-sm text-[var(--color-tertiary)]">
          Directorio del proyecto + catálogos tenant (áreas, equipos
          operativos, roles).
        </p>
      </header>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="flex flex-wrap items-center gap-3 border-b border-[var(--border-default)] p-4">
          <div
            role="radiogroup"
            aria-label="Vista"
            className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
          >
            {(
              [
                { v: "directory", label: "Directorio" },
                { v: "catalog", label: "Áreas y Equipos" },
              ] as const
            ).map((opt) => {
              const active = view === opt.v;
              return (
                <button
                  key={opt.v}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setView(opt.v)}
                  className={cn(
                    "rounded-[var(--radius-sm)] px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                      : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="p-4">
          {view === "directory" ? (
            <DirectoryView projectId={projectId} />
          ) : (
            <AreasAndTeamsPanel />
          )}
        </div>
      </section>
    </div>
  );
}
