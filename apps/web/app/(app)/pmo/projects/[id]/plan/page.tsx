"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Building2,
  ChevronDown,
  ChevronRight,
  Columns3,
  Diamond,
  Download,
  FileDown,
  GripVertical,
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
import { InlineSelectCell } from "@/components/inline-select-cell";
import { PersonPicker } from "@/components/directory/PersonPicker";
import { ProjectAreaPicker } from "@/components/directory/ProjectAreaPicker";
import { ApiError } from "@/lib/api";
import { listUsers, type AdminUser } from "@/lib/api/admin";
import { listActorsByProject, type Actor } from "@/lib/api/areas";
import { listProjectAreas, type ProjectArea } from "@/lib/api/project-areas";
import { getProject } from "@/lib/api/projects";
import {
  TASK_STATUS_LABEL,
  createTask,
  deleteTask,
  getGantt,
  listTasks,
  moveTask,
  renumberWbs,
  updateTask,
  type GanttData,
  type Task,
  type TaskCriticality,
  type TaskStatus,
  type TaskUpdateBody,
} from "@/lib/api/tasks";
import { cn } from "@/lib/cn";

type Mode = "split" | "list" | "gantt";

const MODE_FROM_PARAM = (v: string | null): Mode =>
  v === "list" || v === "gantt" || v === "split" ? v : "split";

// ENH-094: duración inclusive desde dos strings YYYY-MM-DD del form.
// Devuelve null si falta alguno o si end < start.
function computeDurationDaysFromForm(
  start: string | null | undefined,
  end: string | null | undefined,
): number | null {
  if (!start || !end) return null;
  const s = new Date(`${start}T00:00:00`);
  const e = new Date(`${end}T00:00:00`);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null;
  const days = Math.round((e.getTime() - s.getTime()) / 86_400_000) + 1;
  return days >= 0 ? days : null;
}

