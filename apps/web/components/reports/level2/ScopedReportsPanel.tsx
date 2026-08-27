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

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import {
  exportBuilderPdf,
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";

export type ScopedReportsScope =
  | { kind: "organization"; id: string }
  // US-209 — el nivel intermedio de ADR-037. `organizationId` va aparte porque
  // un portafolio no tiene branding propio: lo hereda de su organización, y sin
  // ella el PDF sale con el branding por defecto del inquilino.
  | { kind: "portfolio"; id: string; organizationId?: string }
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
      // Un `if/else` de dos ramas no admitía un tercer nivel sin que quedara
      // mandado como el de al lado, que es un reporte del scope equivocado y no
      // un error.
      const ambito: Record<string, string | undefined> =
        scope.kind === "organization"
          ? { organization_id: scope.id }
          : scope.kind === "portfolio"
            ? { portfolio_id: scope.id, organization_id: scope.organizationId }
            : { program_id: scope.id };
      const body = {
        level: 2,
        window_days: 30,
        ...ambito,
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
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-4 text-[13px] text-[var(--text-tertiary)]">
          {emptyHint ??
            "Sin plantillas Nivel 2 configuradas. La plantilla seed L2-ORG debería estar instalada."}
        </div>
      ) : (
        <ul className="space-y-2">
          {templates.map((t) => (
            <li
              key={t.id}
              className="flex items-center justify-between rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-3.5 shadow-[var(--relieve-isla)]"
            >
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--text-primary)]">
                  <Icono nombre="file-text" size={15} className="text-[var(--text-faint)]" />
                  {t.name}
                </p>
                {t.description && (
                  <p className="mt-0.5 text-[11.5px] text-[var(--text-tertiary)]">{t.description}</p>
                )}
                <p className="mt-0.5 text-[10.5px] text-[var(--text-faint)]">
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
                <Icono nombre="download" size={14} /> PDF
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
