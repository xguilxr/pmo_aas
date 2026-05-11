"use client";

// ENH-086 — rediseño admin Áreas. 2 tabs:
//  - Áreas y Equipos: reutiliza AreasAndTeamsPanel (ENH-081) sobre catálogos
//    tenant (áreas, equipos operativos, roles de proyecto).
//  - Personas: catálogo tenant de actors enriquecidos (US-114).

import { useState } from "react";

import { AreasAndTeamsPanel } from "@/components/directory/AreasAndTeamsPanel";
import { TenantActorsPanel } from "@/components/directory/TenantActorsPanel";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { cn } from "@/lib/cn";

type Tab = "catalog" | "people";

export default function AdminAreasPage() {
  const [tab, setTab] = useState<Tab>("catalog");

  return (
    <div className="space-y-4 p-4">
      <Breadcrumb
        items={[
          { label: "Admin", href: "/admin" },
          { label: "Áreas y personas" },
        ]}
      />
      <header>
        <h1 className="text-xl font-semibold text-[var(--color-primary)]">
          Áreas y personas (catálogo tenant)
        </h1>
        <p className="text-sm text-[var(--color-tertiary)]">
          Administra áreas funcionales, equipos operativos, roles de proyecto y
          el directorio global de personas del tenant.
        </p>
      </header>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="border-b border-[var(--border-default)] p-4">
          <div
            role="radiogroup"
            aria-label="Tab"
            className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
          >
            {(
              [
                { v: "catalog", label: "Áreas y Equipos" },
                { v: "people", label: "Personas" },
              ] as const
            ).map((opt) => {
              const active = tab === opt.v;
              return (
                <button
                  key={opt.v}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setTab(opt.v)}
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
          {tab === "catalog" ? <AreasAndTeamsPanel /> : <TenantActorsPanel />}
        </div>
      </section>
    </div>
  );
}
