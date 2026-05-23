"use client";

/**
 * US-129 + US-137 — Reportes Nivel 2 (Programa).
 *
 * Deep-link a la vista que también se monta como tab dentro del
 * detalle del programa (`?tab=reports`).
 */
import { useParams } from "next/navigation";
import { Network } from "lucide-react";

import { Breadcrumb } from "@/components/ui/breadcrumb";
import { ScopedReportsPanel } from "@/components/reports/level2/ScopedReportsPanel";

export default function ProgramReportsPage() {
  const params = useParams<{ id: string }>();
  const programId = params?.id ?? "";

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      {/* ENH-115: breadcrumb Tenant > Programa > Reportes */}
      <Breadcrumb
        items={[
          { href: "/pmo/reports", label: "Reportes" },
          { href: `/pmo/programs/${programId}`, label: "Programa" },
          { label: "Reportes del programa" },
        ]}
      />
      <header>
        <div className="flex items-center gap-2">
          <Network className="h-6 w-6 text-zinc-700" />
          <h1 className="text-2xl font-semibold text-zinc-900">
            Reportes del Programa (Nivel 2)
          </h1>
        </div>
        <p className="mt-1 text-sm text-zinc-500">
          Plantillas Nivel 2 con scope filtrado a este programa.
        </p>
      </header>

      <ScopedReportsPanel scope={{ kind: "program", id: programId }} />
    </div>
  );
}
