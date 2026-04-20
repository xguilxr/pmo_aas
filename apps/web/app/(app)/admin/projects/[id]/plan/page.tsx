"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { BarChart3, ExternalLink, ListTree, Rows3 } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GanttView } from "@/components/gantt-view";
import { ApiError } from "@/lib/api";
import {
  TASK_STATUS_LABEL,
  getGantt,
  listTasks,
  type GanttData,
  type Task,
} from "@/lib/api/tasks";
import { cn } from "@/lib/cn";

type Mode = "split" | "list" | "gantt";

const MODE_FROM_PARAM = (v: string | null): Mode =>
  v === "list" || v === "gantt" || v === "split" ? v : "split";

function fmtDate(d: string | null | undefined): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("es-MX");
  } catch {
    return d;
  }
}

function StatusBadge({ status }: { status: string }) {
  const label = TASK_STATUS_LABEL[status as keyof typeof TASK_STATUS_LABEL] ?? status;
  const tone =
    status === "done"
      ? "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]"
      : status === "in_progress"
        ? "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]"
        : status === "blocked"
          ? "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]"
          : "bg-[var(--color-subtle)] text-[var(--color-secondary)]";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
        tone,
      )}
    >
      {label}
    </span>
  );
}

function TaskList({ tasks, loading }: { tasks: Task[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }
  if (tasks.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-[var(--color-tertiary)]">
        Sin tareas registradas.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            <th className="w-16 px-3 py-2 font-medium">WBS</th>
            <th className="px-3 py-2 font-medium">Tarea</th>
            <th className="px-3 py-2 font-medium">Inicio</th>
            <th className="px-3 py-2 font-medium">Fin</th>
            <th className="px-3 py-2 font-medium">Avance</th>
            <th className="px-3 py-2 font-medium">Estado</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr
              key={t.id}
              className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
            >
              <td className="px-3 py-2 text-xs text-[var(--color-tertiary)] tabular-nums">
                {t.wbs ?? ""}
              </td>
              <td className="px-3 py-2">
                <div className="font-medium text-[var(--color-primary)]">
                  {t.is_milestone ? "🔷 " : ""}
                  {t.name}
                </div>
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {fmtDate(t.start_date)}
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {fmtDate(t.end_date)}
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)] tabular-nums">
                {t.progress}%
              </td>
              <td className="px-3 py-2">
                <StatusBadge status={t.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlanInner() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode = MODE_FROM_PARAM(searchParams.get("view"));
  const [mode, setMode] = useState<Mode>(initialMode);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [gantt, setGantt] = useState<GanttData | null>(null);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [loadingGantt, setLoadingGantt] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function setModeAndUrl(next: Mode) {
    setMode(next);
    const params = new URLSearchParams(searchParams.toString());
    if (next === "split") params.delete("view");
    else params.set("view", next);
    const qs = params.toString();
    router.replace(
      qs ? `/admin/projects/${id}/plan?${qs}` : `/admin/projects/${id}/plan`,
    );
  }

  useEffect(() => {
    let cancelled = false;
    setLoadingTasks(true);
    listTasks(id)
      .then((rows) => {
        if (!cancelled) setTasks(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudieron cargar las tareas",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTasks(false);
      });
    setLoadingGantt(true);
    getGantt(id)
      .then((d) => {
        if (!cancelled) setGantt(d);
      })
      .catch(() => {
        /* el Gantt falla silencioso; el error del listado cubre el caso */
      })
      .finally(() => {
        if (!cancelled) setLoadingGantt(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const listBlock = useMemo(
    () => (
      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="flex items-center justify-between border-b border-[var(--border-default)] px-4 py-3">
          <div className="flex items-center gap-2">
            <ListTree className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
            <h2 className="text-sm font-semibold text-[var(--color-primary)]">
              Lista de tareas
            </h2>
          </div>
          <Link
            href={`/admin/projects/${id}/tasks`}
            className="inline-flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
          >
            Abrir editor completo
            <ExternalLink className="h-3 w-3" aria-hidden />
          </Link>
        </header>
        <TaskList tasks={tasks} loading={loadingTasks} />
      </section>
    ),
    [tasks, loadingTasks, id],
  );

  const ganttBlock = useMemo(
    () => (
      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2 shadow-[var(--shadow-sm)]">
        <header className="flex items-center gap-2 px-2 py-2">
          <BarChart3 className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Gantt
          </h2>
        </header>
        {loadingGantt ? (
          <Skeleton className="h-[360px] w-full" />
        ) : gantt ? (
          <GanttView data={gantt} />
        ) : (
          <div className="p-6 text-center text-sm text-[var(--color-tertiary)]">
            Sin datos para el Gantt.
          </div>
        )}
      </section>
    ),
    [gantt, loadingGantt],
  );

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <nav className="text-[11px] text-[var(--text-tertiary)]">
            <Link href="/admin/projects" className="hover:underline">
              Proyectos
            </Link>
            <span className="mx-1">/</span>
            <Link href={`/admin/projects/${id}`} className="hover:underline">
              Detalle
            </Link>
            <span className="mx-1">/</span>
            <span>Plan</span>
          </nav>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Plan
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Lista de tareas y timeline Gantt en una sola vista. Ajusta la
            presentación con el toggle.
          </p>
        </div>

        <div
          role="radiogroup"
          aria-label="Vista del Plan"
          className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
        >
          {(
            [
              { v: "list", label: "Lista", icon: ListTree },
              { v: "split", label: "Dividida", icon: Rows3 },
              { v: "gantt", label: "Gantt", icon: BarChart3 },
            ] as const
          ).map((opt) => {
            const Icon = opt.icon;
            const active = mode === opt.v;
            return (
              <button
                key={opt.v}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setModeAndUrl(opt.v as Mode)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] px-3 py-1.5 text-xs font-medium transition-colors",
                  active
                    ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
                )}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden />
                {opt.label}
              </button>
            );
          })}
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {mode === "list" ? (
        listBlock
      ) : mode === "gantt" ? (
        ganttBlock
      ) : (
        <div className="space-y-4">
          {listBlock}
          {ganttBlock}
        </div>
      )}
    </div>
  );
}

export default function PlanPage() {
  return (
    <Suspense fallback={<div className="p-8"><Skeleton className="h-10 w-48" /></div>}>
      <PlanInner />
    </Suspense>
  );
}
