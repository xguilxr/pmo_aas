"use client";

/**
 * US-136 / US-137 — Panel reusable de Reportes Nivel 2.
 *
 * Lista plantillas Nivel 2 + export PDF con scope filtrado a una
 * organización o programa. Se monta como página standalone
 * (`/pmo/organizations/[id]/reports`, `/pmo/programs/[id]/reports`)
 * y también como tab dentro del detalle (US-136 / US-137).
 */
import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  exportBuilderPdf,
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";

export type ScopedReportsScope =
  | { kind: "organization"; id: string }
  | { kind: "program"; id: string };

type Props = {
  scope: ScopedReportsScope;
  /** Texto descriptivo encima de la lista. */
  emptyHint?: string;
};

export function ScopedReportsPanel({ scope, emptyHint }: Props) {
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const all = await listBuilderTemplates({ level: 2 });
        if (!cancelled) setTemplates(all);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function exportPdf(tpl: ReportBuilderTemplate) {
    setExportingId(tpl.id);
    try {
      const body = {
        level: 2,
        window_days: 30,
        ...(scope.kind === "organization"
          ? { organization_id: scope.id }
          : { program_id: scope.id }),
      } as Parameters<typeof exportBuilderPdf>[1];
      const blob = await exportBuilderPdf(tpl.id, body);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${scope.kind}-${scope.id}-${tpl.code}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar PDF");
    } finally {
      setExportingId(null);
    }
  }

  return (
    <div className="space-y-3">
      {error && <Banner variant="danger">{error}</Banner>}

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      ) : templates.length === 0 ? (
        <div className="rounded border border-dashed border-zinc-300 p-4 text-sm text-zinc-500">
          {emptyHint ??
            "Sin plantillas Nivel 2 configuradas. La plantilla seed L2-ORG debería estar instalada."}
        </div>
      ) : (
        <ul className="space-y-2">
          {templates.map((t) => (
            <li
              key={t.id}
              className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white p-3 shadow-sm"
            >
              <div>
                <p className="text-sm font-medium text-zinc-900">
                  <FileText className="mr-1 inline h-4 w-4 text-zinc-400" />
                  {t.name}
                </p>
                {t.description && (
                  <p className="mt-0.5 text-xs text-zinc-500">{t.description}</p>
                )}
                <p className="mt-0.5 text-[10px] text-zinc-400">
                  Código: {t.code} · {t.section_codes.length} secciones · Modo{" "}
                  {t.composition_mode}
                </p>
              </div>
              <Button
                size="sm"
                variant="primary"
                onClick={() => exportPdf(t)}
                loading={exportingId === t.id}
                disabled={!!exportingId}
              >
                <Download className="mr-1 h-3.5 w-3.5" /> PDF
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
