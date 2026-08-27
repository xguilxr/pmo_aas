"use client";

/**
 * US-219 (segunda mitad) — Project Board: las tareas del proyecto por estado.
 *
 * El artboard «Boards» pide dos: «Project Board (kanban por estado, corte
 * bi-semanal)» y el Portfolio Board, que ya está en `/pmo/board`.
 *
 * ## Por qué aquí SÍ se arrastra y en el Portfolio Board no
 *
 * Es la diferencia entre un estado **declarado** y uno **derivado**.
 * `tasks.status` lo pone una persona: arrastrar una tarjeta a «En curso» es
 * exactamente la forma más directa de decir lo que ya se podía decir editando la
 * tarea. El estatus de reporte de un proyecto, en cambio, se calcula de la fecha
 * del último reporte y de la cadencia (US-211): arrastrar un proyecto de
 * «vencido» a «al día» pediría al sistema mentir, y el siguiente recálculo lo
 * devolvería a su sitio. Por eso ese board no se arrastra y este sí.
 *
 * ## El corte del artboard es un marcador, no una columna
 *
 * «Corte bi-semanal» es la cadencia de reporte del inquilino (US-213). Convertirlo
 * en columnas daría un tablero de dos ejes —estado × corte— que no se lee. Lo que
 * hace falta saber al mirar el board es cuáles de estas tareas caen antes del
 * próximo corte, y eso es una marca en la tarjeta.
 *
 * ## Lo que el board muestra y no arregla
 *
 * Una tarea en «Completada» con avance por debajo del 100 % es una
 * contradicción que ya puede existir en los datos —el estado y el avance son
 * campos separados—. El board la **marca** en vez de reescribir el avance en
 * silencio: corregirla es una decisión de quien la conoce, y un tablero que
 * cambia datos que nadie le pidió cambiar es peor que uno que los señala.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { RaidKanban, type KanbanColumn, type KanbanItem } from "@/components/raid-kanban";
import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { ApiError } from "@/lib/api";
import { listTasks, updateTask, type Task, type TaskStatus } from "@/lib/api/tasks";
import { etiquetaDeCadencia, useCadenciaDeReporte } from "@/lib/cadencia-tenant";

/**
 * Las cuatro columnas, en el orden en que avanza el trabajo.
 *
 * `on_hold` va al final y no entre medias: una tarea detenida no está «casi en
 * curso», está fuera del flujo, y ponerla en el camino haría que arrastrar de
 * izquierda a derecha pasara por ella.
 */
const COLUMNAS: KanbanColumn[] = [
  { id: "not_started", label: "Sin empezar" },
  { id: "in_progress", label: "En curso" },
  { id: "completed", label: "Completada" },
  { id: "on_hold", label: "Detenida" },
];

function hoy(): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function dias(desde: Date, hastaIso: string): number {
  const h = new Date(hastaIso);
  h.setHours(0, 0, 0, 0);
  return Math.round((h.getTime() - desde.getTime()) / 86_400_000);
}

