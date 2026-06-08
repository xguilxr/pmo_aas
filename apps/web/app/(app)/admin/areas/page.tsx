"use client";

// ENH-086 — rediseño admin Áreas. 2 tabs:
//  - Áreas y Equipos: reutiliza AreasAndTeamsPanel (ENH-081) sobre catálogos
//    tenant (áreas, equipos operativos, roles de proyecto).
//  - Personas: catálogo tenant de actors enriquecidos (US-114).
// US-170: selector de organización al top — filtra catálogo por org.

import { useEffect, useState } from "react";

import { AreasAndTeamsPanel } from "@/components/directory/AreasAndTeamsPanel";
import { TenantActorsPanel } from "@/components/directory/TenantActorsPanel";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { cn } from "@/lib/cn";
import { listOrganizations, type Organization } from "@/lib/api/organizations";

type Tab = "catalog" | "people";

export default function AdminAreasPage() {
  const [tab, setTab] = useState<Tab>("catalog");
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");

  useEffect(() => {
    listOrganizations({ is_active: true })
      .then((data) => {
        setOrgs(data);
        if (data.length > 0) setSelectedOrgId(data[0].id);
      })
      .catch(() => {});
  }, []);

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

      {/* US-170: selector de organización */}
      {orgs.length > 0 && (
        <div className="flex items-center gap-3">
          <label htmlFor="org-selector" className="text-sm font-medium text-[var(--color-secondary)]">
            Organización:
          </label>
          <select
            id="org-selector"
            value={selectedOrgId}
            onChange={(e) => setSelectedOrgId(e.target.value)}
            className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-1.5 text-sm"
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
      )}

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
    </div>
  );
}
