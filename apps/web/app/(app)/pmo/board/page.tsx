"use client";

/**
 * US-219 — Portfolio Board: los proyectos por estatus de reporte.
 *
 * El artboard «Boards» de los mockups aprobados. Contesta una pregunta que la
 * vista maestra no contesta bien: **«¿qué tengo que perseguir esta semana?»**.
 * En una tabla de veintitrés filas ordenada por salud eso exige leer una columna
 * entera; en cuatro columnas se ve el tamaño de cada pila de un golpe.
 *
 * ## Por qué las columnas son el estatus de reporte
 *
 * Porque es el único eje que la PMO puede accionar directamente: pedir un
 * reporte es una acción con dueño y fecha. La salud no se acciona —se explica—,
 * y la fase avanza por sí sola.
 *
 * `sin reporte` va primero, antes que `vencido`: un proyecto que nunca se
 * reportó no incumplió una fecha, no ha empezado. En un onboarding es
 * exactamente la columna que hay que vaciar.
 *
 * ## No es un kanban
 *
 * No se arrastra. El estatus de reporte es **derivado** —sale de la fecha del
 * último reporte contra la cadencia—, así que mover una tarjeta a «al día» no
 * significaría nada: el dato volvería a su sitio en el siguiente refresco.
 * Para cambiarlo hay que generar el reporte, y a eso lleva el enlace de la
 * tarjeta. Un board que acepta un arrastre que no persiste es peor que uno que
 * no lo acepta.
 */
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ClipboardCheck } from "lucide-react";

import { colorSalud } from "@/components/dashboard-charts";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { useOrgFiltro } from "@/components/organizacion-activa";
import { ApiError } from "@/lib/api";
import {
  getPortfolioBoard,
  type PortfolioBoard as Board,
} from "@/lib/api/dashboard";
import {
  PHASE_BADGE_TONE,
  PHASE_LABEL,
  etiquetaSalud,
  type ProjectPhase,
} from "@/lib/api/projects";
import { etiquetaDeCadencia, useCadenciaDeReporte } from "@/lib/cadencia-tenant";
import { cn } from "@/lib/cn";

/** El tinte del encabezado de cada columna, del mismo mapa que la tabla. */
const TONO: Record<string, string> = {
  sin_reporte: "var(--color-tertiary)",
  vencido: "var(--color-danger-fg)",
  por_vencer: "var(--color-warning-fg)",
  al_dia: "var(--color-success-fg)",
};

/** Qué hacer con cada pila. Un board sin verbo es una lista con bordes. */
const QUE_HACER: Record<string, string> = {
  sin_reporte: "Nunca se han reportado: empieza por aquí",
  vencido: "Pasaron de su fecha: pide el reporte",
  por_vencer: "Vencen dentro de poco: avisa",
  al_dia: "Nada que perseguir",
};

