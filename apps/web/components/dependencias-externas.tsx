"use client";

/**
 * US-218 — Las dependencias del plan con otros proyectos.
 *
 * El artboard «Proyecto — Plan» pide un Gantt con «dependencias inter-proyecto».
 *
 * ## Por qué un panel y no flechas en el Gantt
 *
 * Una flecha necesita dos extremos en pantalla. La tarea del otro proyecto no
 * está en este Gantt —está en el de otro plan, con otras fechas y otra escala—,
 * así que la flecha tendría que salir del borde y apuntar a la nada. Eso no
 * comunica: obliga a adivinar a dónde va.
 *
 * Lo que sí comunica es nombrar el otro extremo con su proyecto y su fecha, que
 * es lo que alguien necesita para decidir: «esto no puede empezar hasta que
 * PRJ-2026-004 cierre su corte de servicios, previsto el 12 de septiembre».
 *
 * ## Entrantes y salientes van separadas
 *
 * Significan cosas distintas. Una entrante es algo que este proyecto **espera** y
 * que puede retrasarlo; una saliente es alguien esperándonos —y a quien hay que
 * avisar si nos movemos—. Mezcladas obligan a leer el sentido en cada fila, y la
 * mitad de las veces se lee al revés.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Trash2 } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { confirmarDestructivo } from "@/lib/confirmar";
import { ApiError } from "@/lib/api";
import {
  deleteExternalDependency,
  listExternalDependencies,
  type DependenciaExterna,
  type DependenciasExternas,
  type ExtremoExterno,
} from "@/lib/api/tasks";

/** Los cuatro vínculos de un cronograma, en palabras. */
const VINCULO: Record<string, string> = {
  FS: "fin → inicio",
  SS: "inicio → inicio",
  FF: "fin → fin",
  SF: "inicio → fin",
};

const FECHA = new Intl.DateTimeFormat("es-MX", {
  day: "2-digit",
  month: "short",
  year: "2-digit",
});

function fecha(iso: string | null | undefined): string {
  if (!iso) return "sin fecha";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "sin fecha" : FECHA.format(d);
}

function Extremo({ e }: { e: ExtremoExterno }) {
  return (
    <span className="min-w-0">
      {e.project_id ? (
        <Link
          href={`/pmo/projects/${e.project_id}/plan`}
          className="font-medium text-[var(--color-primary)] hover:text-[var(--color-accent)]"
          title={`Ir al plan de ${e.project_name ?? e.project_folio ?? ""}`}
        >
          {e.project_folio ?? e.project_name ?? "otro proyecto"}
        </Link>
      ) : (
        <span className="text-[var(--color-tertiary)]">otro proyecto</span>
      )}
      <span className="text-[var(--color-tertiary)]">
        {" · "}
        {e.task_name ?? "tarea"}
        {e.end_date ? ` (${fecha(e.end_date)})` : ""}
      </span>
    </span>
  );
}

export function DependenciasExternasPanel({
  projectId,
  puedeEditar,
}: {
  projectId: string;
  /** Sin permiso de escritura no se ofrece el borrado. */
  puedeEditar: boolean;
}) {
  const [datos, setDatos] = useState<DependenciasExternas | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(() => {
    setCargando(true);
    return listExternalDependencies(projectId)
      .then((r) => {
        setDatos(r);
        setError(null);
      })
      .catch((e) => {
        setDatos(null);
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudieron cargar las dependencias con otros proyectos.",
        );
      })
      .finally(() => setCargando(false));
  }, [projectId]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function quitar(d: DependenciaExterna) {
    // DIS-04 — el aviso nombra el objeto y dice la consecuencia. Quitar un
    // enlace entre planes cambia el orden de dos proyectos, no de uno, y eso
    // hay que decirlo: es la parte que quien confirma no puede inferir.
    const ok = confirmarDestructivo({
      objeto:
        `la dependencia entre «${d.predecessor.task_name ?? "la tarea"}» ` +
        `(${d.predecessor.project_folio ?? "otro proyecto"}) y ` +
        `«${d.successor.task_name ?? "la tarea"}» ` +
        `(${d.successor.project_folio ?? "otro proyecto"})`,
      consecuencia:
        "Los dos planes dejan de estar encadenados. Ninguna tarea se borra.",
      reversibilidad: "definitiva",
    });
    if (!ok) return;
    try {
      await deleteExternalDependency(projectId, d.id);
      await cargar();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo quitar la dependencia.",
      );
    }
  }

  if (cargando) {
    return (
      <span
        aria-hidden
        className="block h-16 animate-pulse rounded-[var(--radius-lg)] bg-[var(--color-muted)]"
      />
    );
  }

  const entrantes = datos?.entrantes ?? [];
  const salientes = datos?.salientes ?? [];

  return (
    <section
      aria-label="Dependencias con otros proyectos"
      className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
    >
      <h2 className="text-sm font-semibold text-[var(--color-primary)]">
        Dependencias con otros proyectos
      </h2>
      {error ? (
        <Banner variant="danger" className="mt-2">
          {error}
        </Banner>
      ) : null}

      {/* DIS-03 — ninguna dependencia externa es lo normal, y decirlo así evita
          que el panel vacío se lea como algo que falló al cargar. */}
      {entrantes.length === 0 && salientes.length === 0 ? (
        <p className="mt-2 text-[13px] text-[var(--color-tertiary)]">
          Este plan no está encadenado con ningún otro proyecto. Las
          dependencias dentro del proyecto viven en cada tarea, por código WBS.
        </p>
      ) : (
        <div className="mt-3 space-y-4">
          {entrantes.length > 0 ? (
            <div>
              <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
                <ArrowDownLeft className="h-3.5 w-3.5" aria-hidden />
                Este proyecto espera ({entrantes.length})
              </h3>
              <ul className="mt-1.5 divide-y divide-[var(--border-subtle)]">
                {entrantes.map((d) => (
                  <li
                    key={d.id}
                    className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-[13px]"
                  >
                    <span className="min-w-0 flex-1">
                      <Extremo e={d.predecessor} />
                      <span className="ml-1.5 text-[11px] text-[var(--color-tertiary)]">
                        {VINCULO[d.type] ?? d.type}
                        {d.lag_days ? ` · ${d.lag_days} d de holgura` : ""}
                      </span>
                    </span>
                    <span className="shrink-0 text-[11px] text-[var(--color-tertiary)]">
                      → {d.successor.task_name ?? "esta tarea"}
                    </span>
                    {puedeEditar ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => void quitar(d)}
                        aria-label="Quitar la dependencia"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {salientes.length > 0 ? (
            <div>
              <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
                Esperan a este proyecto ({salientes.length})
              </h3>
              <ul className="mt-1.5 divide-y divide-[var(--border-subtle)]">
                {salientes.map((d) => (
                  <li
                    key={d.id}
                    className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-[13px]"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="text-[var(--color-tertiary)]">
                        {d.predecessor.task_name ?? "esta tarea"} →{" "}
                      </span>
                      <Extremo e={d.successor} />
                      <span className="ml-1.5 text-[11px] text-[var(--color-tertiary)]">
                        {VINCULO[d.type] ?? d.type}
                      </span>
                    </span>
                    {puedeEditar ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => void quitar(d)}
                        aria-label="Quitar la dependencia"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
