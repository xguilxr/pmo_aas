"use client";

/**
 * ENH-120 — Rediseño tenant-wide de Reportes.
 *
 * Tabs: PMO | Organizaciones | Programas | Proyectos.
 * - PMO (US-144): cascarón con generación + historial.
 * - Organizaciones (US-145): cascarón + filtro org.
 * - Programas (US-146): cascarón + filtros org+programa.
 * - Proyectos (ENH-120): listado actual + 4 fixes (folio, tipo, período,
 *   filtra drafts, link al detail, label "Builder").
 */
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Building2, Download, FileText, Layers, Loader2, Network } from "lucide-react";

import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  exportBuilderPdf,
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";
import { listTenantReports, type TenantReport } from "@/lib/api/tenant-cross";

type TenantReportsTab = "pmo" | "organization" | "program" | "projects";

const TABS: Array<{ v: TenantReportsTab; label: string; icon: React.ReactNode }> = [
  { v: "pmo", label: "PMO", icon: <Layers className="h-3.5 w-3.5" aria-hidden /> },
  {
    v: "organization",
    label: "Organizaciones",
    icon: <Building2 className="h-3.5 w-3.5" aria-hidden />,
  },
  {
    v: "program",
    label: "Programas",
    icon: <Network className="h-3.5 w-3.5" aria-hidden />,
  },
  {
    v: "projects",
    label: "Proyectos",
    icon: <FileText className="h-3.5 w-3.5" aria-hidden />,
  },
];

export default function TenantReportsPage() {
  const search = useSearchParams();
  const tabParam = search?.get("tab") as TenantReportsTab | null;
  const activeTab: TenantReportsTab = useMemo(
    () => (TABS.find((t) => t.v === tabParam) ? (tabParam as TenantReportsTab) : "pmo"),
    [tabParam],
  );

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Reportes
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Reportes a nivel PMO, organización, programa y proyecto.
        </p>
      </header>

      <div
        role="tablist"
        aria-label="Niveles de reportes"
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
      >
        {TABS.map((opt) => {
          const active = activeTab === opt.v;
          const href = opt.v === "pmo" ? "/pmo/reports" : `/pmo/reports?tab=${opt.v}`;
          return (
            <Link
              key={opt.v}
              href={href}
              role="tab"
              aria-selected={active}
              className={`inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] px-4 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]"
              }`}
            >
              {opt.icon}
              {opt.label}
            </Link>
          );
        })}
      </div>

      {activeTab === "pmo" ? (
        <PmoScopePlaceholder />
      ) : activeTab === "organization" ? (
        <OrgScopePlaceholder />
      ) : activeTab === "program" ? (
        <ProgramScopePlaceholder />
      ) : (
        <ProjectsReportsView />
      )}
    </div>
  );
}

// US-144 — Tab PMO. Generación + (placeholder) historial.
function PmoScopePlaceholder() {
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listBuilderTemplates({ level: 1 })
      .then((all) => {
        if (!cancelled) setTemplates(all);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar plantillas");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function generatePmoReport(tpl: ReportBuilderTemplate) {
    setExporting(tpl.id);
    setError(null);
    try {
      const blob = await exportBuilderPdf(tpl.id, {
        level: 1,
        window_days: 30,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pmo-status-${tpl.code}-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el reporte");
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="space-y-5">
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
        <div className="flex items-start gap-3">
          <Layers className="mt-0.5 h-5 w-5 text-[var(--color-accent)]" aria-hidden />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              Reporte Status PMO
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
              Genera el reporte de status de toda la PMO (sin filtros). El reporte
              se descarga directo como PDF.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-14 w-full" />
          </div>
        ) : templates.length === 0 ? (
          <p className="mt-4 text-xs italic text-[var(--text-tertiary)]">
            Sin plantillas Nivel 1 disponibles. Verifica el seed de
            `report_builder_templates`.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {templates.map((tpl) => (
              <li
                key={tpl.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                    {tpl.name}
                  </p>
                  <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                    {tpl.section_codes.length} secciones · Modo {tpl.composition_mode}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => generatePmoReport(tpl)}
                  loading={exporting === tpl.id}
                  disabled={exporting !== null}
                >
                  {exporting === tpl.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  ) : (
                    <Download className="h-3.5 w-3.5" aria-hidden />
                  )}
                  Descargar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Cascarón: historial scoped a PMO no persiste todavía. Cuando la
          estructura final del reporte esté definida (sesión owner aparte),
          aquí va una tabla con los descargados anteriormente. */}
      <section className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-6 text-center">
        <p className="text-xs text-[var(--text-tertiary)]">
          <strong className="text-[var(--text-secondary)]">Historial:</strong>{" "}
          se habilitará cuando se defina la estructura final del reporte PMO
          (cascarón aprobado por owner — pendiente sesión de diseño).
        </p>
      </section>
    </div>
  );
}

// US-145 (cascarón pendiente).
function OrgScopePlaceholder() {
  return (
    <section className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-8 text-center">
      <Building2 className="mx-auto h-8 w-8 text-[var(--color-tertiary)]" aria-hidden />
      <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">
        Reportes por Organización
      </p>
      <p className="mt-1 text-xs text-[var(--text-tertiary)]">
        Cascarón pendiente (US-145). Aquí va el filtro de organización + panel
        de generación + historial scoped.
      </p>
    </section>
  );
}

// US-146 (cascarón pendiente).
function ProgramScopePlaceholder() {
  return (
    <section className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-8 text-center">
      <Network className="mx-auto h-8 w-8 text-[var(--color-tertiary)]" aria-hidden />
      <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">
        Reportes por Programa
      </p>
      <p className="mt-1 text-xs text-[var(--text-tertiary)]">
        Cascarón pendiente (US-146). Aquí van los filtros org + programa + panel
        de generación + historial scoped.
      </p>
    </section>
  );
}

// ENH-120: tab Proyectos = contenido actual + 4 fixes.
function ProjectsReportsView() {
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  const [rows, setRows] = useState<TenantReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenantReports(filter)
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <>
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <TenantCrossFilters value={filter} onChange={setFilter} />
        <p className="mt-2 text-[11px] text-[var(--text-tertiary)]">
          Sólo se muestran reportes guardados (no borradores).
        </p>
      </section>

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin reportes guardados para los filtros actuales.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <th className="px-3 py-2 font-medium">Folio</th>
                <th className="px-3 py-2 font-medium">Título</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium">Período</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2 font-medium">Proyecto</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                >
                  <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
                    {r.folio}
                  </td>
                  <td className="px-3 py-2">
                    {/* ENH-120: link al detail del reporte específico, no al listing del proyecto */}
                    <Link
                      href={`/pmo/projects/${r.project_id}/reports/${r.id}`}
                      className="text-[var(--color-primary)] hover:underline"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    {/* ENH-120: label "Builder" para reportes de US-140 */}
                    <Badge
                      variant={r.report_type === "Builder" ? "info" : "neutral"}
                    >
                      {r.report_type ?? "—"}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.period ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.status}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/pmo/projects/${r.project_id}`}
                      className="text-xs text-[var(--color-accent)] hover:underline"
                      title={r.project_name}
                    >
                      <span className="font-mono">{r.project_folio}</span>
                      <span className="ml-1 text-[var(--color-secondary)]">
                        — {r.project_name}
                      </span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
