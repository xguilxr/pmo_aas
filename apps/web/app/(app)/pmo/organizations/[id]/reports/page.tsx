"use client";

/**
 * US-129 + US-136 — Reportes Nivel 2 (Organización).
 *
 * Este page sigue funcionando como deep-link
 * (`/pmo/organizations/[id]/reports`) pero ahora el contenido vive
 * en `<ScopedReportsPanel>`. El detalle de la organización (US-136)
 * monta el mismo componente como tab.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Building2 } from "lucide-react";

import { ScopedReportsPanel } from "@/components/reports/level2/ScopedReportsPanel";

export default function OrgReportsPage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      <header>
        <Link
          href={`/pmo/organizations/${orgId}`}
          className="mb-1 inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900"
        >
          <ArrowLeft className="h-3 w-3" /> Volver a la organización
        </Link>
        <div className="flex items-center gap-2">
          <Building2 className="h-6 w-6 text-zinc-700" />
          <h1 className="text-2xl font-semibold text-zinc-900">
            Reportes de la Organización (Nivel 2)
          </h1>
        </div>
        <p className="mt-1 text-sm text-zinc-500">
          Plantillas Nivel 2 aplicadas con scope filtrado a esta
          organización.
        </p>
      </header>

      <ScopedReportsPanel scope={{ kind: "organization", id: orgId }} />
    </div>
  );
}