function fmtDate(d: string | null | undefined): string {
  if (!d) return "—";
  // Bug timezone: la API devuelve YYYY-MM-DD (date pura sin TZ). El
  // constructor `new Date("YYYY-MM-DD")` interpreta como UTC midnight,
  // y al formatear en TZ negativa muestra el día anterior. Parseamos
  // YYYY-MM-DD como fecha local explícitamente.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d);
  if (m) {
    const local = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return local.toLocaleDateString("es-MX");
  }
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

// ENH-133: criticidad es booleana (is_critical). Fallback al enum legacy
// para tareas viejas sin el boolean seteado.
function isTaskCritical(t: Task): boolean {
  if (typeof t.is_critical === "boolean") return t.is_critical;
  return t.criticality === "high" || t.criticality === "critical";
}

// US-171: atraso. Tarea NO completada → retrasada si end_date < hoy. Tarea
// completada → retrasada si se cerró tarde (closed_at > end_date). Sin
// closed_at, una tarea completada no se considera retrasada.
function isTaskDelayed(t: Task): boolean {
  if (!t.end_date) return false;
  const end = new Date(t.end_date);
  if (Number.isNaN(end.getTime())) return false;
  const completed = t.status === "completed" || (t.progress ?? 0) >= 100;
  if (completed) {
    if (!t.closed_at) return false;
    const closed = new Date(t.closed_at);
    if (Number.isNaN(closed.getTime())) return false;
    return closed.getTime() > end.getTime();
  }
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

// ENH-135: label + control para los forms de tarea.
function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = TASK_STATUS_LABEL[status as keyof typeof TASK_STATUS_LABEL] ?? status;
  // BUG-067: el enum real es completed/on_hold (no done/blocked).
  const tone =
    status === "completed"
      ? "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]"
      : status === "in_progress"
        ? "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]"
        : status === "on_hold"
          ? "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]"
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

// US-098 fix: dropdown checklist de Áreas para la toolbar top-level.
// Popover simple con click-outside para cerrar. Multi-select via Set.
// Toggle adicional "Agrupar" arriba del listado para que el botón de
// área en la toolbar también permita activar la agrupación por área.
function AreaFilterDropdown({
  areas,
  selected,
  onChange,
  groupByArea,
  onToggleGroup,
}: {
  areas: ProjectArea[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
  groupByArea: boolean;
  onToggleGroup: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [popoverEl, setPopoverEl] = useState<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (popoverEl && !popoverEl.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open, popoverEl]);
  const count = selected.size;
  const label =
    count === 0 ? "Todas" : count === 1 ? "1 área" : `${count} áreas`;
  return (
    <div ref={setPopoverEl} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Filtrar por Área"
        className={cn(
          "inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-medium",
          count > 0
            ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
            : "border border-[var(--border-default)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
        )}
      >
        <Building2 className="h-3.5 w-3.5" aria-hidden />
        Área: {label}
        <ChevronDown className="h-3 w-3" aria-hidden />
      </button>
      {open ? (
        <div
          role="listbox"
          className="absolute left-0 z-20 mt-1 w-64 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2 shadow-[var(--shadow-md)]"
        >
          <div className="mb-1 flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
            <button
              type="button"
              onClick={onToggleGroup}
              aria-pressed={groupByArea}
              className={cn(
                "rounded px-2 py-0.5 text-[11px] font-medium",
                groupByArea
                  ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "border border-[var(--border-default)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
              )}
            >
              {groupByArea ? "Agrupando por Área" : "Agrupar por Área"}
            </button>
            {selected.size > 0 ? (
              <button
                type="button"
                onClick={() => onChange(new Set())}
                className="text-[11px] text-[var(--color-tertiary)] hover:underline"
              >
                Limpiar
              </button>
            ) : null}
          </div>
          {areas.length === 0 ? (
            <p className="p-2 text-[11px] italic text-[var(--color-tertiary)]">
              Sin áreas registradas en el proyecto.
            </p>
          ) : (
            <ul className="max-h-64 overflow-auto">
              {areas.map((a) => {
                const checked = selected.has(a.id);
                return (
                  <li key={a.id}>
                    <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-xs hover:bg-[var(--color-subtle)]">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          const next = new Set(selected);
                          if (checked) next.delete(a.id);
                          else next.add(a.id);
                          onChange(next);
                        }}
                      />
                      <span className="flex-1 text-[var(--color-primary)]">
                        {a.name}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

// ENH-164: configurador de columnas (reemplaza el toggle "MSP"). Las
// columnas obligatorias siempre se muestran; las opcionales se activan aquí.
const OPTIONAL_COLS = [
  { key: "outline", label: "Nivel (outline)" },
  { key: "duration", label: "Duración" },
  { key: "predecessors", label: "Predecesoras" },
  { key: "successors", label: "Sucesoras" },
] as const;
type OptionalColKey = (typeof OPTIONAL_COLS)[number]["key"];
type ColVis = Record<OptionalColKey, boolean>;
const DEFAULT_COL_VIS: ColVis = {
  outline: false,
  duration: false,
  predecessors: false,
  successors: false,
};
const MANDATORY_COL_LABELS = [
  "WBS",
  "Tarea",
  "Área responsable",
  "Inicio",
  "Fin",
  "Avance",
  "Estado",
  "Criticidad",
  "Hito",
];

function ColumnsDropdown({
  value,
  onChange,
}: {
  value: ColVis;
  onChange: (next: ColVis) => void;
}) {
  const [open, setOpen] = useState(false);
  const [popoverEl, setPopoverEl] = useState<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (popoverEl && !popoverEl.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open, popoverEl]);
  const extra = OPTIONAL_COLS.filter((c) => value[c.key]).length;
  return (
    <div ref={setPopoverEl} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Configurar columnas visibles"
        className={cn(
          "inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-medium",
          extra > 0
            ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
            : "border border-[var(--border-default)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
        )}
      >
        <Columns3 className="h-3.5 w-3.5" aria-hidden />
        Columnas{extra > 0 ? ` (+${extra})` : ""}
        <ChevronDown className="h-3 w-3" aria-hidden />
      </button>
      {open ? (
        <div
          role="listbox"
          className="absolute left-0 z-20 mt-1 w-60 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2 shadow-[var(--shadow-md)]"
        >
          <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Siempre visibles
          </p>
          <ul className="mb-1.5 border-b border-[var(--border-subtle)] pb-1.5">
            {MANDATORY_COL_LABELS.map((label) => (
              <li key={label}>
                <label className="flex items-center gap-2 rounded px-2 py-1 text-xs text-[var(--color-tertiary)]">
                  <input type="checkbox" checked readOnly disabled />
                  <span className="flex-1">{label}</span>
                </label>
              </li>
            ))}
          </ul>
          <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Opcionales
          </p>
          <ul>
            {OPTIONAL_COLS.map((c) => {
              const checked = value[c.key];
              return (
                <li key={c.key}>
                  <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-xs hover:bg-[var(--color-subtle)]">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onChange({ ...value, [c.key]: !checked })}
                    />
                    <span className="flex-1 text-[var(--color-primary)]">
                      {c.label}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

// ENH-066 + ENH-077: agrupación por Área. Render header de grupo +
// TaskList plana por área. Sólo se muestran áreas con al menos 1
// fila visible (chips × área filter ya aplicados en filteredTasks).
function AreaGroupedList({
  tasks,
  areas,
  loading,
  onDelete,
  onEdit,
  colVis,
  onInlineUpdate,
}: {
  tasks: Task[];
  areas: ProjectArea[];
  loading: boolean;
  onDelete?: (t: Task) => void;
  onEdit?: (t: Task) => void;
  colVis: ColVis;
  onInlineUpdate?: (taskId: string, patch: Partial<TaskUpdateBody>) => void;
}) {
  const grouped = useMemo(() => {
    const byArea = new Map<string, Task[]>();
    for (const t of tasks) {
      const key = t.area_id ?? "__unassigned__";
      if (!byArea.has(key)) byArea.set(key, []);
      byArea.get(key)!.push(t);
    }
    return byArea;
  }, [tasks]);

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
        Sin tareas registradas (filtros activos pueden estar ocultando todo).
      </div>
    );
  }

  // Áreas con tareas (ordenadas por nombre); "Sin asignar" al final.
  const areaOrder = areas
    .filter((a) => grouped.has(a.id))
    .sort((a, b) => a.name.localeCompare(b.name, "es"));
  const unassigned = grouped.get("__unassigned__");

  return (
    <div>
      {areaOrder.map((a) => (
        <div key={a.id}>
          <div className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--color-secondary)]">
            {a.name}{" "}
            <span className="ml-1 text-[var(--color-tertiary)] tabular-nums">
              ({grouped.get(a.id)!.length})
            </span>
          </div>
          <TaskList
            tasks={grouped.get(a.id)!}
            loading={false}
            onDelete={onDelete}
            onEdit={onEdit}
            colVis={colVis}
            areas={areas}
            onInlineUpdate={onInlineUpdate}
          />
        </div>
      ))}
      {unassigned ? (
        <div>
          <div className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Sin asignar{" "}
            <span className="ml-1 tabular-nums">({unassigned.length})</span>
          </div>
          <TaskList
            tasks={unassigned}
            loading={false}
            onDelete={onDelete}
            onEdit={onEdit}
            colVis={colVis}
            areas={areas}
            onInlineUpdate={onInlineUpdate}
          />
        </div>
      ) : null}
    </div>
  );
}

// US-173: celda de Avance editable con doble clic → input numérico.
function InlineProgressCell({
  value,
  onCommit,
}: {
  value: number;
  onCommit: (n: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));
  useEffect(() => {
    setDraft(String(value));
  }, [value]);
  if (!editing) {
    return (
      <span
        className="cursor-pointer tabular-nums hover:underline"
        title="Doble clic para editar el avance"
        onDoubleClick={() => setEditing(true)}
      >
        {value}%
      </span>
    );
  }
  const commit = () => {
    setEditing(false);
    const n = Math.max(0, Math.min(100, Math.round(Number(draft) || 0)));
    if (n !== value) onCommit(n);
  };
  return (
    <input
      type="number"
      min={0}
      max={100}
      autoFocus
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") {
          setDraft(String(value));
          setEditing(false);
        }
      }}
      className="w-16 rounded border border-[var(--border-default)] bg-[var(--color-surface)] px-1 py-0.5 text-xs tabular-nums"
    />
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
  colVis = DEFAULT_COL_VIS,
  areas = [],
  onInlineUpdate,
  onReorder,
}: {
  tasks: Task[];
  loading: boolean;
  onDelete?: (t: Task) => void;
  // US-095: abre modal de edición pre-poblado.
  onEdit?: (t: Task) => void;
  // US-173: edición inline desde la celda (área/fechas/avance/estado/
  // criticidad/hito) sin abrir el modal.
  onInlineUpdate?: (taskId: string, patch: Partial<TaskUpdateBody>) => void;
  // US-176: reorden por fila (drag con handle). Coloca `dragId` antes de
  // `targetId`. Sólo se provee en la vista plana sin filtros.
  onReorder?: (dragId: string, targetId: string) => void;
  // ENH-047: cuando true, ordena por WBS jerárquico + indenta por nivel
  // y permite colapsar nodos padre.
  groupByWbs?: boolean;
  collapsed?: Set<string>;
  onToggleCollapse?: (wbs: string) => void;
  // ENH-164: columnas opcionales (Nivel/Duración/Predecesoras/Sucesoras).
  colVis?: ColVis;
  // US-098 fix: áreas del proyecto para resolver `task.area_id` →
  // nombre en la columna 'Área responsable'.
  areas?: ProjectArea[];
}) {
  const areaById = useMemo(() => {
    const m = new Map<string, string>();
    for (const a of areas) m.set(a.id, a.name);
    return m;
  }, [areas]);
  const showActions = !!(onEdit || onDelete);
  // US-176: id de la fila que se está arrastrando (reorder).
  const [dragId, setDragId] = useState<string | null>(null);
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
            {onReorder ? (
              <th className="w-8 px-1 py-2" aria-label="Reordenar" />
            ) : null}
            <th className="w-16 px-3 py-2 font-medium">WBS</th>
            {colVis.outline ? (
              <th className="w-12 px-3 py-2 font-medium" title="Outline level (auto)">
                Nivel
              </th>
            ) : null}
            <th className="px-3 py-2 font-medium">Tarea</th>
            {/* US-098 fix: la columna ahora es 'Área responsable'.
                El owner (responsable persona) sigue editable en el form. */}
            <th className="px-3 py-2 font-medium">Área responsable</th>
            <th className="px-3 py-2 font-medium">Inicio</th>
            <th className="px-3 py-2 font-medium">Fin</th>
            {colVis.duration ? (
              <th className="w-16 px-3 py-2 font-medium" title="Duración (auto). Máximo recomendado 21d; macros mayores se permiten con warning.">
                Dur.
              </th>
            ) : null}
            {colVis.predecessors ? (
              <th className="w-24 px-3 py-2 font-medium">Predecesoras</th>
            ) : null}
            {colVis.successors ? (
              <th className="w-24 px-3 py-2 font-medium">Sucesoras</th>
            ) : null}
            <th className="px-3 py-2 font-medium">Avance</th>
            <th className="px-3 py-2 font-medium">Estado</th>
            <th className="px-3 py-2 font-medium">Criticidad</th>
            <th className="px-3 py-2 font-medium">Hito</th>
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
              onDragOver={
                onReorder
                  ? (e) => {
                      if (dragId && dragId !== t.id) e.preventDefault();
                    }
                  : undefined
              }
              onDrop={
                onReorder
                  ? () => {
                      if (dragId && dragId !== t.id) onReorder(dragId, t.id);
                      setDragId(null);
                    }
                  : undefined
              }
              className={cn(
                "border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]",
                delayed && "bg-[var(--color-danger-bg)]/40",
                dragId === t.id && "opacity-50",
              )}
            >
              {/* US-176: handle de arrastre (sólo vista plana sin filtros). */}
              {onReorder ? (
                <td className="px-1 py-2 align-middle">
                  <span
                    draggable
                    onDragStart={() => setDragId(t.id)}
                    onDragEnd={() => setDragId(null)}
                    title="Arrastra para reordenar"
                    aria-label={`Reordenar ${t.name}`}
                    className="flex h-6 w-6 cursor-grab items-center justify-center text-[var(--color-tertiary)] hover:text-[var(--color-primary)] active:cursor-grabbing"
                  >
                    <GripVertical className="h-4 w-4" aria-hidden />
                  </span>
                </td>
              ) : null}
              <td className="px-3 py-2 text-xs text-[var(--color-tertiary)] tabular-nums">
                {t.wbs ?? ""}
              </td>
              {colVis.outline ? (
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
                    {t.is_milestone ? (
                      <Diamond
                        className="mr-1 inline h-3 w-3 text-[var(--color-info-fg)]"
                        aria-hidden
                      />
                    ) : null}
                    {t.name}
                    {delayed ? (
                      <span
                        className="ml-2 inline-flex items-center rounded border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-danger-fg)]"
                        title="end_date < hoy y status != completado"
                      >
                        Retrasada
                      </span>
                    ) : null}
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
              {/* US-173 + Fase 2: Área responsable editable inline (on-click). */}
              <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                {onInlineUpdate ? (
                  <InlineSelectCell
                    value={t.area_id ?? ""}
                    options={[
                      { value: "", label: "— Sin asignar —" },
                      ...areas.map((a) => ({ value: a.id, label: a.name })),
                    ]}
                    onChange={(v) => onInlineUpdate(t.id, { area_id: v || null })}
                    title="Área responsable"
                    ariaLabel={`Área de ${t.name}`}
                  />
                ) : t.area_id && areaById.has(t.area_id) ? (
                  <span className="text-[var(--color-secondary)]">
                    {areaById.get(t.area_id)}
                  </span>
                ) : (
                  <span className="text-[var(--color-tertiary)]">—</span>
                )}
              </td>
              {/* US-173: fechas editables inline (calendario nativo). */}
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {onInlineUpdate ? (
                  <input
                    type="date"
                    value={t.start_date ?? ""}
                    onChange={(e) =>
                      onInlineUpdate(t.id, { start_date: e.target.value || null })
                    }
                    title="Inicio"
                    className="rounded border border-transparent bg-transparent px-1 py-0.5 text-xs hover:border-[var(--border-default)] focus:border-[var(--border-default)] focus:outline-none"
                  />
                ) : (
                  fmtDate(t.start_date)
                )}
              </td>
              <td
                className={cn(
                  "px-3 py-2",
                  delayed
                    ? "font-medium text-[var(--color-danger-fg)]"
                    : "text-[var(--color-secondary)]",
                )}
              >
                {onInlineUpdate ? (
                  <input
                    type="date"
                    value={t.end_date ?? ""}
                    onChange={(e) =>
                      onInlineUpdate(t.id, { end_date: e.target.value || null })
                    }
                    title="Fin"
                    className="rounded border border-transparent bg-transparent px-1 py-0.5 text-xs hover:border-[var(--border-default)] focus:border-[var(--border-default)] focus:outline-none"
                  />
                ) : (
                  fmtDate(t.end_date)
                )}
              </td>
              {colVis.duration ? (
                <td className="px-3 py-2 text-xs text-[var(--color-secondary)] tabular-nums">
                  {t.duration_days != null ? (
                    t.duration_days > 21 ? (
                      <span
                        className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] bg-[var(--color-warning-bg)] px-1.5 py-0.5 font-medium text-[var(--color-warning-fg)]"
                        title="Duración mayor al máximo recomendado de 21 días. OK para actividades macro; considera dividir si es operativa."
                      >
                        ⚠ {t.duration_days}d
                      </span>
                    ) : (
                      <span>{t.duration_days}d</span>
                    )
                  ) : (
                    "—"
                  )}
                </td>
              ) : null}
              {colVis.predecessors ? (
                <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                  {(t.predecessors ?? []).join(", ") || "—"}
                </td>
              ) : null}
              {colVis.successors ? (
                <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                  {(t.successors ?? []).join(", ") || "—"}
                </td>
              ) : null}
              {/* US-173: Avance editable con doble clic. */}
              <td className="px-3 py-2 text-[var(--color-secondary)] tabular-nums">
                {onInlineUpdate ? (
                  <InlineProgressCell
                    value={t.progress}
                    onCommit={(n) => onInlineUpdate(t.id, { progress: n })}
                  />
                ) : (
                  `${t.progress}%`
                )}
              </td>
              {/* US-173 + Fase 2: Estado editable inline (on-click). */}
              <td className="px-3 py-2">
                {onInlineUpdate ? (
                  <InlineSelectCell
                    value={t.status}
                    options={(Object.keys(TASK_STATUS_LABEL) as TaskStatus[]).map(
                      (k) => ({ value: k, label: TASK_STATUS_LABEL[k] }),
                    )}
                    onChange={(v) =>
                      onInlineUpdate(t.id, { status: v as TaskStatus })
                    }
                    title="Estado"
                    ariaLabel={`Estado de ${t.name}`}
                  />
                ) : (
                  <StatusBadge status={t.status} />
                )}
              </td>
              {/* US-173: Criticidad como checkmark inline. */}
              <td className="px-3 py-2">
                {onInlineUpdate ? (
                  <input
                    type="checkbox"
                    checked={isTaskCritical(t)}
                    onChange={(e) =>
                      onInlineUpdate(t.id, { is_critical: e.target.checked })
                    }
                    title="Marcar crítica"
                    aria-label={`Crítica: ${t.name}`}
                  />
                ) : isTaskCritical(t) ? (
                  <span className="inline-flex items-center rounded-full bg-[var(--color-danger-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-danger-fg)]">
                    Sí
                  </span>
                ) : (
                  <span className="text-[var(--color-tertiary)]">—</span>
                )}
              </td>
              {/* ENH-163 + US-173: Hito como checkmark inline. */}
              <td className="px-3 py-2">
                {onInlineUpdate ? (
                  <input
                    type="checkbox"
                    checked={t.is_milestone}
                    onChange={(e) =>
                      onInlineUpdate(t.id, { is_milestone: e.target.checked })
                    }
                    title="Marcar hito"
                    aria-label={`Hito: ${t.name}`}
                  />
                ) : t.is_milestone ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-info-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-info-fg)]">
                    <Diamond className="h-3 w-3" aria-hidden /> Hito
                  </span>
                ) : (
                  <span className="text-[var(--color-tertiary)]">—</span>
                )}
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
  // US-098: áreas del proyecto (project_areas, US-091) para select en
  // form + filtro. Nota: el filter en este state acepta multi-select
  // (Set) para el dropdown checklist de la nueva toolbar.
  const [areas, setAreas] = useState<ProjectArea[]>([]);
  const [areaFilter, setAreaFilter] = useState<Set<string>>(new Set());
  // US-098 fix: usuarios del tenant para el select de Responsable en
  // el edit form de tarea.
  const [users, setUsers] = useState<AdminUser[]>([]);
  // ENH-079: actores del proyecto (catálogo tenant) para Responsable.
  const [actors, setActors] = useState<Actor[]>([]);
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
  // ENH-066: agrupación por Área (mutex con WBS).
  const [groupByArea, setGroupByArea] = useState(false);
  const [collapsedWbs, setCollapsedWbs] = useState<Set<string>>(new Set());
  // ENH-067: nivel rápido WBS. "manual" deja `collapsedWbs` tal cual
  // (default — usuario expande/colapsa con chevron). 1..4 colapsan
  // todos los WBS de profundidad N para que sólo se muestren niveles
  // ≤ N. Cualquier toggle manual del chevron cambia el modo a "manual"
  // automáticamente.
  // ENH-165: nivel 0 = colapsa todo y deja sólo las filas raíz (depth 0).
  type WbsLevel = 0 | 1 | 2 | 3 | 4 | "manual";
  const [wbsLevel, setWbsLevel] = useState<WbsLevel>("manual");

  // US-090: toggle visibilidad de columnas MS Project (Outline / Duration
  // / Predecesoras / Sucesoras). Default OFF para no saturar el ancho.
  const [colVis, setColVis] = useState<ColVis>(DEFAULT_COL_VIS);

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

  const filteredTasks = useMemo(() => {
    let rows = tasks;
    if (activeChips.size > 0) rows = rows.filter((t) => chipMatches(t, activeChips));
    // US-098: filtro por Área (chip dropdown).
    if (areaFilter.size > 0)
      rows = rows.filter((t) => t.area_id && areaFilter.has(t.area_id));
    return rows;
  }, [tasks, activeChips, areaFilter]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const v = window.localStorage.getItem(`plan-grouping:${id}`);
      if (v === "wbs") setGroupByWbs(true);
      else if (v === "area") setGroupByArea(true);
      // ENH-077 CA5: chips activos persistidos.
      const chipsRaw = window.localStorage.getItem(`plan-chips:${id}`);
      if (chipsRaw) {
        const chips = chipsRaw
          .split(",")
          .filter((c): c is ChipKey => c === "milestone" || c === "critical" || c === "delayed");
        if (chips.length > 0) setActiveChips(new Set(chips));
      }
      // ENH-077 CA5: nivel WBS persistido.
      const lvlRaw = window.localStorage.getItem(`plan-wbs-level:${id}`);
      if (
        lvlRaw === "0" || lvlRaw === "1" || lvlRaw === "2" ||
        lvlRaw === "3" || lvlRaw === "4"
      ) {
        setWbsLevel(Number(lvlRaw) as 0 | 1 | 2 | 3 | 4);
      } else if (lvlRaw === "manual") {
        setWbsLevel("manual");
      }
      // areaFilter persistido (CSV de IDs).
      const af = window.localStorage.getItem(`plan-area-filter:${id}`);
      if (af)
        setAreaFilter(new Set(af.split(",").map((s) => s.trim()).filter(Boolean)));
      // ENH-164: visibilidad de columnas opcionales persistida.
      const colsRaw = window.localStorage.getItem(`plan-cols:${id}`);
      if (colsRaw) {
        try {
          const parsed = JSON.parse(colsRaw) as Partial<ColVis>;
          setColVis((prev) => ({ ...prev, ...parsed }));
        } catch {
          /* JSON inválido — ignoramos. */
        }
      }
    } catch {
      /* localStorage puede fallar (modo privado, quota) — ignoramos. */
    }
  }, [id]);

  // ENH-077 CA5: persiste chips, level, areaFilter cuando cambian.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (activeChips.size === 0) window.localStorage.removeItem(`plan-chips:${id}`);
      else window.localStorage.setItem(
        `plan-chips:${id}`,
        Array.from(activeChips).join(","),
      );
    } catch {
      /* ignore */
    }
  }, [activeChips, id]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(`plan-wbs-level:${id}`, String(wbsLevel));
    } catch {
      /* ignore */
    }
  }, [wbsLevel, id]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (areaFilter.size > 0)
        window.localStorage.setItem(
          `plan-area-filter:${id}`,
          Array.from(areaFilter).join(","),
        );
      else window.localStorage.removeItem(`plan-area-filter:${id}`);
    } catch {
      /* ignore */
    }
  }, [areaFilter, id]);

  // ENH-164: persiste la visibilidad de columnas opcionales.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(`plan-cols:${id}`, JSON.stringify(colVis));
    } catch {
      /* ignore */
    }
  }, [colVis, id]);

  // ENH-077: WBS y Área son mutex — sólo un agrupador a la vez.
  function persistGrouping(mode: "wbs" | "area" | null) {
    if (typeof window === "undefined") return;
    try {
      if (mode) window.localStorage.setItem(`plan-grouping:${id}`, mode);
      else window.localStorage.removeItem(`plan-grouping:${id}`);
    } catch {
      /* localStorage puede fallar — la preferencia se pierde, no es crítico. */
    }
  }

  function toggleGroupByWbs() {
    const next = !groupByWbs;
    setGroupByWbs(next);
    if (next) setGroupByArea(false); // mutex
    persistGrouping(next ? "wbs" : null);
  }

  function toggleGroupByArea() {
    const next = !groupByArea;
    setGroupByArea(next);
    if (next) {
      setGroupByWbs(false); // mutex
      // ENH-077: cada agrupador tiene su propio set de colapsado;
      // al cambiar de WBS a Área limpiamos collapsedWbs para no
      // contaminar.
      setCollapsedWbs(new Set());
      setWbsLevel("manual");
    }
    persistGrouping(next ? "area" : null);
  }

  function toggleCollapsedWbs(wbs: string) {
    setCollapsedWbs((prev) => {
      const next = new Set(prev);
      if (next.has(wbs)) next.delete(wbs);
      else next.add(wbs);
      return next;
    });
    // ENH-067: cualquier toggle manual sale de los niveles rápidos.
    setWbsLevel("manual");
  }

  // ENH-067: aplica un nivel rápido. Colapsa todos los WBS con
  // `depth >= level` para que sólo se muestren los niveles 1..level.
  function applyWbsLevel(level: WbsLevel) {
    setWbsLevel(level);
    if (level === "manual") return;
    const next = new Set<string>();
    for (const t of tasks) {
      const w = t.wbs;
      if (!w) continue;
      if (wbsDepth(w) >= level) next.add(w);
    }
    setCollapsedWbs(next);
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
    // ENH-097: boolean explicito de criticidad (paralelo al enum).
    is_critical: false,
    // ENH-050: hito relacionado, opcional.
    related_milestone_id: "" as string,
    // US-090: predecesoras como string CSV ("1.1, 1.2") por simplicidad
    // del MVP — el backend valida cada wbs.
    predecessors_csv: "" as string,
    // ENH-135: área responsable + responsable también en Nueva tarea.
    area_id: "" as string,
    assignee_actor_id: "" as string,
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
    // US-171: fecha de cierre real.
    closed_at: "",
    duration_days: "",
    progress: "0",
    is_milestone: false,
    status: "not_started" as TaskStatus,
    criticality: "medium" as TaskCriticality,
    // ENH-097: boolean explicito de criticidad (paralelo al enum).
    is_critical: false,
    related_milestone_id: "" as string,
    predecessors_csv: "" as string,
    // US-098: área responsable + responsable (owner).
    area_id: "" as string,
    owner_id: "" as string,
    // ENH-079: responsable como Actor del catálogo.
    assignee_actor_id: "" as string,
  });
  const [updating, setUpdating] = useState(false);

  function openEditTask(t: Task) {
    setEditingId(t.id);
    setEditForm({
      name: t.name,
      wbs: t.wbs ?? "",
      start_date: t.start_date ?? "",
      end_date: t.end_date ?? "",
      closed_at: t.closed_at ?? "",
      duration_days: t.duration_days != null ? String(t.duration_days) : "",
      progress: String(t.progress ?? 0),
      area_id: t.area_id ?? "",
      owner_id: t.owner_id ?? "",
      assignee_actor_id: (t as { assignee_actor_id?: string | null }).assignee_actor_id ?? "",
      is_milestone: !!t.is_milestone,
      status: (t.status as TaskStatus) ?? "not_started",
      criticality: (t.criticality as TaskCriticality) ?? "medium",
      // ENH-097: respeta valor del backend; si viene undefined (rows
      // pre-migración), mirror desde el enum criticality.
      is_critical:
        typeof t.is_critical === "boolean"
          ? t.is_critical
          : t.criticality === "high" || t.criticality === "critical",
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
        closed_at: editForm.closed_at || null,
        duration_days: editForm.duration_days ? Number(editForm.duration_days) : null,
        progress: Number(editForm.progress) || 0,
        is_milestone: editForm.is_milestone,
        status: editForm.status,
        criticality: editForm.criticality,
        is_critical: editForm.is_critical,
        related_milestone_id: editForm.related_milestone_id || null,
        predecessors: editForm.predecessors_csv
          ? editForm.predecessors_csv
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : null,
        area_id: editForm.area_id || null,
        owner_id: editForm.assignee_actor_id ? null : (editForm.owner_id || null),
        // ENH-079: nuevo flujo. Si elige Actor, owner_id se nulea para
        // evitar doble fuente. Backend display prioriza Actor.
        assignee_actor_id: editForm.assignee_actor_id || null,
      } as Parameters<typeof updateTask>[1] & { assignee_actor_id: string | null });
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

  // BUG-076: áreas del proyecto (project-scoped). Se recarga junto con las
  // tareas para que un área recién creada/asignada inline aparezca en la
  // lista y el filtro sin reload de página.
  async function loadAreas() {
    try {
      const rows = await listProjectAreas(id, { is_active: true });
      setAreas(rows.filter((r) => r.type === "area"));
    } catch {
      /* silencioso — la UI muestra "Sin áreas" */
    }
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
    // BUG-076: refrescar áreas tras cualquier reload de tareas.
    void loadAreas();
  }

  // US-172: renumera el WBS de todo el proyecto (jerárquico + único).
  const [renumbering, setRenumbering] = useState(false);
  async function handleRenumberWbs() {
    if (renumbering) return;
    if (
      !window.confirm(
        "Auto-numerar WBS reescribe el WBS de TODAS las tareas de forma " +
          "jerárquica (1, 1.1, 1.2, 2, …), preservando el orden actual y " +
          "resolviendo duplicados. ¿Continuar?",
      )
    )
      return;
    setRenumbering(true);
    try {
      await renumberWbs(id);
      await loadTasksAndGantt();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo renumerar el WBS",
      );
    } finally {
      setRenumbering(false);
    }
  }

  // US-173 + Fase 2: cambio inline OPTIMISTA — aplica el patch local de
  // inmediato; si el PATCH falla, revierte a la fila previa y muestra el error.
  async function handleInlineUpdate(
    taskId: string,
    patch: Partial<TaskUpdateBody>,
  ) {
    const prevTask = tasks.find((t) => t.id === taskId);
    setTasks((prev) =>
      prev.map((r) => (r.id === taskId ? ({ ...r, ...patch } as Task) : r)),
    );
    try {
      const updated = await updateTask(taskId, patch);
      // El server puede derivar campos (duration, closed_at en completed) →
      // reemplazamos con la versión autoritativa.
      setTasks((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      // Cambios que afectan el Gantt → refrescar en background.
      if (
        "start_date" in patch ||
        "end_date" in patch ||
        "status" in patch ||
        "progress" in patch ||
        "is_milestone" in patch
      ) {
        void getGantt(id)
          .then(setGantt)
          .catch(() => {});
      }
    } catch (err) {
      // Revert optimista.
      if (prevTask) {
        setTasks((prev) => prev.map((r) => (r.id === taskId ? prevTask : r)));
      }
      setError(
        err instanceof ApiError ? err.message : "No se pudo actualizar la tarea",
      );
    }
  }

  // US-176: reorden por fila (drag). Coloca dragId ANTES de targetId.
  // Optimista sobre `tasks` (sólo se habilita en vista plana sin filtros, así
  // que `tasks` === orden mostrado). Recalcula after_id y persiste.
  function handleReorderTask(dragId: string, targetId: string) {
    if (dragId === targetId) return;
    const arr = [...tasks];
    const from = arr.findIndex((t) => t.id === dragId);
    if (from < 0) return;
    const [moved] = arr.splice(from, 1);
    const insertAt = arr.findIndex((t) => t.id === targetId);
    if (insertAt < 0) return;
    arr.splice(insertAt, 0, moved); // insertar ANTES del target
    const newIdx = arr.findIndex((t) => t.id === dragId);
    const afterId = newIdx > 0 ? arr[newIdx - 1].id : null;
    setTasks(arr); // optimista
    void moveTask(id, dragId, afterId).catch((err) => {
      setError(
        err instanceof ApiError ? err.message : "No se pudo reordenar la tarea",
      );
      void loadTasksAndGantt(); // revert desde el server
    });
  }

  useEffect(() => {
    void loadTasksAndGantt();
    // ENH-028: nombre del proyecto para el filename del export. Falla silencioso
    // y queda con string vacío → fallback a "PROYECTO" en el nombre del archivo.
    getProject(id)
      .then((p) => setProjectName(p.name))
      .catch(() => {});
    // US-098 / BUG-076: las áreas del proyecto las carga loadTasksAndGantt
    // (arriba), así se refrescan en cada reload sin duplicar el fetch.
    listUsers({ is_active: true, page: 1, limit: 200 })
      .then((resp) => setUsers(resp.items))
      .catch(() => {});
    // ENH-079: actores del proyecto (vía area_assignments cascade) para
    // el dropdown de Responsable. Reemplaza el flujo legacy `users`.
    listActorsByProject(id)
      .then((rows) => setActors(rows))
      .catch(() => setActors([]));
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
        is_critical: newForm.is_critical,
        related_milestone_id: newForm.related_milestone_id || null,
        predecessors: newForm.predecessors_csv
          ? newForm.predecessors_csv
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : null,
        // ENH-135: área + responsable desde Nueva tarea.
        area_id: newForm.area_id || null,
        owner_id: null,
        assignee_actor_id: newForm.assignee_actor_id || null,
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
        is_critical: false,
        related_milestone_id: "",
        predecessors_csv: "",
        area_id: "",
        assignee_actor_id: "",
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
  function buildFilename(ext: "xlsx"): string {
    const safeName = (projectName || "PROYECTO")
      .replace(/[\\/:*?"<>|]/g, "")
      .trim() || "PROYECTO";
    const today = new Date().toISOString().slice(0, 10);
    return `PLAN - ${safeName} - ${today}.${ext}`;
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
      // ENH-134: orden de columnas canónico (espeja la plantilla).
      const areaName = (aid: string | null) =>
        (aid && areas.find((a) => a.id === aid)?.name) || "";
      ws.columns = [
        { header: "WBS", key: "wbs", width: 10 },
        { header: "Tarea", key: "name", width: 40 },
        { header: "Outline Level", key: "outline", width: 12 },
        { header: "Inicio", key: "start", width: 12 },
        { header: "Fin", key: "end", width: 12 },
        { header: "Duración (días)", key: "duration", width: 14 },
        { header: "Avance (%)", key: "progress", width: 12 },
        { header: "Estado", key: "status", width: 16 },
        { header: "Área Responsable", key: "area", width: 22 },
        { header: "Responsable", key: "owner", width: 18 },
        { header: "Criticidad", key: "criticality", width: 12 },
        { header: "Es hito", key: "milestone", width: 10 },
        { header: "Hito Relacionado", key: "related_milestone", width: 18 },
        { header: "Predecessors", key: "predecessors", width: 16 },
        { header: "Successors", key: "successors", width: 16 },
      ];
      // Header bold + fill gris claro. ENH-134: font negro.
      const header = ws.getRow(1);
      header.font = { bold: true, color: { argb: "FF000000" } };
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
          outline: t.outline_level ?? "",
          start: t.start_date ?? "",
          end: t.end_date ?? "",
          duration: t.duration_days ?? "",
          progress: typeof t.progress === "number" ? t.progress / 100 : 0,
          status:
            TASK_STATUS_LABEL[t.status as keyof typeof TASK_STATUS_LABEL] ??
            t.status,
          area: areaName(t.area_id),
          owner: ownerLabel(t.owner),
          criticality: isTaskCritical(t) ? "Sí" : "No",
          milestone: t.is_milestone ? "Sí" : "No",
          related_milestone: t.related_milestone?.wbs ?? t.related_milestone?.name ?? "",
          predecessors: (t.predecessors ?? []).join(", "),
          successors: (t.successors ?? []).join(", "),
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
        <header className="flex items-center gap-2 border-b border-[var(--border-default)] px-4 py-3">
          <ListTree className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Lista de tareas
          </h2>
        </header>
        {/* ENH-048 (movido a la toolbar top-level): los chips Hitos /
            Críticos / Retrasados ahora viven junto a WBS/Área/MSP para
            seguir accesibles en modo "solo Gantt". */}
        {groupByArea ? (
          // ENH-066: agrupación por Área. Render una TaskList por
          // grupo con header. Áreas vacías post-filtro se omiten
          // (ENH-077 CA1/CA3).
          <AreaGroupedList
            tasks={filteredTasks}
            areas={areas}
            loading={loadingTasks}
            onDelete={handleDeleteTask}
            onEdit={openEditTask}
            colVis={colVis}
            onInlineUpdate={handleInlineUpdate}
          />
        ) : (
          <TaskList
            tasks={filteredTasks}
            loading={loadingTasks}
            onDelete={handleDeleteTask}
            onEdit={openEditTask}
            groupByWbs={groupByWbs}
            collapsed={collapsedWbs}
            onToggleCollapse={toggleCollapsedWbs}
            colVis={colVis}
            areas={areas}
            onInlineUpdate={handleInlineUpdate}
            onReorder={
              // US-176: reorden sólo en vista plana sin filtros (display === tasks).
              !groupByWbs && activeChips.size === 0 && areaFilter.size === 0
                ? handleReorderTask
                : undefined
            }
          />
        )}
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
      colVis,
      areaFilter,
    ],
  );

  // ENH-068 + ENH-077: el Gantt respeta el set visible de la lista
  // (chips × agrupador × área filter × nivel WBS). Construimos un
  // GanttData filtrado a partir de filteredTasks + collapsedWbs.
  const filteredGantt = useMemo<GanttData | null>(() => {
    if (!gantt) return null;
    const visibleIds = new Set<string>();
    // Si hay agrupación WBS con colapsado, descartamos también las
    // tasks ocultas por la cadena de padres (mismo criterio que la
    // lista). Si no hay agrupación, sólo aplica filteredTasks.
    const filteredById = new Set(filteredTasks.map((t) => t.id));
    for (const t of filteredTasks) {
      if (groupByWbs && collapsedWbs.size > 0) {
        let p = wbsParent(t.wbs);
        let hidden = false;
        while (p) {
          if (collapsedWbs.has(p)) {
            hidden = true;
            break;
          }
          p = wbsParent(p);
        }
        if (!hidden) visibleIds.add(t.id);
      } else {
        visibleIds.add(t.id);
      }
    }
    return {
      ...gantt,
      tasks: gantt.tasks.filter((g) => visibleIds.has(g.id)),
      dependencies: gantt.dependencies.filter(
        (d) => visibleIds.has(d.predecessor_id) && visibleIds.has(d.successor_id),
      ),
    };
  }, [gantt, filteredTasks, groupByWbs, collapsedWbs]);

  const ganttBlock = useMemo(
    () => (
      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2 shadow-[var(--shadow-sm)]">
        <header className="flex items-center gap-2 px-2 py-2">
          <BarChart3 className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Gantt
          </h2>
          {filteredGantt && gantt && filteredGantt.tasks.length < gantt.tasks.length ? (
            <span className="ml-2 text-xs text-[var(--color-tertiary)]">
              ({filteredGantt.tasks.length} de {gantt.tasks.length} visibles)
            </span>
          ) : null}
        </header>
        {loadingGantt ? (
          <Skeleton className="h-[360px] w-full" />
        ) : filteredGantt && filteredGantt.tasks.length > 0 ? (
          <GanttView data={filteredGantt} />
        ) : (
          <div className="p-6 text-center text-sm text-[var(--color-tertiary)]">
            Sin datos para el Gantt con los filtros activos.
          </div>
        )}
      </section>
    ),
    [filteredGantt, gantt, loadingGantt],
  );

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      {/* ENH-162: acciones (Plantilla / Descargar / Importar / Nueva tarea)
          al nivel del título + breadcrumbs, por encima de la barra de filtros
          y agrupaciones. */}
      <header className="flex flex-wrap items-start justify-between gap-3">
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
        </div>
        <div className="flex flex-wrap items-center gap-2">
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

      {/* US-098 fix toolbar refactor: WBS / Área / MSP / Vista al mismo
          nivel, sobre el panel de la lista. Orden L→R: WBS+niveles,
          Área (multi-checklist), MSP, Vista (Lista/Dividida/Gantt). */}
      <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 shadow-[var(--shadow-sm)]">
        {/* WBS toggle + niveles 1/2/3/4/Manual integrados */}
        <div className="flex items-center gap-1 rounded border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5">
          <button
            type="button"
            onClick={toggleGroupByWbs}
            aria-pressed={groupByWbs}
            title="Agrupar por WBS"
            className={cn(
              "inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-medium",
              groupByWbs
                ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
            )}
          >
            <Network className="h-3.5 w-3.5" aria-hidden />
            WBS
          </button>
          {groupByWbs
            ? ([0, 1, 2, 3, 4, "manual"] as const).map((lvl) => {
                const active = wbsLevel === lvl;
                return (
                  <button
                    key={String(lvl)}
                    type="button"
                    onClick={() => applyWbsLevel(lvl)}
                    aria-pressed={active}
                    title={
                      lvl === "manual"
                        ? "Modo manual (chevrons)"
                        : lvl === 0
                          ? "Sólo nivel raíz (colapsa todo)"
                          : `Mostrar hasta nivel ${lvl}`
                    }
                    className={cn(
                      "h-7 rounded px-2 text-[11px] font-medium",
                      active
                        ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                        : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
                    )}
                  >
                    {lvl === "manual" ? "Manual" : lvl}
                  </button>
                );
              })
            : null}
        </div>
        {/* US-172: auto-numerar WBS (jerárquico + único). */}
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={handleRenumberWbs}
          loading={renumbering}
          title="Renumerar WBS de todo el proyecto: 1, 1.1, 1.2, 2, … (resuelve duplicados)"
        >
          <Network className="h-3.5 w-3.5" aria-hidden />
          Auto-WBS
        </Button>
        {/* Área dropdown checklist */}
        <AreaFilterDropdown
          areas={areas}
          selected={areaFilter}
          onChange={setAreaFilter}
          groupByArea={groupByArea}
          onToggleGroup={toggleGroupByArea}
        />
        {/* ENH-164: configurador de columnas (reemplaza el toggle "MSP"). */}
        <ColumnsDropdown value={colVis} onChange={setColVis} />
        {/* ENH-048 (movido): chips Hitos / Críticos / Retrasados. Antes
            vivían dentro del panel de lista y desaparecían en modo
            "solo Gantt"; ahora están al nivel de WBS/Área/MSP y filtran
            el Gantt en cualquier vista (condensan/expanden vía
            filteredGantt). */}
        <div className="flex flex-wrap items-center gap-1">
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
                  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
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
              Limpiar
            </button>
          ) : null}
        </div>
        {/* Mode toggle (Lista / Dividida / Gantt) */}
        <div
          role="radiogroup"
          aria-label="Vista del Plan"
          className="ml-auto inline-flex rounded border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
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
                  "inline-flex h-7 items-center gap-1 rounded px-2 text-xs font-medium",
                  active
                    ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                    : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
                )}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden />
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

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
        <div className="space-y-3">
          {/* ENH-094: warning soft cuando duración inferida supera el
              máximo recomendado (21d). No bloquea guardar. */}
          {(() => {
            const d = computeDurationDaysFromForm(
              newForm.start_date,
              newForm.end_date,
            );
            return d != null && d > 21 ? (
              <Banner variant="warning">
                Duración inferida: {d} días. El máximo recomendado son 21 para
                tareas operativas. Es válido para actividades macro, pero
                considera dividirla.
              </Banner>
            ) : null;
          })()}
          {/* ENH-135: WBS (pequeño) | Nombre */}
          <div className="grid gap-3 sm:grid-cols-[110px_1fr]">
            <FormField label="WBS">
              <Input
                value={newForm.wbs}
                onChange={(e) => setNewForm({ ...newForm, wbs: e.target.value })}
                placeholder="1.2.3"
              />
            </FormField>
            <FormField label="Nombre *">
              <Input
                value={newForm.name}
                onChange={(e) => setNewForm({ ...newForm, name: e.target.value })}
                required
              />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Inicio">
              <Input
                type="date"
                value={newForm.start_date}
                onChange={(e) => setNewForm({ ...newForm, start_date: e.target.value })}
              />
            </FormField>
            <FormField label="Fin">
              <Input
                type="date"
                value={newForm.end_date}
                onChange={(e) => setNewForm({ ...newForm, end_date: e.target.value })}
              />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Avance (0-100)">
              <Input
                type="number"
                min={0}
                max={100}
                value={newForm.progress}
                onChange={(e) => setNewForm({ ...newForm, progress: e.target.value })}
              />
            </FormField>
            <FormField label="Estado">
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
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Área responsable">
              <ProjectAreaPicker
                projectId={id}
                value={newForm.area_id || null}
                onChange={(v) => setNewForm({ ...newForm, area_id: v ?? "" })}
                placeholder="— Sin asignar —"
              />
            </FormField>
            <FormField label="Responsable">
              <PersonPicker
                projectId={id}
                value={newForm.assignee_actor_id || null}
                onChange={(v) => setNewForm({ ...newForm, assignee_actor_id: v ?? "" })}
                placeholder="— Sin responsable —"
              />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={newForm.is_critical}
                onChange={(e) => setNewForm({ ...newForm, is_critical: e.target.checked })}
              />
              <span className="text-xs text-[var(--color-secondary)]">
                Marcar como crítica
              </span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={newForm.is_milestone}
                onChange={(e) => setNewForm({ ...newForm, is_milestone: e.target.checked })}
              />
              <span className="text-xs text-[var(--color-secondary)]">Marcar hito</span>
            </label>
          </div>
          <FormField label="Hito relacionado (opcional)">
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
          </FormField>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Predecesoras (WBS separadas por coma)">
              <Input
                value={newForm.predecessors_csv}
                onChange={(e) =>
                  setNewForm({ ...newForm, predecessors_csv: e.target.value })
                }
                placeholder="1.1, 1.2"
              />
            </FormField>
            <FormField label="Sucesoras (auto)">
              <Input value="" disabled placeholder="Se calculan automáticamente" />
            </FormField>
          </div>
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
        <div className="space-y-3">
          {/* ENH-094: warning soft cuando duración inferida supera el
              máximo recomendado (21d). No bloquea guardar. */}
          {(() => {
            const d = computeDurationDaysFromForm(
              editForm.start_date,
              editForm.end_date,
            );
            return d != null && d > 21 ? (
              <Banner variant="warning">
                Duración inferida: {d} días. El máximo recomendado son 21 para
                tareas operativas. Es válido para actividades macro, pero
                considera dividirla.
              </Banner>
            ) : null;
          })()}
          {/* ENH-135: WBS (pequeño) | Nombre */}
          <div className="grid gap-3 sm:grid-cols-[110px_1fr]">
            <FormField label="WBS">
              <Input
                value={editForm.wbs}
                onChange={(e) => setEditForm({ ...editForm, wbs: e.target.value })}
                placeholder="1.2.3"
              />
            </FormField>
            <FormField label="Nombre *">
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                required
              />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Inicio">
              <Input
                type="date"
                value={editForm.start_date}
                onChange={(e) => setEditForm({ ...editForm, start_date: e.target.value })}
              />
            </FormField>
            <FormField label="Fin">
              <Input
                type="date"
                value={editForm.end_date}
                onChange={(e) => setEditForm({ ...editForm, end_date: e.target.value })}
              />
            </FormField>
          </div>
          {/* US-171: fecha de cierre real, base del cálculo de atraso. */}
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Fecha de cierre">
              <Input
                type="date"
                value={editForm.closed_at}
                onChange={(e) => setEditForm({ ...editForm, closed_at: e.target.value })}
              />
              <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
                Fecha real en que se cerró la actividad. Si es posterior a la
                fecha Fin, se marca como “Retrasada”. Al completar sin fecha,
                se usa hoy.
              </p>
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Avance (0-100)">
              <Input
                type="number"
                min={0}
                max={100}
                value={editForm.progress}
                onChange={(e) => setEditForm({ ...editForm, progress: e.target.value })}
              />
            </FormField>
            <FormField label="Estado">
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
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {/* US-098 / ENH-083: Área responsable con inline-create. */}
            <FormField label="Área responsable">
              <ProjectAreaPicker
                projectId={id}
                value={editForm.area_id || null}
                onChange={(v) => setEditForm({ ...editForm, area_id: v ?? "" })}
                placeholder="— Sin asignar —"
              />
            </FormField>
            {/* ENH-079 / BUG-056: Responsable = Actor del catálogo. */}
            <FormField label="Responsable">
              <PersonPicker
                projectId={id}
                value={editForm.assignee_actor_id || null}
                onChange={(v) => setEditForm({ ...editForm, assignee_actor_id: v ?? "" })}
                placeholder="— Sin responsable —"
              />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.is_critical}
                onChange={(e) => setEditForm({ ...editForm, is_critical: e.target.checked })}
              />
              <span className="text-xs text-[var(--color-secondary)]">
                Marcar como crítica
              </span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.is_milestone}
                onChange={(e) => setEditForm({ ...editForm, is_milestone: e.target.checked })}
              />
              <span className="text-xs text-[var(--color-secondary)]">Marcar hito</span>
            </label>
          </div>
          <FormField label="Hito relacionado (opcional)">
            <Select
              value={editForm.related_milestone_id}
              onChange={(e) =>
                setEditForm({ ...editForm, related_milestone_id: e.target.value })
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
          </FormField>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Predecesoras (WBS separadas por coma)">
              <Input
                value={editForm.predecessors_csv}
                onChange={(e) =>
                  setEditForm({ ...editForm, predecessors_csv: e.target.value })
                }
                placeholder="1.1, 1.2"
              />
            </FormField>
            <FormField label="Sucesoras (auto)">
              <Input
                value={(tasks.find((t) => t.id === editingId)?.successors ?? []).join(", ")}
                disabled
                placeholder="Se calculan automáticamente"
              />
            </FormField>
          </div>
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