export default function ProjectBoardPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  const cadencia = useCadenciaDeReporte();
  const [tareas, setTareas] = useState<Task[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [moviendo, setMoviendo] = useState<string | null>(null);
  const leido = useLectura(tareas);

  const cargar = useCallback(() => {
    return listTasks(id)
      .then((t) => {
        setTareas(t);
        setError(null);
      })
      .catch((e) => {
        setTareas(null);
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudieron cargar las tareas del proyecto.",
        );
      });
  }, [id]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function mover(taskId: string, estado: string) {
    setMoviendo(taskId);
    // Se pinta el cambio antes de que el servidor conteste: arrastrar y ver la
    // tarjeta volver a su columna medio segundo se lee como que falló.
    setTareas((prev) =>
      prev
        ? prev.map((t) =>
            t.id === taskId ? { ...t, status: estado as TaskStatus } : t,
          )
        : prev,
    );
    try {
      await updateTask(taskId, { status: estado as TaskStatus });
      await cargar();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo mover la tarea.",
      );
      // Si falló, el estado real lo dice el servidor y no este componente.
      await cargar();
    } finally {
      setMoviendo(null);
    }
  }

  const items: KanbanItem[] = useMemo(() => {
    if (!tareas) return [];
    const ahora = hoy();
    return tareas.map((t) => {
      const restantes = t.end_date ? dias(ahora, t.end_date) : null;
      const vencida =
        t.status !== "completed" && restantes !== null && restantes < 0;
      const enElCorte =
        t.status !== "completed" &&
        restantes !== null &&
        restantes >= 0 &&
        restantes <= cadencia;
      // `progress` no es nulable en el modelo (0 por defecto), así que aquí un
      // cero es un cero de verdad y no un hueco: la tarea está declarada
      // completada y su avance dice que nadie la tocó.
      const avanceIncoherente = t.status === "completed" && t.progress < 100;
      return {
        id: t.id,
        status: t.status,
        // Un WBS es lo que identifica una tarea en una conversación de plan,
        // igual que el folio identifica un riesgo en el board de RAID.
        folio: t.wbs_code || "—",
        title: t.name,
        href: `/pmo/projects/${id}/plan`,
        accent: (
          <span className="flex items-center gap-1.5">
            {t.is_milestone ? (
              <span
                aria-hidden
                title="Hito"
                className="inline-block h-2 w-2 shrink-0 rotate-45 rounded-[1px] bg-[var(--color-info-fg)]"
              />
            ) : null}
            {vencida ? (
              <span
                className="flex items-center gap-0.75 font-mono text-[10px] text-[var(--color-danger-fg)]"
                title={`Venció hace ${Math.abs(restantes as number)} días`}
              >
                <Icono nombre="triangle-alert" size={11} />
                {Math.abs(restantes as number)}d
              </span>
            ) : enElCorte ? (
              <span
                className="flex items-center gap-0.75 font-mono text-[10px] text-[var(--color-warning-fg)]"
                title={`Vence antes del próximo corte (cadencia ${etiquetaDeCadencia(cadencia)})`}
              >
                <Icono nombre="clock" size={11} />
                {restantes}d
              </span>
            ) : null}
            {avanceIncoherente ? (
              <span
                className="font-mono text-[10px] text-[var(--color-warning-fg)]"
                title="Está completada y su avance es menor al 100 %. El board no lo corrige solo: los dos campos son separados y cuál está mal lo sabe quien conoce la tarea."
              >
                {t.progress}%
              </span>
            ) : null}
          </span>
        ),
      };
    });
  }, [tareas, cadencia, id]);

  const enElCorte = useMemo(
    () =>
      (tareas ?? []).filter((t) => {
        if (t.status === "completed" || !t.end_date) return false;
        const r = dias(hoy(), t.end_date);
        return r >= 0 && r <= cadencia;
      }).length,
    [tareas, cadencia],
  );

  return (
    <div className="space-y-4 p-6">
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
          <span>Board</span>
        </nav>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Board del proyecto
        </h1>
        {leido ? (
          <MarcaDeDatos
            periodo="vivo"
            detalle={`corte ${etiquetaDeCadencia(cadencia)}`}
            actualizado={leido}
          />
        ) : null}
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {tareas === null ? (
        error ? null : (
          <span
            aria-hidden
            className="block h-48 animate-pulse rounded-[var(--radius-xl)] bg-[var(--color-muted)]"
          />
        )
      ) : tareas.length === 0 ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-8 text-center text-sm text-[var(--text-secondary)]">
          Este proyecto todavía no tiene tareas. El board las muestra por estado;
          para cargarlas, usa{" "}
          <Link
            href={`/pmo/projects/${id}/plan`}
            className="text-[var(--text-primary)] underline"
          >
            el plan
          </Link>
          .
        </div>
      ) : (
        <>
          <p className="text-xs text-[var(--text-tertiary)]">
            {enElCorte === 0
              ? `Ninguna tarea vence antes del próximo corte (${etiquetaDeCadencia(cadencia)}).`
              : `${enElCorte} tarea${enElCorte === 1 ? "" : "s"} vence${enElCorte === 1 ? "" : "n"} antes del próximo corte (${etiquetaDeCadencia(cadencia)}).`}{" "}
            Arrastra una tarjeta para cambiar su estado.
          </p>
          <RaidKanban
            columns={COLUMNAS}
            items={items}
            onMove={(taskId, estado) => void mover(taskId, estado)}
            busyId={moviendo}
          />
        </>
      )}
    </div>
  );
}
