"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Download,
  Eye,
} from "lucide-react";

import {
  InlineSelectCell,
  InlineTextCell,
  InlineDateCell,
} from "@/components/inline-select-cell";
import { ItemPreviewModal } from "@/components/item-preview-modal";
import { RaidEditModal } from "@/components/raid-edit-modal";
import { Trash2, Pencil } from "lucide-react";
import { listAreasByProject } from "@/lib/api/areas";
import { listEligibleActors } from "@/lib/api/project-directory";
import type { InlineOption } from "@/components/inline-select-cell";
import {
  RaidKanban,
  type KanbanColumn,
  type KanbanItem,
} from "@/components/raid-kanban";
import {
  KIND_NEW_LABEL,
  RaidCreateModal,
  type RaidKind,
} from "@/components/raid-create-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiBase } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import {
  ISSUE_FINAL_STATUSES,
  ISSUE_STATUS_LABEL,
  ISSUE_STATUS_ORDER,
  ISSUE_TYPE_LABEL,
  RISK_FINAL_STATUSES,
  RISK_STATUS_LABEL,
  RISK_STATUS_ORDER,
  listIssues,
  listRisks,
  updateIssue,
  updateRisk,
  deleteIssue,
  deleteRisk,
  RAID_STATUS_BADGE,
  RAID_STATUS_LABEL,
  onHoldDays,
  type Issue,
  type IssueStatus,
  type IssueType,
  type IssueUpdateBody,
  type RaidStatus,
  type Risk,
  type RiskStatus,
  type RiskUpdateBody,
} from "@/lib/api/modules";
import { cn } from "@/lib/cn";

type Tab = RaidKind;

const TABS: { id: Tab; letter: string; label: string; color: string }[] = [
  { id: "risks", letter: "R", label: "Riesgos", color: "var(--color-danger-fg)" },
  { id: "actions", letter: "A", label: "Acciones", color: "var(--color-info-fg)" },
  { id: "incidents", letter: "I", label: "Incidentes", color: "var(--color-warning-fg)" },
  { id: "decisions", letter: "D", label: "Decisiones", color: "var(--color-success-fg)" },
];

// Per DEC-007: en backend los tipos son action/issue/decision.
// En UI etiquetamos 'issue' como "Incidente" (I de RAID).
const INCIDENT_LABEL = "Incidente";

function tabFromParam(v: string | null): Tab {
  if (v === "risks" || v === "actions" || v === "incidents" || v === "decisions")
    return v;
  return "risks";
}

