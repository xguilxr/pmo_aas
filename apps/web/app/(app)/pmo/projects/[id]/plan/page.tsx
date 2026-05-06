"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  ChevronDown,
  ChevronRight,
  Download,
  FileDown,
  FileSpreadsheet,
  ListTree,
  Network,
  Pencil,
  Plus,
  Rows3,
  Trash2,
  Upload,
} from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { GanttView } from "@/components/gantt-view";
import { ImportWizard } from "@/components/import-wizard";
import { ApiError } from "@/lib/api";
import { getProject } from "@/lib/api/projects";
import {
  TASK_CRITICALITY_LABEL,
  TASK_STATUS_LABEL,
  createTask,
  deleteTask,
  getGantt,
  listTasks,
  updateTask,
  type GanttData,
  type Task,
  type TaskCriticality,
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

// ENH-047: ordena WBS como `1.2.10` > `1.2.2` (numérico, no lexicográfico).
function compareWbs(a: string | null | undefined, b: string | null | undefined): number {
  const sa = (a ?? "").split(".").map((p) => Number.parseInt(p, 10));
  const sb = (b ?? "").split(".").map((p) => Number.parseInt(p, 10));
  const len = Math.max(sa.length, sb.length);
  for (let i = 0; i < len; i += 1) {
    const va = Number.isFinite(sa[i]) ? sa[i] : 0;
    const vb = Number.isFinite(sb[i]) ? sb[i] : 0;
    if (va !== vb) return va - vb;
  }
  return 0;
}

function wbsDepth(wbs: string | null | undefined): number {
  if (!wbs) return 0;
  return wbs.split(".").filter(Boolean).length - 1;
}

function wbsParent(wbs: string | null | undefined): string | null {
  if (!wbs) return null;
  const parts = wbs.split(".").filter(Boolean);
  if (parts.length <= 1) return null;
  return parts.slice(0, -1).join(".");
}

// ENH-048: predicados para los chips de filtro Hitos / Críticos / Retrasados.
type ChipKey = "milestone" | "critical" | "delayed";

function isTaskCritical(t: Task): boolean {
  return t.criticality === "high" || t.criticality === "critical";
}

function isTaskDelayed(t: Task): boolean {
  if (!t.end_date) return false;
  if (t.status === "completed") return false;
  const end = new Date(t.end_date);
  if (Number.isNaN(end.getTime())) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return end.getTime() < today.getTime();
}

function chipMatches(t: Task, chips: Set<ChipKey>): boolean {
  if (chips.size === 0) return true;
  if (chips.has("milestone") && t.is_milestone) return true;
  if (chips.has("critical") && isTaskCritical(t)) return true;
  if (chips.has("delayed") && isTaskDelayed(t)) return true;
  return false;
}

function ownerLabel(owner: Task["owner"]): string {
  if (!owner) return "—";
  return owner.full_name?.trim() || owner.email;
}

function ownerInitials(owner: Task["owner"]): string {
  if (!owner) return "—";
  const src = owner.full_name?.trim() || owner.email;
  return src
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("") || "?";
}

function OwnerCell({ owner }: { owner: Task["owner"] }) {
  if (!owner) {
    return <span className="text-[var(--color-tertiary)]">—</span>;
  }
  return (
    <span
      className="inline-flex items-center gap-2"
      title={ownerLabel(owner)}
    >
      <span
        aria-hidden
        className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-subtle)] text-[10px] font-medium text-[var(--color-secondary)]"
      >
        {ownerInitials(owner)}
      </span>
      <span className="truncate text-[var(--color-secondary)]">
        {ownerLabel(owner)}
      </span>
    </span>
  );
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

// ENH-051: chip de color por criticidad. Critical rojo, high naranja,
// medium gris (sin chip — default), low verde.
function CriticalityChip({ value }: { value: TaskCriticality }) {
  if (value === "medium") return null;
  const tone =
    value === "critical"
      ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
      : value === "high"
        ? "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300"
        : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300";
  return (
    <span
      className={cn(
        "ml-2 inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide",
        tone,
      )}
      title={`Criticidad: ${TASK_CRITICALITY_LABEL[value]}`}
    >
      {TASK_CRITICALITY_LABEL[value]}
    </span>
  );
}

