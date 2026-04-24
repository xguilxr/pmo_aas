"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { BarChart3, Download, ListTree, Plus, Rows3, Trash2 } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { GanttView } from "@/components/gantt-view";
import { ApiError } from "@/lib/api";
import { getProject } from "@/lib/api/projects";
import {
  TASK_STATUS_LABEL,
  createTask,
  deleteTask,
  getGantt,
  listTasks,
  type GanttData,
  type Task,
  type TaskStatus,
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

function TaskList({
  tasks,
  loading,
  onDelete,
}: {
  tasks: Task[];
  loading: boolean;
  onDelete?: (t: Task) => void;
}) {
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
            {onDelete ? <th className="w-10 px-3 py-2" aria-label="Acciones" /> : null}
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
              {onDelete ? (
                <td className="px-3 py-2">
                  <button
                    type="button"
                    onClick={() => onDelete(t)}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
                    aria-label={`Eliminar ${t.name}`}
                    title="Eliminar"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </td>
              ) : null}
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
  const [projectName, setProjectName] = useState<string>("");
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [loadingGantt, setLoadingGantt] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingXlsx, setExportingXlsx] = useState(false);

  // ENH-006: editor de tareas inline (crear + eliminar) sin depender de
  // una página extra /tasks.
  const [newOpen, setNewOpen] = useState(false);
  const [newForm, setNewForm] = useState({
    name: "",
    wbs: "",
    start_date: "",
    end_date: "",
    duration_days: "",
    progress: "0",
    is_milestone: false,
    status: "not_started" as TaskStatus,
  });
  const [creating, setCreating] = useState(false);

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

  async function loadTasksAndGantt() {
    setLoadingTasks(true);
    setLoadingGantt(true);
    try {
      const rows = await listTasks(id);
      setTasks(rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las tareas");
    } finally {
      setLoadingTasks(false);
    }
    try {
      const d = await getGantt(id);
      setGantt(d);
    } catch {
      /* el Gantt falla silencioso; el error del listado cubre el caso */
    } finally {
      setLoadingGantt(false);
    }
  }

  useEffect(() => {
    void loadTasksAndGantt();
    // ENH-028: nombre del proyecto para el filename del export. Falla silencioso
    // y queda con string vacío → fallback a "PROYECTO" en el nombre del archivo.
    getProject(id)
      .then((p) => setProjectName(p.name))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submitNewTask() {
    setCreating(true);
    setError(null);
    try {
      await createTask(id, {
        name: newForm.name,
        wbs: newForm.wbs || null,
        start_date: newForm.start_date || null,
        end_date: newForm.end_date || null,
        duration_days: newForm.duration_days ? Number(newForm.duration_days) : null,
        progress: Number(newForm.progress) || 0,
        is_milestone: newForm.is_milestone,
        status: newForm.status,
      });
      setNewOpen(false);
      setNewForm({
        name: "",
        wbs: "",
        start_date: "",
        end_date: "",
        duration_days: "",
        progress: "0",
        is_milestone: false,
        status: "not_started",
      });
      await loadTasksAndGantt();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la tarea");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteTask(t: Task) {
    if (!window.confirm(`Eliminar tarea "${t.name}"?`)) return;
    try {
      await deleteTask(t.id);
      await loadTasksAndGantt();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar la tarea");
    }
  }

  // ENH-028: filename "PLAN - {Proyecto} - {YYYY-MM-DD}". Sanitiza
  // caracteres ilegales en filesystems comunes (Windows, macOS).
  function buildFilename(ext: "csv" | "xlsx"): string {
    const safeName = (projectName || "PROYECTO")
      .replace(/[\\/:*?"<>|]/g, "")
      .trim() || "PROYECTO";
    const today = new Date().toISOString().slice(0, 10);
    return `PLAN - ${safeName} - ${today}.${ext}`;
  }

  function exportToCSV() {
    if (tasks.length === 0) {
      alert("No hay tareas para exportar");
      return;
    }
    const headers = [
      "WBS",
      "Tarea",
      "Inicio",
      "Fin",
      "Duración (días)",
      "Avance (%)",
      "Es hito",
      "Estado",
      "Responsable",
    ];
    const rows = tasks.map((t) => [
      t.wbs ?? "",
      t.name,
      t.start_date ?? "",
      t.end_date ?? "",
      t.duration_days ?? "",
      t.progress ?? 0,
      t.is_milestone ? "Sí" : "No",
      TASK_STATUS_LABEL[t.status as keyof typeof TASK_STATUS_LABEL] ?? t.status,
      "—",
    ]);
    const csv = [
      headers.map((h) => `"${h}"`).join(","),
      ...rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")),
    ].join("\n");
    // ENH-028: BOM UTF-8 (﻿) para que Excel lea acentos correctamente
    // (antes: "DuraciÃ³n", "DiseÃ±o" → ahora: "Duración", "Diseño").
    const blob = new Blob(["﻿", csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = buildFilename("csv");
    link.click();
  }

  // ENH-028: Excel MPP-like (XLSX) — colores sutiles por estado, hitos
  // resaltados, highlight retraso ligero (celda Avance amarilla si la
  // tarea debería estar más avanzada a hoy). Generación 100% client-side
  // con exceljs (dynamic import para no bloatear el bundle inicial).
  async function exportToExcel() {
    if (tasks.length === 0) {
      alert("No hay tareas para exportar");
      return;
    }
    setExportingXlsx(true);
    try {
      const ExcelJS = (await import("exceljs")).default;
      const wb = new ExcelJS.Workbook();
      wb.creator = "PMO aaS";
      wb.created = new Date();
      const ws = wb.addWorksheet("Plan", {
        views: [{ state: "frozen", ySplit: 1 }],
      });
      ws.columns = [
        { header: "WBS", key: "wbs", width: 10 },
        { header: "Tarea", key: "name", width: 40 },
        { header: "Inicio", key: "start", width: 12 },
        { header: "Fin", key: "end", width: 12 },
        { header: "Duración (días)", key: "duration", width: 14 },
        { header: "Avance (%)", key: "progress", width: 12 },
        { header: "Es hito", key: "milestone", width: 10 },
        { header: "Estado", key: "status", width: 16 },
        { header: "Responsable", key: "owner", width: 18 },
      ];
      // Header bold + fill gris claro.
      const header = ws.getRow(1);
      header.font = { bold: true, color: { argb: "FF1F2937" } };
      header.fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: { argb: "FFE5E7EB" },
      };
      header.alignment = { vertical: "middle", horizontal: "left" };
      header.height = 20;

      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayMs = today.getTime();

      // Colores sutiles MPP-like por estado (ARGB hex sin #).
      const STATUS_FILL: Record<string, string> = {
        completed: "FFE6F4EA",   // verde pálido
        in_progress: "FFE3F0FF", // azul pálido
        on_hold: "FFFFF4E5",     // ámbar pálido
        not_started: "FFF3F4F6", // gris claro
      };
      const LATE_PROGRESS_FILL = "FFFFF8C5"; // amarillo suave

      tasks.forEach((t, i) => {
        const rowNum = i + 2;
        const row = ws.addRow({
          wbs: t.wbs ?? "",
          name: t.name,
          start: t.start_date ?? "",
          end: t.end_date ?? "",
          duration: t.duration_days ?? "",
          progress: typeof t.progress === "number" ? t.progress / 100 : 0,
          milestone: t.is_milestone ? "♦" : "",
          status:
            TASK_STATUS_LABEL[t.status as keyof typeof TASK_STATUS_LABEL] ??
            t.status,
          owner: "—",
        });
        // Avance como porcentaje formateado.
        row.getCell("progress").numFmt = "0%";

        // Color por estado (todas las filas no-hito).
        const statusFill = STATUS_FILL[t.status as string];
        if (statusFill && !t.is_milestone) {
          row.eachCell({ includeEmpty: true }, (cell) => {
            cell.fill = {
              type: "pattern",
              pattern: "solid",
              fgColor: { argb: statusFill },
            };
          });
        }
        // Hitos: fondo morado pálido + bold para que destaquen.
        if (t.is_milestone) {
          row.eachCell({ includeEmpty: true }, (cell) => {
            cell.fill = {
              type: "pattern",
              pattern: "solid",
              fgColor: { argb: "FFEDE9FE" },
            };
            cell.font = { bold: true, color: { argb: "FF5B21B6" } };
          });
        }

        // Highlight retraso ligero: si end_date < hoy y avance < 100%,
        // pintamos solo la celda de Avance en amarillo (no agresivo).
        const endStr = t.end_date;
        if (endStr && (t.progress ?? 0) < 100) {
          const endMs = new Date(endStr).getTime();
          if (!Number.isNaN(endMs) && endMs < todayMs) {
            row.getCell("progress").fill = {
              type: "pattern",
              pattern: "solid",
              fgColor: { argb: LATE_PROGRESS_FILL },
            };
          }
        }
      });

      const buf = await wb.xlsx.writeBuffer();
      const blob = new Blob([buf], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = buildFilename("xlsx");
      link.click();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No se pudo generar el Excel",
      );
    } finally {
      setExportingXlsx(false);
    }
  }

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
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={exportToCSV}
              aria-label="Exportar a CSV"
            >
              <Download className="h-4 w-4" aria-hidden />
              CSV
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={exportToExcel}
              loading={exportingXlsx}
              aria-label="Exportar a Excel"
            >
              <Download className="h-4 w-4" aria-hidden />
              Excel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => setNewOpen(true)}
              aria-label="Nueva tarea"
            >
              <Plus className="h-4 w-4" aria-hidden />
              Nueva tarea
            </Button>
          </div>
        </header>
        <TaskList tasks={tasks} loading={loadingTasks} onDelete={handleDeleteTask} />
      </section>
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tasks, loadingTasks, id, exportingXlsx, projectName],
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

      <Modal
        open={newOpen}
        onClose={() => setNewOpen(false)}
        title="Nueva tarea"
        footer={
          <>
            <Button variant="secondary" onClick={() => setNewOpen(false)} disabled={creating}>
              Cancelar
            </Button>
            <Button onClick={submitNewTask} loading={creating} disabled={!newForm.name.trim()}>
              Crear
            </Button>
          </>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Nombre *
            </span>
            <Input
              value={newForm.name}
              onChange={(e) => setNewForm({ ...newForm, name: e.target.value })}
              required
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">WBS</span>
            <Input
              value={newForm.wbs}
              onChange={(e) => setNewForm({ ...newForm, wbs: e.target.value })}
              placeholder="1.2.3"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Estado
            </span>
            <Select
              value={newForm.status}
              onChange={(e) =>
                setNewForm({ ...newForm, status: e.target.value as TaskStatus })
              }
            >
              {(Object.keys(TASK_STATUS_LABEL) as TaskStatus[]).map((k) => (
                <option key={k} value={k}>
                  {TASK_STATUS_LABEL[k]}
                </option>
              ))}
            </Select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Inicio
            </span>
            <Input
              type="date"
              value={newForm.start_date}
              onChange={(e) => setNewForm({ ...newForm, start_date: e.target.value })}
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Fin
            </span>
            <Input
              type="date"
              value={newForm.end_date}
              onChange={(e) => setNewForm({ ...newForm, end_date: e.target.value })}
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Avance (0-100)
            </span>
            <Input
              type="number"
              min={0}
              max={100}
              value={newForm.progress}
              onChange={(e) => setNewForm({ ...newForm, progress: e.target.value })}
            />
          </label>
          <label className="inline-flex items-center gap-2 self-end">
            <input
              type="checkbox"
              checked={newForm.is_milestone}
              onChange={(e) =>
                setNewForm({ ...newForm, is_milestone: e.target.checked })
              }
            />
            <span className="text-xs text-[var(--color-secondary)]">Hito</span>
          </label>
        </div>
      </Modal>
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