export default function PortfolioBoardPage() {
  const orgFiltro = useOrgFiltro();
  const cadencia = useCadenciaDeReporte();
  const [board, setBoard] = useState<Board | null>(null);
  const leido = useLectura(board);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    setError(null);
    getPortfolioBoard({ organization_id: orgFiltro })
      .then((r) => !cancelado && setBoard(r))
      .catch((e) => {
        if (cancelado) return;
        setBoard(null);
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudo cargar el board. Reintenta en un momento.",
        );
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [orgFiltro]);

  const conDecisiones = useMemo(
    () =>
      (board?.columns ?? []).reduce(
        (n, c) => n + c.projects.filter((p) => p.pending_decisions > 0).length,
        0,
      ),
    [board],
  );

  return (
    <div className="space-y-4 p-4">
      <Breadcrumb
        items={[{ href: "/pmo", label: "Portafolio" }, { label: "Board" }]}
      />
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Portfolio Board
        </h1>
        {leido && (
          <MarcaDeDatos
            periodo="vivo"
            detalle={`estatus contra la cadencia ${etiquetaDeCadencia(cadencia)}`}
            actualizado={leido}
          />
        )}
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Los proyectos por estatus de reporte, de lo más urgente a lo que no
          necesita nada. No se arrastra: el estatus se deriva de la fecha del
          último reporte, así que se cambia generando el reporte.
          {conDecisiones > 0 ? (
            <>
              {" "}
              <strong>{conDecisiones}</strong>{" "}
              {conDecisiones === 1 ? "proyecto tiene" : "proyectos tienen"}{" "}
              decisiones pendientes, marcadas en su tarjeta.
            </>
          ) : null}
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {cargando ? (
        <div className="grid gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              aria-hidden
              className="block h-64 animate-pulse rounded-[var(--radius-xl)] bg-[var(--color-muted)]"
            />
          ))}
        </div>
      ) : !board || board.total === 0 ? (
        /* DIS-03 — sin proyectos activos no hay board. Se dice, en vez de pintar
           cuatro columnas vacías que se leen como un error de carga. */
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--color-tertiary)]">
          No hay proyectos activos en esta organización. El board agrupa los que
          están en curso; los cerrados no se reportan y quedan fuera a propósito.
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-4">
          {board.columns.map((col) => (
            <section
              key={col.status}
              aria-label={`Proyectos ${col.label}`}
              className="flex flex-col rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]"
            >
              <header
                className="border-b border-[var(--border-default)] p-3"
                style={{ borderTopColor: TONO[col.status] }}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <h2
                    className="text-sm font-semibold capitalize"
                    style={{ color: TONO[col.status] }}
                  >
                    {col.label}
                  </h2>
                  <span className="text-sm font-semibold tabular-nums text-[var(--color-primary)]">
                    {col.projects.length}
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] text-[var(--color-tertiary)]">
                  {QUE_HACER[col.status]}
                </p>
              </header>
              <div className="flex-1 space-y-2 p-2">
                {col.projects.length === 0 ? (
                  <p className="py-6 text-center text-[11px] text-[var(--color-tertiary)]">
                    Vacía
                  </p>
                ) : (
                  col.projects.map((p) => (
                    <article
                      key={p.project_id}
                      className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-2.5"
                    >
                      <Link
                        href={`/pmo/projects/${p.project_id}/reports`}
                        className="block truncate text-[13px] font-medium text-[var(--color-primary)] hover:text-[var(--color-accent)]"
                        title={`${p.folio} · ${p.name} — ir a sus reportes`}
                      >
                        {p.name}
                      </Link>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                        <Badge
                          variant={
                            PHASE_BADGE_TONE[p.phase as ProjectPhase] ?? "neutral"
                          }
                        >
                          {PHASE_LABEL[p.phase as ProjectPhase] ?? p.phase}
                        </Badge>
                        <span style={{ color: colorSalud(p.health) }}>
                          {etiquetaSalud(p.health)}
                        </span>
                        {p.report_days_late > 0 ? (
                          <span className="tabular-nums text-[var(--color-danger-fg)]">
                            +{p.report_days_late} d
                          </span>
                        ) : null}
                      </div>
                      {/* El marcador de decisiones: el tercer cubo del mockup,
                          que no puede ser columna sin duplicar la tarjeta. */}
                      {p.pending_decisions > 0 ? (
                        <Link
                          href={`/pmo/projects/${p.project_id}/raid`}
                          className="mt-1.5 flex items-center gap-1 text-[11px] text-[var(--color-warning-fg)] hover:underline"
                        >
                          <ClipboardCheck className="h-3 w-3" aria-hidden />
                          {p.pending_decisions}{" "}
                          {p.pending_decisions === 1
                            ? "decisión pendiente"
                            : "decisiones pendientes"}
                        </Link>
                      ) : null}
                      {p.next_milestone ? (
                        <p
                          className={cn(
                            "mt-1 truncate text-[11px]",
                            p.next_milestone.overdue
                              ? "text-[var(--color-danger-fg)]"
                              : "text-[var(--color-tertiary)]",
                          )}
                          title={p.next_milestone.name}
                        >
                          {p.next_milestone.overdue ? (
                            <AlertTriangle
                              className="mr-1 inline h-3 w-3"
                              aria-hidden
                            />
                          ) : null}
                          {p.next_milestone.name}
                        </p>
                      ) : null}
                    </article>
                  ))
                )}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
