"use client";

/**
 * ENH-120 — Detail de un reporte específico.
 *
 * Vista mínima: iframe con el HTML del reporte renderizado por
 * `GET /reports/{id}/render-html`. Permite que el link desde el listing
 * tenant-wide (`/pmo/reports?tab=projects`) abra el reporte concreto.
 *
 * Mejorable a futuro (incluido en ENH-121): UX con metadata + acciones
 * de descarga PDF/HTML, regenerar, etc. Este page es el cascarón mínimo
 * que cierra el AC del link de la fila.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import { apiBase } from "@/lib/api";
import { getReport, type Report } from "@/lib/api/reports";

export default function ReportDetailPage() {
  const { id, reportId } = useParams<{ id: string; reportId: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getReport(reportId)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar el reporte");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reportId]);

  const htmlUrl = `${apiBase()}/api/v1/reports/${reportId}/render-html?refresh=${refreshKey > 0}&_=${refreshKey}`;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/pmo/projects/${id}`} className="hover:underline">
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/pmo/projects/${id}/reports`} className="hover:underline">
            Reportes
          </Link>
          <span className="mx-1">/</span>
          <span>Detalle</span>
        </nav>
        <Link
          href={`/pmo/projects/${id}/reports`}
          className="mt-2 inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
        >
          <Icono nombre="arrow-left" size={14} />
          Volver a Reportes
        </Link>
        {loading ? (
          <Skeleton className="mt-2 h-8 w-72" />
        ) : (
          <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
            <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              <Icono nombre="file-text" size={20} className="text-[var(--text-tertiary)]" />
              {report?.title ?? "Reporte"}
            </h1>
            <div className="flex flex-wrap items-center gap-2">
              {report?.generator ? (
                <Badge variant={report.generator === "builder" ? "info" : "neutral"}>
                  {report.generator === "builder"
                    ? "Builder"
                    : report.generator === "ai"
                    ? "Builder"
                    : report.generator}
                </Badge>
              ) : null}
              {report?.period ? <Badge variant="neutral">{report.period}</Badge> : null}
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setRefreshKey((k) => k + 1)}
              >
                <Icono nombre="refresh-ccw" size={14} /> Regenerar
              </Button>
              {report?.generator === "builder" ? (
                <a
                  href={`${apiBase()}/api/v1/reports/${reportId}/regenerate-pdf`}
                  className="inline-flex h-7 items-center gap-1.75 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-2.5 text-[13px] font-medium text-[var(--text-primary)] shadow-[var(--relieve-control)] hover:bg-[var(--color-subtle)]"
                >
                  <Icono nombre="download" size={14} /> PDF
                </a>
              ) : null}
            </div>
          </div>
        )}
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        {loading ? (
          <div className="p-4">
            <Skeleton className="h-96 w-full" />
          </div>
        ) : (
          <iframe
            key={refreshKey}
            src={htmlUrl}
            title={report?.title ?? "Reporte"}
            className="h-[calc(100vh-220px)] w-full rounded-[var(--radius-window)]"
          />
        )}
      </section>
    </div>
  );
}
