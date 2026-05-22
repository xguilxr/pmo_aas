"use client";

/**
 * US-129 + US-137 — Reportes Nivel 2 (Programa).
 *
 * Deep-link a la vista que también se monta como tab dentro del
 * detalle del programa (`?tab=reports`).
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Network } from "lucide-react";

import { ScopedReportsPanel } from "@/components/reports/level2/ScopedReportsPanel";

export default function ProgramReportsPage() {
  const params = useParams<{ id: string }>();
  const programId = params?.id ?? "";

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      <header>
        <Link
          href={`/pmo/programs/${programId}`}
          className="mb-1 inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900"
        >
          <ArrowLeft className="h-3 w-3" /> Volver al programa
        </Link>
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