function RaidInner() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>(tabFromParam(searchParams.get("tab")));

  const [risks, setRisks] = useState<Risk[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ENH-026: modal de creación + filtros avanzados consolidados (antes
  // vivían en las rutas separadas /risks y /issues, borradas en este ENH).
  const [createOpen, setCreateOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityMin, setSeverityMin] = useState<number | "">("");
  const [priorityMin, setPriorityMin] = useState<number | "">("");
  // ENH-166: por default sólo activos (oculta finalizados). Toggle global.
  const [includeFinalized, setIncludeFinalized] = useState(false);
  // ENH-167: filtro por área (id; "" = todas).
  const [areaFilter, setAreaFilter] = useState<string>("");
  // US-174: vista Lista vs Kanban (por tab). Persistida en la URL.
  const [view, setView] = useState<"list" | "board">(
    searchParams.get("view") === "board" ? "board" : "list",
  );
  const [kanbanBusyId, setKanbanBusyId] = useState<string | null>(null);
  // ENH-171: menú "Exportar ▾" (agrupa export por tipo + 4 hojas).
  const [exportOpen, setExportOpen] = useState(false);
  const [exportEl, setExportEl] = useState<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!exportOpen) return;
    function onDoc(e: MouseEvent) {
      if (exportEl && !exportEl.contains(e.target as Node)) setExportOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [exportOpen, exportEl]);

  function setViewAndUrl(v: "list" | "board") {
    setView(v);
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", v);
    router.replace(`/pmo/projects/${id}/raid?${params.toString()}`);
  }

  // Reset filtros al cambiar de tab (los valores legales dependen del kind).
  function switchTab(next: Tab) {
    setTabAndUrl(next);
    setStatusFilter("");
    setSeverityMin("");
    setPriorityMin("");
  }

  function setTabAndUrl(next: Tab) {
    setTab(next);
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", next);
    router.replace(`/pmo/projects/${id}/raid?${params.toString()}`);
  }

  function reload() {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([listRisks(id), listIssues(id)])
      .then(([r, i]) => {
        if (cancelled) return;
        setRisks(r);
        setIssues(i);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Error al cargar RAID");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }

  useEffect(() => {
    const cleanup = reload();
    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const actions = useMemo(() => issues.filter((i) => i.type === "action"), [issues]);
  const incidents = useMemo(() => issues.filter((i) => i.type === "issue"), [issues]);
  const decisions = useMemo(() => issues.filter((i) => i.type === "decision"), [issues]);

  // ENH-026: filtros avanzados aplicados al tab activo.
  const filteredRisks = useMemo(() => {
    const out = risks.filter((r) => {
      // ENH-166: oculta finalizados salvo toggle.
      if (!includeFinalized && RISK_FINAL_STATUSES.includes(r.status)) return false;
      if (statusFilter && r.status !== statusFilter) return false;
      if (severityMin !== "" && (r.severity ?? 0) < Number(severityMin))
        return false;
      if (areaFilter && r.area_id !== areaFilter) return false; // ENH-167
      return true;
    });
    // ENH-166: orden por fase de estado, luego severidad desc (no alfabético).
    return out.sort((a, b) => {
      const pa = RISK_STATUS_ORDER.indexOf(a.status);
      const pb = RISK_STATUS_ORDER.indexOf(b.status);
      if (pa !== pb) return pa - pb;
      return (b.severity ?? 0) - (a.severity ?? 0);
    });
  }, [risks, statusFilter, severityMin, includeFinalized, areaFilter]);

  function filterIssues(list: Issue[]): Issue[] {
    const out = list.filter((it) => {
      if (!includeFinalized && ISSUE_FINAL_STATUSES.includes(it.status)) return false;
      if (statusFilter && it.status !== statusFilter) return false;
      if (priorityMin !== "" && (it.priority ?? 0) < Number(priorityMin))
        return false;
      if (areaFilter && it.area_id !== areaFilter) return false; // ENH-167
      return true;
    });
    // ENH-166: orden por fase de estado, luego prioridad desc.
    return out.sort((a, b) => {
      const pa = ISSUE_STATUS_ORDER.indexOf(a.status);
      const pb = ISSUE_STATUS_ORDER.indexOf(b.status);
      if (pa !== pb) return pa - pb;
      return (b.priority ?? 0) - (a.priority ?? 0);
    });
  }

  const filteredActions = useMemo(
    () => filterIssues(actions),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [actions, statusFilter, priorityMin, includeFinalized, areaFilter],
  );
  const filteredIncidents = useMemo(
    () => filterIssues(incidents),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [incidents, statusFilter, priorityMin, includeFinalized, areaFilter],
  );
  const filteredDecisions = useMemo(
    () => filterIssues(decisions),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [decisions, statusFilter, priorityMin, includeFinalized, areaFilter],
  );

  const counts: Record<Tab, number> = {
    risks: risks.length,
    actions: actions.length,
    incidents: incidents.length,
    decisions: decisions.length,
  };

  // ENH-167: áreas presentes en los items cargados (para el filtro de área).
  const areaOptions = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of risks) if (r.area_id && r.area?.name) m.set(r.area_id, r.area.name);
    for (const it of issues) if (it.area_id && it.area?.name) m.set(it.area_id, it.area.name);
    return Array.from(m, ([aid, name]) => ({ id: aid, name })).sort((a, b) =>
      a.name.localeCompare(b.name, "es"),
    );
  }, [risks, issues]);

  // US-174: columnas e items del Kanban para el tab activo. El board muestra
  // TODAS las fases como columnas (ignora el toggle de finalizados y el filtro
  // de estado), pero respeta severidad/prioridad y área.
  const isRiskTab = tab === "risks";
  const boardColumns: KanbanColumn[] = useMemo(
    () =>
      (isRiskTab ? RISK_STATUS_ORDER : ISSUE_STATUS_ORDER).map((s) => ({
        id: s,
        label: isRiskTab
          ? RISK_STATUS_LABEL[s as RiskStatus]
          : ISSUE_STATUS_LABEL[s as IssueStatus],
      })),
    [isRiskTab],
  );
  const boardItems: KanbanItem[] = useMemo(() => {
    if (isRiskTab) {
      return risks
        .filter(
          (r) =>
            (severityMin === "" || (r.severity ?? 0) >= Number(severityMin)) &&
            (!areaFilter || r.area_id === areaFilter),
        )
        .map((r) => ({
          id: r.id,
          status: r.status,
          folio: r.folio,
          title: r.title,
          href: `/pmo/projects/${id}/raid/${r.id}?type=risk`,
          accent: <SeverityBadge severity={r.severity} />,
        }));
    }
    const src = tab === "actions" ? actions : tab === "incidents" ? incidents : decisions;
    return src
      .filter(
        (it) =>
          (priorityMin === "" || (it.priority ?? 0) >= Number(priorityMin)) &&
          (!areaFilter || it.area_id === areaFilter),
      )
      .map((it) => ({
        id: it.id,
        status: it.status,
        folio: it.folio,
        title: it.title,
        href: `/pmo/projects/${id}/raid/${it.id}?type=${it.type}`,
        accent: it.priority ? (
          <span className="rounded bg-[var(--color-subtle)] px-1 text-[10px] font-medium text-[var(--color-secondary)]">
            P{it.priority}
          </span>
        ) : null,
      }));
  }, [isRiskTab, risks, actions, incidents, decisions, tab, severityMin, priorityMin, areaFilter, id]);

  // Fase 2: cambio de estado OPTIMISTA (Kanban + estado inline en listas).
  // Aplica el nuevo estado local de inmediato; revierte si el PATCH falla.
  async function handleBoardMove(itemId: string, toStatus: string) {
    setError(null);
    // US-179: al pasar a On Hold se exige una razón de detención. La
    // dependencia (área + responsable) se completa en el form de edición.
    let onHoldReason: string | undefined;
    if (toStatus === "on_hold") {
      const reason = window.prompt(
        "Razón de detención (obligatoria para poner On Hold). " +
          "La dependencia (área/responsable) se completa en Editar.",
        "",
      );
      if (reason === null || reason.trim() === "") return;
      onHoldReason = reason.trim();
    }
    if (isRiskTab) {
      const patch: RiskUpdateBody = { status: toStatus as RiskStatus };
      if (onHoldReason) patch.on_hold_reason = onHoldReason;
      const prev = risks.find((r) => r.id === itemId);
      setRisks((rows) =>
        rows.map((r) => (r.id === itemId ? { ...r, ...patch } : r)),
      );
      setKanbanBusyId(itemId);
      try {
        const updated = await updateRisk(itemId, patch);
        setRisks((rows) =>
          rows.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)),
        );
      } catch (err) {
        if (prev) {
          setRisks((rows) => rows.map((r) => (r.id === itemId ? prev : r)));
        }
        setError(
          err instanceof ApiError ? err.message : "No se pudo mover la tarjeta",
        );
      } finally {
        setKanbanBusyId(null);
      }
    } else {
      const patch: IssueUpdateBody = { status: toStatus as IssueStatus };
      if (onHoldReason) patch.on_hold_reason = onHoldReason;
      const prev = issues.find((i) => i.id === itemId);
      setIssues((rows) =>
        rows.map((i) => (i.id === itemId ? { ...i, ...patch } : i)),
      );
      setKanbanBusyId(itemId);
      try {
        const updated = await updateIssue(itemId, patch);
        setIssues((rows) =>
          rows.map((i) => (i.id === updated.id ? { ...i, ...updated } : i)),
        );
      } catch (err) {
        if (prev) {
          setIssues((rows) => rows.map((i) => (i.id === itemId ? prev : i)));
        }
        setError(
          err instanceof ApiError ? err.message : "No se pudo mover la tarjeta",
        );
      } finally {
        setKanbanBusyId(null);
      }
    }
  }

  // ENH-176: edición inline de probabilidad/impacto en riesgos (optimista).
  // El backend recomputa severity = P × I; localmente la recomputamos para
  // que el badge reaccione de inmediato.
  async function handleRiskPatch(
    id: string,
    patch: { probability?: number; impact?: number },
  ) {
    setError(null);
    const prev = risks.find((r) => r.id === id);
    setRisks((rows) =>
      rows.map((r) => {
        if (r.id !== id) return r;
        const merged = { ...r, ...patch };
        merged.severity =
          (merged.probability ?? 0) * (merged.impact ?? 0) || null;
        return merged;
      }),
    );
    setKanbanBusyId(id);
    try {
      const updated = await updateRisk(id, patch);
      setRisks((rows) =>
        rows.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)),
      );
    } catch (err) {
      if (prev) setRisks((rows) => rows.map((r) => (r.id === id ? prev : r)));
      setError(
        err instanceof ApiError ? err.message : "No se pudo actualizar el riesgo",
      );
    } finally {
      setKanbanBusyId(null);
    }
  }

  // US-178: edición inline genérica (cualquier campo) + borrar + modal editar.
  const [editItem, setEditItem] = useState<
    { kind: "risk"; item: Risk } | { kind: "issue"; item: Issue } | null
  >(null);
  // US-178: opciones para los dropdowns inline de Área y Responsable
  // (cargadas una vez; BUG-086 las hace consistentes con la cascada).
  const [areaOpts, setAreaOpts] = useState<InlineOption[]>([]);
  const [actorOpts, setActorOpts] = useState<InlineOption[]>([]);
  useEffect(() => {
    listAreasByProject(id)
      .then((rows) =>
        setAreaOpts(rows.map((a) => ({ value: a.id, label: a.name }))),
      )
      .catch(() => setAreaOpts([]));
    listEligibleActors(id)
      .then((rows) =>
        setActorOpts(rows.map((a) => ({ value: a.id, label: a.name }))),
      )
      .catch(() => setActorOpts([]));
  }, [id]);

  async function patchRiskFields(id: string, patch: RiskUpdateBody) {
    setError(null);
    const prev = risks.find((r) => r.id === id);
    setRisks((rows) =>
      rows.map((r) => (r.id === id ? ({ ...r, ...patch } as Risk) : r)),
    );
    try {
      const updated = await updateRisk(id, patch);
      setRisks((rows) =>
        rows.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)),
      );
    } catch (err) {
      if (prev) setRisks((rows) => rows.map((r) => (r.id === id ? prev : r)));
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar");
    }
  }

  async function patchIssueFields(id: string, patch: IssueUpdateBody) {
    setError(null);
    const prev = issues.find((i) => i.id === id);
    setIssues((rows) =>
      rows.map((i) => (i.id === id ? ({ ...i, ...patch } as Issue) : i)),
    );
    try {
      const updated = await updateIssue(id, patch);
      setIssues((rows) =>
        rows.map((i) => (i.id === updated.id ? { ...i, ...updated } : i)),
      );
    } catch (err) {
      if (prev) setIssues((rows) => rows.map((i) => (i.id === id ? prev : i)));
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar");
    }
  }

  async function removeRisk(id: string) {
    if (!window.confirm("¿Eliminar este riesgo?")) return;
    const prev = risks;
    setRisks((rows) => rows.filter((r) => r.id !== id));
    try {
      await deleteRisk(id);
    } catch (err) {
      setRisks(prev);
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    }
  }

  async function removeIssue(id: string) {
    if (!window.confirm("¿Eliminar este ítem?")) return;
    const prev = issues;
    setIssues((rows) => rows.filter((i) => i.id !== id));
    try {
      await deleteIssue(id);
    } catch (err) {
      setIssues(prev);
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    }
  }

  // ENH-152: Export RAID = descarga autenticada del XLSX (4 hojas ES:
  // Riesgos/Acciones/Incidencias/Decisiones) del endpoint /raid/export — el
  // MISMO archivo que el botón del módulo Documentos. El filename
  // ('RAID-[Nombre Proyecto].xlsx') viene en el Content-Disposition.
  const [exporting, setExporting] = useState(false);

  async function downloadRaid(only?: Tab) {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const headers: Record<string, string> = {
        Accept: "application/octet-stream",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      // ENH-168: `only` → XLSX de una sola hoja para el tipo actual.
      const qs = only ? `?only=${only}` : "";
      const res = await fetch(
        `${apiBase()}/api/v1/projects/${id}/raid/export${qs}`,
        {
          method: "GET",
          headers,
          credentials: "include",
        },
      );
      if (!res.ok) {
        throw new ApiError(
          res.status,
          "EXPORT_FAILED",
          `Exportación falló (HTTP ${res.status})`,
        );
      }
      const cd = res.headers.get("Content-Disposition") ?? "";
      const match = /filename="([^"]+)"/.exec(cd);
      const name = match ? match[1] : `RAID-${id}.xlsx`;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo exportar el RAID",
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
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
            <span>RAID</span>
          </nav>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            RAID
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Vista consolidada: Riesgos · Acciones · Incidentes · Decisiones.
            Click en una fila abre el módulo correspondiente para editar.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] bg-[var(--color-primary)] px-3 text-sm font-medium text-[var(--color-inverse)] shadow-[var(--shadow-sm)] hover:bg-[var(--color-primary-hover,var(--color-primary))]"
          >
            + {KIND_NEW_LABEL[tab]}
          </button>
          {/* ENH-168 + ENH-171: menú "Exportar ▾" (export por tipo + 4 hojas). */}
          <div ref={setExportEl} className="relative">
            <button
              type="button"
              onClick={() => setExportOpen((v) => !v)}
              disabled={exporting}
              aria-haspopup="menu"
              aria-expanded={exportOpen}
              className="inline-flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-subtle)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Download className="h-4 w-4" aria-hidden />
              {exporting ? "Exportando…" : "Exportar"}
              <ChevronDown className="h-3.5 w-3.5" aria-hidden />
            </button>
            {exportOpen ? (
              <div
                role="menu"
                className="absolute right-0 z-20 mt-1 w-60 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-1 shadow-[var(--shadow-md)]"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setExportOpen(false);
                    void downloadRaid(tab);
                  }}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-[var(--color-primary)] hover:bg-[var(--color-subtle)]"
                >
                  <Download className="h-4 w-4" aria-hidden />
                  Sólo {TABS.find((t) => t.id === tab)?.label ?? "tipo"} (1 hoja)
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setExportOpen(false);
                    void downloadRaid();
                  }}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-[var(--color-primary)] hover:bg-[var(--color-subtle)]"
                >
                  <Download className="h-4 w-4" aria-hidden />
                  RAID completo (4 hojas)
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <div
        role="tablist"
        aria-label="Secciones RAID"
        className="flex flex-wrap gap-2"
      >
        {TABS.map((t) => {
          const active = t.id === tab;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => switchTab(t.id)}
              className={cn(
                "inline-flex items-center gap-2 rounded-[var(--radius-md)] border px-2 py-1.5 text-sm transition-colors",
                active
                  ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "border-[var(--border-default)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
              )}
            >
              <span
                className="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold"
                style={{
                  backgroundColor: active ? "var(--color-inverse)" : t.color,
                  color: active ? t.color : "var(--color-inverse)",
                }}
                aria-hidden
              >
                {t.letter}
              </span>
              <span>{t.label}</span>
              <Badge variant={active ? "neutral" : "neutral"}>
                {loading ? "…" : counts[t.id]}
              </Badge>
            </button>
          );
        })}
      </div>

      {/* US-174: toggle Lista / Kanban (por tab). */}
      <div className="flex w-fit items-center gap-1 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5">
        {(["list", "board"] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setViewAndUrl(v)}
            aria-pressed={view === v}
            className={cn(
              "rounded px-3 py-1 text-xs font-medium",
              view === v
                ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
            )}
          >
            {v === "list" ? "Lista" : "Kanban"}
          </button>
        ))}
      </div>

      {/* ENH-026: filtros avanzados (status + severity/priority)
          consolidados — antes vivían en /risks y /issues. */}
      <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] px-2 py-1.5 text-[13px]">
        <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
          Filtros
        </span>
        <select
          aria-label="Estado"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-8 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[12px] text-[var(--color-primary)]"
        >
          <option value="">Todos los estados</option>
          {tab === "risks"
            ? (Object.keys(RISK_STATUS_LABEL) as RiskStatus[]).map((s) => (
                <option key={s} value={s}>
                  {RISK_STATUS_LABEL[s]}
                </option>
              ))
            : (Object.keys(ISSUE_STATUS_LABEL) as IssueStatus[]).map((s) => (
                <option key={s} value={s}>
                  {ISSUE_STATUS_LABEL[s]}
                </option>
              ))}
        </select>
        {tab === "risks" ? (
          <select
            aria-label="Severidad mínima"
            value={severityMin === "" ? "" : String(severityMin)}
            onChange={(e) =>
              setSeverityMin(e.target.value === "" ? "" : Number(e.target.value))
            }
            className="h-8 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[12px] text-[var(--color-primary)]"
          >
            <option value="">Cualquier severidad</option>
            <option value="1">Baja (≥ 1)</option>
            <option value="6">Media (≥ 6)</option>
            <option value="13">Alta (≥ 13)</option>
          </select>
        ) : (
          <select
            aria-label="Prioridad mínima"
            value={priorityMin === "" ? "" : String(priorityMin)}
            onChange={(e) =>
              setPriorityMin(e.target.value === "" ? "" : Number(e.target.value))
            }
            className="h-8 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[12px] text-[var(--color-primary)]"
          >
            <option value="">Cualquier prioridad</option>
            <option value="1">P1+ (Crítica)</option>
            <option value="2">P2+ (Alta)</option>
            <option value="3">P3+ (Media)</option>
            <option value="4">P4+ (Baja)</option>
          </select>
        )}
        {/* ENH-167: filtro por área. */}
        {areaOptions.length > 0 ? (
          <select
            aria-label="Área"
            value={areaFilter}
            onChange={(e) => setAreaFilter(e.target.value)}
            className="h-8 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[12px] text-[var(--color-primary)]"
          >
            <option value="">Todas las áreas</option>
            {areaOptions.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        ) : null}
        {/* ENH-166: toggle para incluir finalizados (oculto por default). */}
        <label className="ml-auto inline-flex items-center gap-1.5 text-[12px] text-[var(--color-secondary)]">
          <input
            type="checkbox"
            checked={includeFinalized}
            onChange={(e) => setIncludeFinalized(e.target.checked)}
          />
          Mostrar finalizados
        </label>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : view === "board" ? (
        <div className="space-y-2">
          {/* ENH-171: el board muestra todas las fases (ignora el toggle
              "Mostrar finalizados", que sólo aplica a la vista Lista). */}
          <p className="text-[11px] text-[var(--color-tertiary)]">
            El tablero muestra <strong>todas las fases</strong> (incluye
            finalizados). Arrastra una tarjeta entre columnas para cambiar su
            estado.
          </p>
          <RaidKanban
            columns={boardColumns}
            items={boardItems}
            onMove={handleBoardMove}
            busyId={kanbanBusyId}
          />
        </div>
      ) : tab === "risks" ? (
        <RisksSection
          rows={filteredRisks}
          projectId={id}
          areaOptions={areaOpts}
          actorOptions={actorOpts}
          onStatusChange={handleBoardMove}
          onRiskPatch={handleRiskPatch}
          onPatch={patchRiskFields}
          onDelete={removeRisk}
          onEdit={(r) => setEditItem({ kind: "risk", item: r })}
        />
      ) : (
        <IssuesSection
          rows={
            tab === "actions"
              ? filteredActions
              : tab === "incidents"
                ? filteredIncidents
                : filteredDecisions
          }
          projectId={id}
          sectionLabel={
            tab === "actions"
              ? "Acciones"
              : tab === "incidents"
                ? "Incidentes"
                : "Decisiones"
          }
          issueType={
            tab === "actions" ? "action" : tab === "incidents" ? "issue" : "decision"
          }
          areaOptions={areaOpts}
          actorOptions={actorOpts}
          onStatusChange={handleBoardMove}
          onPatch={patchIssueFields}
          onDelete={removeIssue}
          onEdit={(i) => setEditItem({ kind: "issue", item: i })}
        />
      )}

      {editItem ? (
        editItem.kind === "risk" ? (
          <RaidEditModal
            kind="risk"
            item={editItem.item}
            onClose={() => setEditItem(null)}
            onSaved={(updated) => {
              setRisks((prev) =>
                prev.map((x) => (x.id === updated.id ? { ...x, ...updated } : x)),
              );
            }}
          />
        ) : (
          <RaidEditModal
            kind="issue"
            item={editItem.item}
            onClose={() => setEditItem(null)}
            onSaved={(updated) => {
              setIssues((prev) =>
                prev.map((x) => (x.id === updated.id ? { ...x, ...updated } : x)),
              );
            }}
          />
        )
      ) : null}

      <RaidCreateModal
        projectId={id}
        kind={tab}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          setCreateOpen(false);
          reload();
        }}
      />
    </div>
  );
}