function TaskList({
  tasks,
  loading,
  onDelete,
  onEdit,
  groupByWbs = false,
  collapsed,
  onToggleCollapse,
  showProjectCols = false,
}: {
  tasks: Task[];
  loading: boolean;
  onDelete?: (t: Task) => void;
  // US-095: abre modal de edición pre-poblado.
  onEdit?: (t: Task) => void;
  // ENH-047: cuando true, ordena por WBS jerárquico + indenta por nivel
  // y permite colapsar nodos padre.
  groupByWbs?: boolean;
  collapsed?: Set<string>;
  onToggleCollapse?: (wbs: string) => void;
  // US-090: cuando true, muestra columnas Outline/Duration/Pred/Succ.
  showProjectCols?: boolean;
}) {
  const showActions = !!(onEdit || onDelete);
  // ENH-047: orden + visibilidad bajo grupo WBS.
  const display = useMemo(() => {
    if (!groupByWbs) return tasks;
    const sorted = [...tasks].sort((a, b) => compareWbs(a.wbs, b.wbs));
    if (!collapsed || collapsed.size === 0) return sorted;
    return sorted.filter((t) => {
      let p = wbsParent(t.wbs);
      while (p) {
        if (collapsed.has(p)) return false;
        p = wbsParent(p);
      }
      return true;
    });
  }, [tasks, groupByWbs, collapsed]);

  // ENH-047: set de WBS que tienen al menos un hijo (para mostrar chevron).
  const hasChildren = useMemo(() => {
    if (!groupByWbs) return new Set<string>();
    const out = new Set<string>();
    for (const t of tasks) {
      const p = wbsParent(t.wbs);
      if (p) out.add(p);
    }
    return out;
  }, [tasks, groupByWbs]);

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
            {showProjectCols ? (
              <th className="w-12 px-3 py-2 font-medium" title="Outline level (auto)">
                Nivel
              </th>
            ) : null}
            <th className="px-3 py-2 font-medium">Tarea</th>
            {/* ENH-049: columna Responsable entre Tarea y Fechas. */}
            <th className="px-3 py-2 font-medium">Responsable</th>
            <th className="px-3 py-2 font-medium">Inicio</th>
            <th className="px-3 py-2 font-medium">Fin</th>
            {showProjectCols ? (
              <>
                <th className="w-16 px-3 py-2 font-medium" title="Duración (auto, máx 21d)">
                  Dur.
                </th>
                <th className="w-24 px-3 py-2 font-medium">Predecesoras</th>
                <th className="w-24 px-3 py-2 font-medium">Sucesoras</th>
              </>
            ) : null}
            <th className="px-3 py-2 font-medium">Avance</th>
            <th className="px-3 py-2 font-medium">Estado</th>
            {showActions ? <th className="w-20 px-3 py-2" aria-label="Acciones" /> : null}
          </tr>
        </thead>
        <tbody>
          {display.map((t) => {
            const depth = groupByWbs ? wbsDepth(t.wbs) : 0;
            const wbsKey = t.wbs ?? "";
            const isParent = groupByWbs && wbsKey && hasChildren.has(wbsKey);
            const isCollapsed = !!(isParent && collapsed?.has(wbsKey));
            const delayed = isTaskDelayed(t);
            return (
            <tr
              key={t.id}
              className={cn(
                "border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]",
                delayed && "bg-[var(--color-danger-bg)]/40",
              )}
            >
              <td className="px-3 py-2 text-xs text-[var(--color-tertiary)] tabular-nums">
                {t.wbs ?? ""}
              </td>
              {showProjectCols ? (
                <td className="px-3 py-2 text-xs text-[var(--color-tertiary)] tabular-nums">
                  {t.outline_level ?? "—"}
                </td>
              ) : null}
              <td className="px-3 py-2">
                <div
                  className="flex items-center gap-1 font-medium text-[var(--color-primary)]"
                  style={groupByWbs ? { paddingLeft: depth * 16 } : undefined}
                >
                  {groupByWbs && isParent && onToggleCollapse ? (
                    <button
                      type="button"
                      onClick={() => onToggleCollapse(wbsKey)}
                      className="inline-flex h-4 w-4 items-center justify-center text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
                      aria-label={isCollapsed ? "Expandir" : "Colapsar"}
                    >
                      {isCollapsed ? (
                        <ChevronRight className="h-3.5 w-3.5" aria-hidden />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
                      )}
                    </button>
                  ) : groupByWbs ? (
                    <span className="inline-block h-4 w-4" aria-hidden />
                  ) : null}
                  <span className={delayed ? "text-[var(--color-danger-fg)]" : undefined}>
                    {t.is_milestone ? "🔷 " : ""}
                    {t.name}
                    {delayed ? (
                      <span
                        className="ml-2 inline-flex items-center rounded border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-danger-fg)]"
                        title="end_date < hoy y status != completado"
                      >
                        Retrasada
                      </span>
                    ) : null}
                    <CriticalityChip value={t.criticality ?? "medium"} />
                    {/* ENH-050: tooltip con hito relacionado. */}
                    {t.related_milestone ? (
                      <span
                        className="ml-2 inline-flex items-center rounded bg-[var(--color-subtle)] px-1.5 py-0.5 text-[9px] text-[var(--color-tertiary)]"
                        title={`Hito relacionado: ${t.related_milestone.name}`}
                      >
                        ↪ {t.related_milestone.wbs ?? t.related_milestone.name}
                      </span>
                    ) : null}
                  </span>
                </div>
              </td>
              <td className="px-3 py-2 text-xs">
                <OwnerCell owner={t.owner} />
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {fmtDate(t.start_date)}
              </td>
              <td
                className={cn(
                  "px-3 py-2",
                  delayed
                    ? "font-medium text-[var(--color-danger-fg)]"
                    : "text-[var(--color-secondary)]",
                )}
              >
                {fmtDate(t.end_date)}
              </td>
              {showProjectCols ? (
                <>
                  <td className="px-3 py-2 text-xs text-[var(--color-secondary)] tabular-nums">
                    {t.duration_days != null ? `${t.duration_days}d` : "—"}
                  </td>
                  <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                    {(t.predecessors ?? []).join(", ") || "—"}
                  </td>
                  <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                    {(t.successors ?? []).join(", ") || "—"}
                  </td>
                </>
              ) : null}
              <td className="px-3 py-2 text-[var(--color-secondary)] tabular-nums">
                {t.progress}%
              </td>
              <td className="px-3 py-2">
                <StatusBadge status={t.status} />
              </td>
              {showActions ? (
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1">
                    {onEdit ? (
                      <button
                        type="button"
                        onClick={() => onEdit(t)}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                        aria-label={`Editar ${t.name}`}
                        title="Editar"
                      >
                        <Pencil className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    ) : null}
                    {onDelete ? (
                      <button
                        type="button"
                        onClick={() => onDelete(t)}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
                        aria-label={`Eliminar ${t.name}`}
                        title="Eliminar"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    ) : null}
                  </div>
                </td>
              ) : null}
            </tr>
            );
          })}
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
  // US-071: descarga de plantilla vacía.
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  // US-070: el wizard maneja su propio busy/strategy/mapping.
  const [wizardOpen, setWizardOpen] = useState(false);

  // ENH-047: agrupación jerárquica por WBS. Default OFF para no romper
  // la UX actual; persiste en localStorage por proyecto.
  const [groupByWbs, setGroupByWbs] = useState(false);
  const [collapsedWbs, setCollapsedWbs] = useState<Set<string>>(new Set());

  // US-090: toggle visibilidad de columnas MS Project (Outline / Duration
  // / Predecesoras / Sucesoras). Default OFF para no saturar el ancho.
  const [showProjectCols, setShowProjectCols] = useState(false);

  // ENH-048: chips de filtro multi-select Hitos / Críticos / Retrasados.
  const [activeChips, setActiveChips] = useState<Set<ChipKey>>(new Set());

  function toggleChip(key: ChipKey) {
    setActiveChips((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  // Conteos por chip (siempre sobre el set total, no sobre filtrado).
  const chipCounts = useMemo(
    () => ({
      milestone: tasks.filter((t) => t.is_milestone).length,
      critical: tasks.filter((t) => isTaskCritical(t)).length,
      delayed: tasks.filter((t) => isTaskDelayed(t)).length,
    }),
    [tasks],
  );

  const filteredTasks = useMemo(
    () => (activeChips.size === 0 ? tasks : tasks.filter((t) => chipMatches(t, activeChips))),
    [tasks, activeChips],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const v = window.localStorage.getItem(`plan-grouping:${id}`);
      if (v === "wbs") setGroupByWbs(true);
    } catch {
      /* localStorage puede fallar (modo privado, quota) — ignoramos. */
    }
  }, [id]);

  function toggleGroupByWbs() {
    const next = !groupByWbs;
    setGroupByWbs(next);
    if (typeof window !== "undefined") {
      try {
        if (next) window.localStorage.setItem(`plan-grouping:${id}`, "wbs");
        else window.localStorage.removeItem(`plan-grouping:${id}`);
      } catch {
        /* localStorage puede fallar — la preferencia se pierde, no es crítico. */
      }
    }
  }

  function toggleCollapsedWbs(wbs: string) {
    setCollapsedWbs((prev) => {
      const next = new Set(prev);
      if (next.has(wbs)) next.delete(wbs);
      else next.add(wbs);
      return next;
    });
  }

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
    criticality: "medium" as TaskCriticality,
    // ENH-050: hito relacionado, opcional.
    related_milestone_id: "" as string,
    // US-090: predecesoras como string CSV ("1.1, 1.2") por simplicidad
    // del MVP — el backend valida cada wbs.
    predecessors_csv: "" as string,
  });
  const [creating, setCreating] = useState(false);

  // US-095: edición de tarea existente (mismo schema que newForm).
  const [editOpen, setEditOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    wbs: "",
    start_date: "",
    end_date: "",
    duration_days: "",
    progress: "0",
    is_milestone: false,
    status: "not_started" as TaskStatus,
    criticality: "medium" as TaskCriticality,
    related_milestone_id: "" as string,
    predecessors_csv: "" as string,
  });
  const [updating, setUpdating] = useState(false);

  function openEditTask(t: Task) {
    setEditingId(t.id);
    setEditForm({
      name: t.name,
      wbs: t.wbs ?? "",
      start_date: t.start_date ?? "",
      end_date: t.end_date ?? "",
      duration_days: t.duration_days != null ? String(t.duration_days) : "",
      progress: String(t.progress ?? 0),
      is_milestone: !!t.is_milestone,
      status: (t.status as TaskStatus) ?? "not_started",
      criticality: (t.criticality as TaskCriticality) ?? "medium",
      related_milestone_id: t.related_milestone?.id ?? "",
      predecessors_csv: (t.predecessors ?? []).join(", "),
    });
    setEditOpen(true);
  }

  async function submitEditTask() {
    if (!editingId) return;
    setUpdating(true);
    setError(null);
    try {
      const updated = await updateTask(editingId, {
        name: editForm.name,
        wbs: editForm.wbs || null,
        start_date: editForm.start_date || null,
        end_date: editForm.end_date || null,
        duration_days: editForm.duration_days ? Number(editForm.duration_days) : null,
        progress: Number(editForm.progress) || 0,
        is_milestone: editForm.is_milestone,
        status: editForm.status,
        criticality: editForm.criticality,
        related_milestone_id: editForm.related_milestone_id || null,
        predecessors: editForm.predecessors_csv
          ? editForm.predecessors_csv
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : null,
      });
      setEditOpen(false);
      setEditingId(null);
      // BUG-fix US-095 rework v2: refetch primero (para sincronizar gantt
      // y dependencias) y APLICAR DESPUÉS la respuesta del PATCH como
      // fuente autoritativa para la fila editada. Antes se aplicaba la
      // optimistic update y luego loadTasksAndGantt la pisaba con datos
      // potencialmente stale del cache HTTP del navegador.
      await loadTasksAndGantt();
      setTasks((prev) => prev.map((row) => (row.id === updated.id ? updated : row)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la tarea");
    } finally {
      setUpdating(false);
    }
  }

  function setModeAndUrl(next: Mode) {
    setMode(next);
    const params = new URLSearchParams(searchParams.toString());
    if (next === "split") params.delete("view");
    else params.set("view", next);
    const qs = params.toString();
    router.replace(
      qs ? `/pmo/projects/${id}/plan?${qs}` : `/pmo/projects/${id}/plan`,
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
        criticality: newForm.criticality,
        related_milestone_id: newForm.related_milestone_id || null,
        predecessors: newForm.predecessors_csv
          ? newForm.predecessors_csv
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : null,
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
        criticality: "medium",
        related_milestone_id: "",
        predecessors_csv: "",
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
      ownerLabel(t.owner),
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
          owner: ownerLabel(t.owner),
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
          {/* ENH-052: orden Plantilla → Descargar (Excel/CSV) → Importar
              con colores distintos. Plantilla = gris secundario;
              Descargar = azul; Importar = verde. CSV queda como variante
              compacta junto a Excel para no perder funcionalidad
              (ENH-028). Layout `flex-wrap` para apilar en móvil. */}
          <div className="flex flex-wrap items-center gap-2">
            {/* ENH-047: toggle agrupación por WBS jerárquica. */}
            <Button
              type="button"
              size="sm"
              variant={groupByWbs ? "primary" : "ghost"}
              onClick={toggleGroupByWbs}
              aria-label="Agrupar por WBS"
              aria-pressed={groupByWbs}
              title="Agrupar tareas por WBS jerárquico"
            >
              <Network className="h-4 w-4" aria-hidden />
              WBS
            </Button>
            {/* US-090: toggle columnas tipo MS Project (Outline / Duration
                / Predecesoras / Sucesoras). */}
            <Button
              type="button"
              size="sm"
              variant={showProjectCols ? "primary" : "ghost"}
              onClick={() => setShowProjectCols((v) => !v)}
              aria-label="Mostrar columnas MS Project"
              aria-pressed={showProjectCols}
              title="Outline level + Duración + Predecesoras + Sucesoras"
            >
              MSP
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              loading={downloadingTemplate}
              onClick={async () => {
                if (downloadingTemplate) return;
                setDownloadingTemplate(true);
                try {
                  const { downloadEmptyTemplate } = await import(
                    "@/lib/plan-template"
                  );
                  await downloadEmptyTemplate(projectName || "proyecto");
                } catch (err) {
                  alert(
                    err instanceof Error
                      ? err.message
                      : "No se pudo generar la plantilla",
                  );
                } finally {
                  setDownloadingTemplate(false);
                }
              }}
              aria-label="Descargar plantilla vacía"
              title="Descargar XLSX vacío con las columnas que el sistema espera"
            >
              <FileDown className="h-4 w-4" aria-hidden />
              Plantilla
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={exportToExcel}
              loading={exportingXlsx}
              aria-label="Descargar plan en Excel"
              className="bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300"
            >
              <Download className="h-4 w-4" aria-hidden />
              Descargar
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={exportToCSV}
              aria-label="Exportar a CSV"
              title="Descargar como CSV"
            >
              <FileSpreadsheet className="h-4 w-4" aria-hidden />
              CSV
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => setWizardOpen(true)}
              aria-label="Abrir wizard de import"
              className="bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-emerald-300"
            >
              <Upload className="h-4 w-4" aria-hidden />
              Importar
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
        {/* ENH-048: chips multi-select Hitos / Críticos / Retrasados. */}
        <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-2">
          {(
            [
              { key: "milestone" as const, label: "Hitos" },
              { key: "critical" as const, label: "Críticos" },
              { key: "delayed" as const, label: "Retrasados" },
            ]
          ).map(({ key, label }) => {
            const active = activeChips.has(key);
            const count = chipCounts[key];
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleChip(key)}
                aria-pressed={active}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  active
                    ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-inverse)]"
                    : "border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
                )}
              >
                {label}
                <span className="tabular-nums opacity-80">({count})</span>
              </button>
            );
          })}
          {activeChips.size > 0 ? (
            <button
              type="button"
              onClick={() => setActiveChips(new Set())}
              className="text-xs text-[var(--color-tertiary)] underline-offset-2 hover:underline"
            >
              Limpiar filtros
            </button>
          ) : null}
        </div>
        <TaskList
          tasks={filteredTasks}
          loading={loadingTasks}
          onDelete={handleDeleteTask}
          onEdit={openEditTask}
          groupByWbs={groupByWbs}
          collapsed={collapsedWbs}
          onToggleCollapse={toggleCollapsedWbs}
          showProjectCols={showProjectCols}
        />
      </section>
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      tasks,
      filteredTasks,
      loadingTasks,
      id,
      exportingXlsx,
      projectName,
      downloadingTemplate,
      groupByWbs,
      collapsedWbs,
      activeChips,
      chipCounts,
      showProjectCols,
    ],
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
            <Link href="/pmo/projects" className="hover:underline">
              Proyectos
            </Link>
            <span className="mx-1">/</span>
            <Link href={`/pmo/projects/${id}`} className="hover:underline">
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
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Criticidad
            </span>
            <Select
              value={newForm.criticality}
              onChange={(e) =>
                setNewForm({
                  ...newForm,
                  criticality: e.target.value as TaskCriticality,
                })
              }
            >
              {(Object.keys(TASK_CRITICALITY_LABEL) as TaskCriticality[]).map((k) => (
                <option key={k} value={k}>
                  {TASK_CRITICALITY_LABEL[k]}
                </option>
              ))}
            </Select>
          </label>
          {/* US-090: predecesoras CSV de wbs_code. */}
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Predecesoras (lista de WBS separadas por coma)
            </span>
            <Input
              value={newForm.predecessors_csv}
              onChange={(e) =>
                setNewForm({ ...newForm, predecessors_csv: e.target.value })
              }
              placeholder="1.1, 1.2"
            />
          </label>
          {/* ENH-050: hito relacionado. Solo lista tareas con
              is_milestone=true del proyecto actual. */}
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Hito relacionado (opcional)
            </span>
            <Select
              value={newForm.related_milestone_id}
              onChange={(e) =>
                setNewForm({ ...newForm, related_milestone_id: e.target.value })
              }
            >
              <option value="">— Sin hito —</option>
              {tasks
                .filter((t) => t.is_milestone)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.wbs ? `${t.wbs} · ` : ""}
                    {t.name}
                  </option>
                ))}
            </Select>
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

      {/* US-095: modal de edición. Mismos campos que Nueva tarea. */}
      <Modal
        open={editOpen}
        onClose={() => {
          setEditOpen(false);
          setEditingId(null);
        }}
        title="Editar tarea"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setEditOpen(false);
                setEditingId(null);
              }}
              disabled={updating}
            >
              Cancelar
            </Button>
            <Button
              onClick={submitEditTask}
              loading={updating}
              disabled={!editForm.name.trim()}
            >
              Guardar
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
              value={editForm.name}
              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              required
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">WBS</span>
            <Input
              value={editForm.wbs}
              onChange={(e) => setEditForm({ ...editForm, wbs: e.target.value })}
              placeholder="1.2.3"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Estado
            </span>
            <Select
              value={editForm.status}
              onChange={(e) =>
                setEditForm({ ...editForm, status: e.target.value as TaskStatus })
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
              value={editForm.start_date}
              onChange={(e) =>
                setEditForm({ ...editForm, start_date: e.target.value })
              }
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Fin
            </span>
            <Input
              type="date"
              value={editForm.end_date}
              onChange={(e) =>
                setEditForm({ ...editForm, end_date: e.target.value })
              }
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
              value={editForm.progress}
              onChange={(e) =>
                setEditForm({ ...editForm, progress: e.target.value })
              }
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Criticidad
            </span>
            <Select
              value={editForm.criticality}
              onChange={(e) =>
                setEditForm({
                  ...editForm,
                  criticality: e.target.value as TaskCriticality,
                })
              }
            >
              {(Object.keys(TASK_CRITICALITY_LABEL) as TaskCriticality[]).map((k) => (
                <option key={k} value={k}>
                  {TASK_CRITICALITY_LABEL[k]}
                </option>
              ))}
            </Select>
          </label>
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Predecesoras (lista de WBS separadas por coma)
            </span>
            <Input
              value={editForm.predecessors_csv}
              onChange={(e) =>
                setEditForm({ ...editForm, predecessors_csv: e.target.value })
              }
              placeholder="1.1, 1.2"
            />
          </label>
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
              Hito relacionado (opcional)
            </span>
            <Select
              value={editForm.related_milestone_id}
              onChange={(e) =>
                setEditForm({
                  ...editForm,
                  related_milestone_id: e.target.value,
                })
              }
            >
              <option value="">— Sin hito —</option>
              {tasks
                .filter((t) => t.is_milestone && t.id !== editingId)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.wbs ? `${t.wbs} · ` : ""}
                    {t.name}
                  </option>
                ))}
            </Select>
          </label>
          <label className="inline-flex items-center gap-2 self-end">
            <input
              type="checkbox"
              checked={editForm.is_milestone}
              onChange={(e) =>
                setEditForm({ ...editForm, is_milestone: e.target.checked })
              }
            />
            <span className="text-xs text-[var(--color-secondary)]">Hito</span>
          </label>
        </div>
      </Modal>

      <ImportWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        projectId={id}
        onImported={async () => {
          await loadTasksAndGantt();
        }}
      />
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
