"use client";

/**
 * US-129 — UI Reportes Nivel 2 (Programa).
 *
 * Variante para programas. Mismo patrón que la organización pero
 * pasa `program_id` al export.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Download, FileText, Network } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  exportBuilderPdf,
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";

export default function ProgramReportsPage() {
  const params = useParams<{ id: string }>();
  const programId = params?.id ?? "";

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
      const blob = await exportBuilderPdf(tpl.id, {
        program_id: programId,
        level: 2,
        window_days: 30,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `programa-${programId}-${tpl.code}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar PDF");
    } finally {
      setExportingId(null);
    }
  }

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

      {error && <Banner variant="danger">{error}</Banner>}

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      ) : templates.length === 0 ? (
        <div className="rounded border border-dashed border-zinc-300 p-4 text-sm text-zinc-500">
          Sin plantillas Nivel 2 configuradas.
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