function severityToneOf(sev: number | null): "danger" | "warning" | "success" | "neutral" {
  if (sev === null) return "neutral";
  if (sev >= 13) return "danger";
  if (sev >= 6) return "warning";
  return "success";
}

// US-179: tag de color del estado RAID.
function RaidStatusBadge({ status }: { status: RaidStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold",
        RAID_STATUS_BADGE[status] ?? "bg-[var(--color-subtle)]",
      )}
    >
      {RAID_STATUS_LABEL[status] ?? status}
    </span>
  );
}

// US-178/US-179: estado con tag de color, editable inline on-click. Para
// On Hold delega al handler (que pide la razón).
function StatusInlineCell({
  status,
  onChange,
  ariaLabel,
}: {
  status: RaidStatus;
  onChange: (s: string) => void;
  ariaLabel?: string;
}) {
  const [editing, setEditing] = useState(false);
  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        title="Estado (clic para editar)"
        aria-label={ariaLabel}
        className="rounded focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-strong)]"
      >
        <RaidStatusBadge status={status} />
      </button>
    );
  }
  return (
    <select
      autoFocus
      value={status}
      aria-label={ariaLabel}
      onChange={(e) => {
        onChange(e.target.value);
        setEditing(false);
      }}
      onBlur={() => setEditing(false)}
      className="rounded border border-[var(--border-default)] bg-[var(--color-surface)] px-1 py-0.5 text-xs text-[var(--color-secondary)] focus:outline-none"
    >
      {(Object.keys(RAID_STATUS_LABEL) as RaidStatus[]).map((s) => (
        <option key={s} value={s}>
          {RAID_STATUS_LABEL[s]}
        </option>
      ))}
    </select>
  );
}

