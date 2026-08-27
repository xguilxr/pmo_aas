"use client";

/**
 * US-129 + US-136 — Reportes Nivel 2 (Organización).
 *
 * Este page sigue funcionando como deep-link
 * (`/pmo/organizations/[id]/reports`) pero ahora el contenido vive
 * en `<ScopedReportsPanel>`. El detalle de la organización (US-136)
 * monta el mismo componente como tab.
 */
import { useParams } from "next/navigation";

import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Icono } from "@/components/ui/icono";
import { ScopedReportsPanel } from "@/components/reports/level2/ScopedReportsPanel";

export default function OrgReportsPage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      {/* ENH-115: breadcrumb consistente Tenant > Organización > Reportes */}
      <Breadcrumb
        items={[
          { href: "/pmo/reports", label: "Reportes" },
          { href: `/pmo/organizations/${orgId}`, label: "Organización" },
          { label: "Reportes de la organización" },
        ]}
      />
      <header>
        <div className="flex items-center gap-2">
          <Icono nombre="building" size={20} className="text-[var(--text-secondary)]" />
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">
            Reportes de la Organización (Nivel 2)
          </h1>
        </div>
        <p className="mt-1 text-sm text-[var(--text-tertiary)]">
          Plantillas Nivel 2 aplicadas con scope filtrado a esta
          organización.
        </p>
      </header>

      <ScopedReportsPanel scope={{ kind: "organization", id: orgId }} />
    </div>
  );
}
