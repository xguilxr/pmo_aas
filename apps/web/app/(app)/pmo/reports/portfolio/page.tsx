"use client";

/**
 * US-128 — Módulo UI Reportes Nivel 1 (PMO Portafolio).
 *
 * Ruta `/pmo/reports/portfolio`. Listado de plantillas L1 disponibles
 * + acciones (generar PDF, abrir en builder). Permisos: solo roles
 * PMO / admin (chequeo a nivel de UI; el endpoint backend valida con
 * el tenant del JWT).
 *
 * v1.0: no se persiste un "histórico de reportes generados" para el
 * builder (la tabla `reports` es para reportes operativos). El export
 * se descarga directo al cliente.
 */
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Download, FileText, LayoutDashboard, Loader2, Plus, Sparkles } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  exportBuilderPdf,
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";
import { getStoredUser } from "@/lib/auth-storage";

const ADMIN_ROLES = new Set([
  "admin",
  "Administrador",
  "PMO Manager",
  "pmo",
]);

function userIsAllowed(): boolean {
  const u = getStoredUser();
  if (!u) return false;
  if (u.is_superadmin) return true;
  const roles = (u.roles ?? []) as string[];
  return roles.some((r) => ADMIN_ROLES.has(r));
}

export default function PortfolioReportsPage() {
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const allowed = useMemo(() => userIsAllowed(), []);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const all = await listBuilderTemplates({ level: 1 });
        if (!cancelled) setTemplates(all);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "No se pudo cargar");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [allowed]);

  async function exportPdf(tpl: ReportBuilderTemplate) {
    setExportingId(tpl.id);
    try {
      const blob = await exportBuilderPdf(tpl.id, {
        level: 1,
        window_days: 30,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `portafolio-${tpl.code}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el PDF");
    } finally {
      setExportingId(null);
    }
  }

  if (!allowed) {
    return (
      <div className="mx-auto max-w-3xl space-y-3 p-6">
        <Banner variant="danger">
          Acceso restringido. Solo los roles PMO / admin del tenant pueden
          consultar los reportes de portafolio.
        </Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      {/* ENH-115: breadcrumb Tenant > Reportes > Portafolio */}
      <Breadcrumb
        items={[
          { href: "/pmo/reports", label: "Reportes" },
          { label: "Portafolio (PMO)" },
        ]}
      />
      <header className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="h-6 w-6 text-zinc-700" />
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900">
              Reportes de Portafolio (Nivel 1)
            </h1>
            <p className="mt-0.5 text-sm text-zinc-500">
              Reportes agregados de todos los proyectos del tenant.
            </p>
          </div>
        </div>
      </header>

      {error && <Banner variant="danger">{error}</Banner>}

      <section>
        <h2 className="mb-2 text-sm font-semibold text-zinc-700">
          Plantillas disponibles
        </h2>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-14" />
            <Skeleton className="h-14" />
          </div>
        ) : templates.length === 0 ? (
          <div className="rounded border border-dashed border-zinc-300 p-4 text-sm text-zinc-500">
            No hay plantillas Nivel 1 configuradas. La plantilla seed{" "}
            <code>L1-PORTAFOLIO</code> debería estar instalada.
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
                    {t.is_seed && (
                      <span className="ml-2 rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-600">
                        seed
                      </span>
                    )}
                  </p>
                  {t.description && (
                    <p className="mt-0.5 text-xs text-zinc-500">{t.description}</p>
                  )}
                  <p className="mt-0.5 text-[10px] text-zinc-400">
                    Código: {t.code} · {t.section_codes.length} secciones · Modo{" "}
                    {t.composition_mode}
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => exportPdf(t)}
                    loading={exportingId === t.id}
                    disabled={!!exportingId}
                  >
                    <Download className="mr-1 h-3.5 w-3.5" /> PDF
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="border-t border-zinc-200 pt-4">
        <h2 className="mb-2 text-sm font-semibold text-zinc-700">
          Crear reporte custom
        </h2>
        <p className="mb-2 text-xs text-zinc-500">
          Construye un reporte de portafolio desde cero o sobre una plantilla
          (usa el builder de proyecto y cambia el level a 1 al guardar).
        </p>
        <div className="flex gap-2">
          <Link
            href="/pmo/projects"
            className="inline-flex items-center gap-1 rounded-md bg-zinc-900 px-3 py-1.5 text-xs text-white hover:bg-zinc-700"
          >
            <Plus className="h-3.5 w-3.5" /> Abrir un proyecto y usar el builder
          </Link>
          <Link
            href="/pmo/reports"
            className="inline-flex items-center gap-1 rounded-md border border-zinc-300 px-3 py-1.5 text-xs text-zinc-700 hover:bg-zinc-50"
          >
            <Sparkles className="h-3.5 w-3.5" /> Ver reportes operativos del tenant
          </Link>
        </div>
      </section>
    </div>
  );
}