// US-178: acciones por fila — vista rápida, editar (modal) y borrar.
function RowActions({
  onPreview,
  onEdit,
  onDelete,
  label,
}: {
  onPreview: () => void;
  onEdit: () => void;
  onDelete: () => void;
  label: string;
}) {
  return (
    <div className="flex items-center justify-end gap-1">
      <button
        type="button"
        onClick={onPreview}
        aria-label={`Vista rápida ${label}`}
        title="Vista rápida"
        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
      >
        <Eye className="h-3.5 w-3.5" aria-hidden />
      </button>
      <button
        type="button"
        onClick={onEdit}
        aria-label={`Editar ${label}`}
        title="Editar"
        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
      >
        <Pencil className="h-3.5 w-3.5" aria-hidden />
      </button>
      <button
        type="button"
        onClick={onDelete}
        aria-label={`Eliminar ${label}`}
        title="Eliminar"
        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
      >
        <Trash2 className="h-3.5 w-3.5" aria-hidden />
      </button>
    </div>
  );
}

// US-179: indicador compacto de días detenido (On Hold).
function OnHoldInfo({
  status,
  since,
}: {
  status: RaidStatus;
  since: string | null;
}) {
  if (status !== "on_hold") return null;
  const days = onHoldDays(since);
  if (days === null) return null;
  return (
    <span
      className="ml-1 rounded bg-[var(--color-warning-bg)] px-1 text-[10px] font-medium text-[var(--color-warning-fg)]"
      title={`Detenido desde ${since}`}
    >
      {days}d
    </span>
  );
}

