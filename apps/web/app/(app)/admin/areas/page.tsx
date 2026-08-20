"use client";

// ENH-086 — rediseño admin Áreas. 2 tabs:
//  - Áreas y Equipos: reutiliza AreasAndTeamsPanel (ENH-081) sobre catálogos
//    tenant (áreas, equipos operativos, roles de proyecto).
//  - Personas: catálogo tenant de actors enriquecidos (US-114).
// US-170: el catálogo se filtra por organización.
// US-205: ese filtro ya no es de esta pantalla — sale del switcher del header,
//   igual que en el resto de la aplicación. El select local se retira.

import { useState } from "react";

import { AreasAndTeamsPanel } from "@/components/directory/AreasAndTeamsPanel";
import { TenantActorsPanel } from "@/components/directory/TenantActorsPanel";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { cn } from "@/lib/cn";
import { useOrganizacionActiva } from "@/components/organizacion-activa";

type Tab = "catalog" | "people";

export default function AdminAreasPage() {
  const [tab, setTab] = useState<Tab>("catalog");
  // `/admin/areas` no agrega, así que `efectiva` es siempre una organización
  // concreta: el catálogo nunca se queda sin a qué organización pertenecer.
  const { efectiva: selectedOrgId, vacio } = useOrganizacionActiva();

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
          Áreas y personas (catálogo por organización)
        </h1>
        <p className="text-sm text-[var(--color-tertiary)]">
          Administra áreas funcionales, equipos operativos, roles de proyecto y
          el directorio global de personas del tenant.
        </p>
      </header>

      {/* DIS-03 — sin organizaciones no hay catálogo que administrar, y las
          áreas y los equipos cuelgan de una. Se dice en vez de pintar los dos
          paneles vacíos, que se leen como un error de carga. */}
      {vacio && (
        <p className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-6 text-center text-sm text-[var(--color-tertiary)]">
          Este inquilino no tiene organizaciones todavía. Crea la primera en{" "}
          <a
            className="underline underline-offset-2 hover:text-[var(--color-primary)]"
            href="/admin/organizations"
          >
            Admin → Organizaciones
          </a>{" "}
          y aquí podrás administrar sus áreas, equipos y personas.
        </p>
      )}

      {!vacio && (
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
          {tab === "catalog" ? (
            <AreasAndTeamsPanel organizationId={selectedOrgId || undefined} />
          ) : (
            <TenantActorsPanel />
          )}
        </div>
        </section>
      )}
    </div>
  );
}