// ENH-007: matriz P×I inline en la pestaña Riesgos del RAID, para que
// no sea necesario abrir /risks como página separada.
// ENH-061: celdas clicables → filtran tabla por (probability, impact).
function RiskMatrix({
  rows,
  selected,
  onCellToggle,
}: {
  rows: Risk[];
  selected: { p: number; i: number } | null;
  onCellToggle: (p: number, i: number) => void;
}) {
  const grid: number[][] = useMemo(() => {
    const g: number[][] = Array.from({ length: 5 }, () => Array(5).fill(0));
    for (const r of rows) {
      if (r.probability && r.impact) g[r.probability - 1][r.impact - 1]++;
    }
    return g;
  }, [rows]);
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-1 text-sm font-semibold text-[var(--color-primary)]">
        Matriz P × I
      </h2>
      <p className="mb-3 text-xs text-[var(--color-tertiary)]">
        Click en una celda para filtrar la tabla por esa combinación.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full max-w-xl border-collapse text-center text-xs">
          <thead>
            <tr>
              <th className="p-2 text-left text-[11px] uppercase text-[var(--color-tertiary)]">
                P / I
              </th>
              {[1, 2, 3, 4, 5].map((i) => (
                <th key={i} className="p-2 text-[11px] text-[var(--color-tertiary)]">
                  {i}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.map((row, p) => (
              <tr key={p}>
                <td className="p-2 text-left text-[11px] text-[var(--color-tertiary)]">
                  {p + 1}
                </td>
                {row.map((count, i) => {
                  const sev = (p + 1) * (i + 1);
                  const tone = severityToneOf(sev);
                  const bg =
                    tone === "danger"
                      ? "var(--color-danger-bg)"
                      : tone === "warning"
                        ? "var(--color-warning-bg)"
                        : "var(--color-success-bg)";
                  const border =
                    tone === "danger"
                      ? "var(--color-danger-border)"
                      : tone === "warning"
                        ? "var(--color-warning-border)"
                        : "var(--color-success-border)";
                  const isActive =
                    selected && selected.p === p + 1 && selected.i === i + 1;
                  return (
                    <td
                      key={i}
                      className="h-12 w-12 border p-0 text-[var(--color-primary)]"
                      style={{ backgroundColor: bg, borderColor: border }}
                    >
                      <button
                        type="button"
                        onClick={() => onCellToggle(p + 1, i + 1)}
                        aria-pressed={Boolean(isActive)}
                        aria-label={`Filtrar P=${p + 1}, I=${i + 1} (${count} riesgos)`}
                        title={`Severidad ${sev} · ${count} riesgo(s)`}
                        className={cn(
                          "h-full w-full cursor-pointer font-semibold tabular-nums transition hover:opacity-80 focus:outline-none focus-visible:outline-none",
                          isActive
                            ? "ring-2 ring-inset ring-[var(--color-accent)]"
                            : "",
                        )}
                      >
                        {count}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function RisksSection({
  rows,
  projectId,
  areaOptions,
  actorOptions,
  onStatusChange,
  onRiskPatch,
  onPatch,
  onDelete,
  onEdit,
}: {
  rows: Risk[];
  projectId: string;
  areaOptions: InlineOption[];
  actorOptions: InlineOption[];
  // US-175: cambio de estado inline (reusa el handler de Kanban → pide la
  // razón de detención al pasar a On Hold).
  onStatusChange?: (id: string, status: string) => void;
  // ENH-176: edición inline de probabilidad/impacto (severity = P × I).
  onRiskPatch?: (id: string, patch: { probability?: number; impact?: number }) => void;
  // US-178: patch inline genérico + borrar + abrir form de edición.
  onPatch: (id: string, patch: RiskUpdateBody) => void;
  onDelete: (id: string) => void;
  onEdit: (r: Risk) => void;
}) {
  const [preview, setPreview] = useState<Risk | null>(null);
  const areaOpts = (r: Risk): InlineOption[] => {
    const opts = [...areaOptions];
    if (r.area_id && !opts.some((o) => o.value === r.area_id))
      opts.unshift({ value: r.area_id, label: r.area?.name ?? "(área)" });
    return [{ value: "", label: "— sin área —" }, ...opts];
  };
  const respOpts = (r: Risk): InlineOption[] => {
    const opts = [...actorOptions];
    if (r.owner_actor_id && !opts.some((o) => o.value === r.owner_actor_id))
      opts.unshift({
        value: r.owner_actor_id,
        label: r.responsible_name ?? "(responsable)",
      });
    return [{ value: "", label: "— sin responsable —" }, ...opts];
  };
  // ENH-061: filtro por celda P×I de la matriz.
  const [cellFilter, setCellFilter] = useState<
    { p: number; i: number } | null
  >(null);
  // Matriz P×I colapsada por default (ocupaba mucho espacio en la principal);
  // un toggle la muestra. Si hay un filtro de celda activo, se mantiene abierta.
  const [showMatrix, setShowMatrix] = useState(false);
  void projectId;

  function toggleCell(p: number, i: number) {
    setCellFilter((prev) =>
      prev && prev.p === p && prev.i === i ? null : { p, i },
    );
  }

  const filteredRows = useMemo(() => {
    if (!cellFilter) return rows;
    return rows.filter(
      (r) => r.probability === cellFilter.p && r.impact === cellFilter.i,
    );
  }, [rows, cellFilter]);
  const { sortedRows: visibleRows, ctrl: riskSortCtrl } = useSortableRows<Risk>(filteredRows);

  return (
    <div className="space-y-3">
      {/* Toggle de la matriz P×I — colapsada por default para no robar
          espacio a la lista principal. */}
      <button
        type="button"
        onClick={() => setShowMatrix((v) => !v)}
        aria-expanded={showMatrix || cellFilter !== null}
        className="inline-flex items-center gap-1 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]"
      >
        {showMatrix || cellFilter ? (
          <ChevronDown className="h-3.5 w-3.5" aria-hidden />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" aria-hidden />
        )}
        Matriz P × I
      </button>
      {showMatrix || cellFilter ? (
        <RiskMatrix
          rows={rows}
          selected={cellFilter}
          onCellToggle={toggleCell}
        />
      ) : null}
      {cellFilter ? (
        <div className="flex items-center gap-2 text-xs">
          <span className="text-[var(--color-tertiary)]">Filtro:</span>
          <span className="inline-flex items-center gap-1 rounded-full border border-[var(--color-accent)] bg-[var(--color-accent-bg,var(--color-subtle))] px-2 py-0.5 text-[var(--color-accent)]">
            P={cellFilter.p}, I={cellFilter.i}
            <button
              type="button"
              onClick={() => setCellFilter(null)}
              aria-label="Quitar filtro de matriz"
              className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full hover:bg-[var(--color-subtle)]"
            >
              ×
            </button>
          </span>
          <span className="text-[var(--color-tertiary)]">
            {visibleRows.length} riesgo(s)
          </span>
        </div>
      ) : null}
      {rows.length === 0 ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
          Sin riesgos registrados. Usa el botón <strong>+ Nuevo riesgo</strong>
          {" "}arriba para crear el primero.
        </div>
      ) : (
        <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <tr>
                  <SortableTh<Risk> sortKey="folio" getter={(r) => r.folio} ctrl={riskSortCtrl}>Folio</SortableTh>
                  <SortableTh<Risk> sortKey="title" getter={(r) => r.title} ctrl={riskSortCtrl}>Título</SortableTh>
                  <SortableTh<Risk> sortKey="area" getter={(r) => (r as any).area?.name ?? ""} ctrl={riskSortCtrl}>Área</SortableTh>
                  <SortableTh<Risk> sortKey="responsible" getter={(r) => r.responsible_name ?? ""} ctrl={riskSortCtrl}>Responsable</SortableTh>
                  <SortableTh<Risk> sortKey="severity" getter={(r) => r.severity ?? 0} ctrl={riskSortCtrl}>Severidad</SortableTh>
                  <SortableTh<Risk> sortKey="status" getter={(r) => r.status} ctrl={riskSortCtrl}>Estado</SortableTh>
                  <SortableTh<Risk> sortKey="identified" getter={(r) => (r as any).identified_at ?? ""} ctrl={riskSortCtrl}>F. Creación</SortableTh>
                  <SortableTh<Risk> sortKey="due" getter={(r) => r.due_date ?? ""} ctrl={riskSortCtrl}>F. Compromiso</SortableTh>
                  <th className="px-2 py-1.5 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                  >
                    {/* US-178: folio = único link que abre el ticket. */}
                    <td className="px-2 py-1.5 font-mono text-xs text-[var(--color-tertiary)]">
                      <Link
                        href={`/pmo/projects/${projectId}/raid/${r.id}?type=risk`}
                        className="hover:text-[var(--color-accent)] hover:underline"
                      >
                        {r.folio}
                      </Link>
                    </td>
                    {/* US-178: título editable inline. */}
                    <td className="px-2 py-1.5 text-[var(--color-primary)]">
                      <InlineTextCell
                        value={r.title}
                        onChange={(v) => onPatch(r.id, { title: v })}
                        title="Título"
                        ariaLabel={`Título de ${r.folio}`}
                      />
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                      <InlineSelectCell
                        value={r.area_id ?? ""}
                        options={areaOpts(r)}
                        onChange={(v) => onPatch(r.id, { area_id: v || undefined })}
                        placeholder="—"
                        title="Área"
                        ariaLabel={`Área de ${r.folio}`}
                      />
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                      <InlineSelectCell
                        value={r.owner_actor_id ?? ""}
                        options={respOpts(r)}
                        onChange={(v) =>
                          onPatch(r.id, { owner_actor_id: v || null })
                        }
                        placeholder="—"
                        title="Responsable"
                        ariaLabel={`Responsable de ${r.folio}`}
                      />
                    </td>
                    {/* ENH-176: severidad = P × I, editable inline. Compacto:
                        badge + P×I sin labels de texto (tooltips lo aclaran). */}
                    <td className="px-2 py-1.5">
                      <div className="flex items-center gap-0.5">
                        <SeverityBadge severity={r.severity} />
                        <InlineSelectCell
                          value={r.probability != null ? String(r.probability) : ""}
                          options={[1, 2, 3, 4, 5].map((n) => ({
                            value: String(n),
                            label: String(n),
                          }))}
                          onChange={(v) =>
                            (onRiskPatch ?? ((id, p) => onPatch(id, p)))(r.id, {
                              probability: Number(v),
                            })
                          }
                          placeholder="P"
                          title="Probabilidad (P)"
                          ariaLabel={`Probabilidad de ${r.folio}`}
                        />
                        <span className="text-[10px] text-[var(--color-tertiary)]">×</span>
                        <InlineSelectCell
                          value={r.impact != null ? String(r.impact) : ""}
                          options={[1, 2, 3, 4, 5].map((n) => ({
                            value: String(n),
                            label: String(n),
                          }))}
                          onChange={(v) =>
                            (onRiskPatch ?? ((id, p) => onPatch(id, p)))(r.id, {
                              impact: Number(v),
                            })
                          }
                          placeholder="I"
                          title="Impacto (I)"
                          ariaLabel={`Impacto de ${r.folio}`}
                        />
                      </div>
                    </td>
                    {/* US-178/US-179: estado con tag de color, editable inline. */}
                    <td className="px-2 py-1.5">
                      <span className="inline-flex items-center">
                        <StatusInlineCell
                          status={r.status}
                          onChange={(v) =>
                            onStatusChange
                              ? onStatusChange(r.id, v)
                              : onPatch(r.id, { status: v as RaidStatus })
                          }
                          ariaLabel={`Estado de ${r.folio}`}
                        />
                        <OnHoldInfo status={r.status} since={r.on_hold_since} />
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                      <InlineDateCell
                        value={r.identified_at}
                        onChange={(v) => onPatch(r.id, { identified_at: v })}
                        title="Fecha de creación"
                        ariaLabel={`Fecha de creación de ${r.folio}`}
                      />
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                      <InlineDateCell
                        value={r.due_date}
                        onChange={(v) => onPatch(r.id, { due_date: v })}
                        title="Fecha compromiso"
                        ariaLabel={`Fecha compromiso de ${r.folio}`}
                      />
                    </td>
                    <td className="px-2 py-1.5">
                      <RowActions
                        onPreview={() => setPreview(r)}
                        onEdit={() => onEdit(r)}
                        onDelete={() => onDelete(r.id)}
                        label={r.folio}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <ItemPreviewModal
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={preview?.title ?? ""}
        subtitle={preview?.folio}
        fields={
          preview
            ? [
                { label: "ID", value: preview.id, mono: true },
                { label: "Folio", value: preview.folio, mono: true },
                { label: "Área", value: preview.area?.name ?? "—" },
                { label: "Severidad", value: preview.severity ?? "—" },
                {
                  label: "P × I",
                  value: `${preview.probability ?? "—"} × ${preview.impact ?? "—"}`,
                },
                { label: "F. Creación", value: preview.identified_at ?? "—" },
                { label: "F. Compromiso", value: preview.due_date ?? "—" },
                { label: "Asignado", value: preview.owner_id ?? "—", mono: true },
              ]
            : []
        }
        description={preview?.description ?? null}
        openHref={
          preview
            ? `/pmo/projects/${preview.project_id}/raid/${preview.id}?type=risk`
            : undefined
        }
      />
    </div>
  );
}

function IssuesSection({
  rows,
  projectId,
  sectionLabel,
  issueType,
  areaOptions,
  actorOptions,
  onStatusChange,
  onPatch,
  onDelete,
  onEdit,
}: {
  rows: Issue[];
  projectId: string;
  sectionLabel: string;
  issueType: IssueType;
  areaOptions: InlineOption[];
  actorOptions: InlineOption[];
  // US-175: cambio de estado inline.
  onStatusChange?: (id: string, status: string) => void;
  // US-178: patch inline genérico + borrar + abrir form de edición.
  onPatch: (id: string, patch: IssueUpdateBody) => void;
  onDelete: (id: string) => void;
  onEdit: (i: Issue) => void;
}) {
  const [preview, setPreview] = useState<Issue | null>(null);
  const { sortedRows, ctrl: issueSortCtrl } = useSortableRows<Issue>(rows);
  const areaOpts = (it: Issue): InlineOption[] => {
    const opts = [...areaOptions];
    if (it.area_id && !opts.some((o) => o.value === it.area_id))
      opts.unshift({ value: it.area_id, label: it.area?.name ?? "(área)" });
    return [{ value: "", label: "— sin área —" }, ...opts];
  };
  const respOpts = (it: Issue): InlineOption[] => {
    const opts = [...actorOptions];
    if (it.owner_actor_id && !opts.some((o) => o.value === it.owner_actor_id))
      opts.unshift({
        value: it.owner_actor_id,
        label: it.responsible_name ?? "(responsable)",
      });
    return [{ value: "", label: "— sin responsable —" }, ...opts];
  };
  if (rows.length === 0) {
    return (
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
        Sin {sectionLabel.toLowerCase()} registradas. Usa el botón{" "}
        <strong>+ Nueva {sectionLabel.toLowerCase().replace(/s$/, "")}</strong>
        {" "}arriba para crear la primera.
      </div>
    );
  }
  const displayLabel =
    issueType === "issue" ? INCIDENT_LABEL : ISSUE_TYPE_LABEL[issueType];
  return (
    <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
            <tr>
              <SortableTh<Issue> sortKey="folio" getter={(r) => r.folio} ctrl={issueSortCtrl}>Folio</SortableTh>
              <SortableTh<Issue> sortKey="title" getter={(r) => r.title} ctrl={issueSortCtrl}>Título</SortableTh>
              <SortableTh<Issue> sortKey="area" getter={(r) => (r as any).area?.name ?? ""} ctrl={issueSortCtrl}>Área</SortableTh>
              <SortableTh<Issue> sortKey="responsible" getter={(r) => r.responsible_name ?? ""} ctrl={issueSortCtrl}>Responsable</SortableTh>
              <SortableTh<Issue> sortKey="priority" getter={(r) => (r as any).priority ?? 0} ctrl={issueSortCtrl}>Prioridad</SortableTh>
              <SortableTh<Issue> sortKey="status" getter={(r) => r.status} ctrl={issueSortCtrl}>Estado</SortableTh>
              <SortableTh<Issue> sortKey="identified" getter={(r) => (r as any).reported_at ?? ""} ctrl={issueSortCtrl}>F. Creación</SortableTh>
              <SortableTh<Issue> sortKey="committed" getter={(r) => (r as any).committed_date ?? ""} ctrl={issueSortCtrl}>F. Compromiso</SortableTh>
              <th className="px-2 py-1.5 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((it) => (
              <tr
                key={it.id}
                className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
              >
                {/* US-178: folio = único link que abre el ticket. */}
                <td className="px-2 py-1.5 font-mono text-xs text-[var(--color-tertiary)]">
                  <Link
                    href={`/pmo/projects/${projectId}/raid/${it.id}?type=${issueType === "action" ? "action" : issueType === "decision" ? "decision" : "incident"}`}
                    className="hover:text-[var(--color-accent)] hover:underline"
                  >
                    {it.folio}
                  </Link>
                </td>
                {/* US-178: título editable inline. */}
                <td className="px-2 py-1.5 text-[var(--color-primary)]">
                  <InlineTextCell
                    value={it.title}
                    onChange={(v) => onPatch(it.id, { title: v })}
                    title="Título"
                    ariaLabel={`Título de ${it.folio}`}
                  />
                </td>
                <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                  <InlineSelectCell
                    value={it.area_id ?? ""}
                    options={areaOpts(it)}
                    onChange={(v) => onPatch(it.id, { area_id: v || undefined })}
                    placeholder="—"
                    title="Área"
                    ariaLabel={`Área de ${it.folio}`}
                  />
                </td>
                <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                  <InlineSelectCell
                    value={it.owner_actor_id ?? ""}
                    options={respOpts(it)}
                    onChange={(v) => onPatch(it.id, { owner_actor_id: v || null })}
                    placeholder="—"
                    title="Responsable"
                    ariaLabel={`Responsable de ${it.folio}`}
                  />
                </td>
                <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                  <InlineSelectCell
                    value={it.priority != null ? String(it.priority) : ""}
                    options={[1, 2, 3, 4, 5].map((n) => ({
                      value: String(n),
                      label: `P${n}`,
                    }))}
                    onChange={(v) =>
                      onPatch(it.id, { priority: v ? Number(v) : null })
                    }
                    placeholder="—"
                    title="Prioridad"
                    ariaLabel={`Prioridad de ${it.folio}`}
                  />
                </td>
                {/* US-178/US-179: estado con tag de color, editable inline. */}
                <td className="px-2 py-1.5">
                  <span className="inline-flex items-center">
                    <StatusInlineCell
                      status={it.status}
                      onChange={(v) =>
                        onStatusChange
                          ? onStatusChange(it.id, v)
                          : onPatch(it.id, { status: v as RaidStatus })
                      }
                      ariaLabel={`Estado de ${it.folio}`}
                    />
                    <OnHoldInfo status={it.status} since={it.on_hold_since} />
                  </span>
                </td>
                <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                  <InlineDateCell
                    value={it.reported_at ? it.reported_at.slice(0, 10) : null}
                    onChange={(v) =>
                      onPatch(it.id, {
                        reported_at: v ? `${v}T00:00:00Z` : null,
                      })
                    }
                    title="Fecha de creación"
                    ariaLabel={`Fecha de creación de ${it.folio}`}
                  />
                </td>
                <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                  <InlineDateCell
                    value={it.committed_date}
                    onChange={(v) => onPatch(it.id, { committed_date: v })}
                    title="Fecha compromiso"
                    ariaLabel={`Fecha compromiso de ${it.folio}`}
                  />
                </td>
                <td className="px-2 py-1.5">
                  <RowActions
                    onPreview={() => setPreview(it)}
                    onEdit={() => onEdit(it)}
                    onDelete={() => onDelete(it.id)}
                    label={it.folio}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ItemPreviewModal
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={preview?.title ?? ""}
        subtitle={preview?.folio}
        fields={
          preview
            ? [
                { label: "ID", value: preview.id, mono: true },
                { label: "Folio", value: preview.folio, mono: true },
                { label: "Área", value: preview.area?.name ?? "—" },
                { label: "Tipo", value: displayLabel },
                { label: "Prioridad", value: preview.priority ?? "—" },
                { label: "Compromiso", value: preview.committed_date ?? "—" },
                { label: "Asignado", value: preview.owner_id ?? "—", mono: true },
                { label: "Resolución", value: preview.resolution ?? "—" },
              ]
            : []
        }
        description={preview?.description ?? null}
        openHref={
          preview
            ? `/pmo/projects/${preview.project_id}/raid/${preview.id}?type=${issueType === "issue" ? "incident" : issueType}`
            : undefined
        }
      />
    </section>
  );
}

function SeverityBadge({ severity }: { severity: number | null }) {
  if (severity === null) return <span className="text-xs">—</span>;
  const tone =
    severity >= 13
      ? "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]"
      : severity >= 6
        ? "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]"
        : "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold",
        tone,
      )}
    >
      {severity}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: number | null | undefined }) {
  if (priority === null || priority === undefined)
    return <span className="text-xs">—</span>;
  const tone =
    priority === 1
      ? "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]"
      : priority === 2
        ? "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]"
        : priority === 3
          ? "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]"
          : "bg-[var(--color-subtle)] text-[var(--color-secondary)]";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold",
        tone,
      )}
      aria-label={`Prioridad ${priority}`}
      title={`Prioridad ${priority}`}
    >
      P{priority}
    </span>
  );
}

export default function RaidPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8">
          <Skeleton className="h-10 w-48" />
        </div>
      }
    >
      <RaidInner />
    </Suspense>
  );
}
