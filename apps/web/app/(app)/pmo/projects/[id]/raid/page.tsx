"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Eye,
  GitCommit,
  TriangleAlert,
} from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  KIND_NEW_LABEL,
  RaidCreateModal,
  type RaidKind,
} from "@/components/raid-create-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  ISSUE_STATUS_LABEL,
  ISSUE_TYPE_LABEL,
  RISK_STATUS_LABEL,
  listIssues,
  listRisks,
  type Issue,
  type IssueStatus,
  type IssueType,
  type Risk,
  type RiskStatus,
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
    return risks.filter((r) => {
      if (statusFilter && r.status !== statusFilter) return false;
      if (severityMin !== "" && (r.severity ?? 0) < Number(severityMin))
        return false;
      return true;
    });
  }, [risks, statusFilter, severityMin]);

  function filterIssues(list: Issue[]): Issue[] {
    return list.filter((it) => {
      if (statusFilter && it.status !== statusFilter) return false;
      if (priorityMin !== "" && (it.priority ?? 0) < Number(priorityMin))
        return false;
      return true;
    });
  }

  const filteredActions = useMemo(
    () => filterIssues(actions),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [actions, statusFilter, priorityMin],
  );
  const filteredIncidents = useMemo(
    () => filterIssues(incidents),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [incidents, statusFilter, priorityMin],
  );
  const filteredDecisions = useMemo(
    () => filterIssues(decisions),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [decisions, statusFilter, priorityMin],
  );

  const counts: Record<Tab, number> = {
    risks: risks.length,
    actions: actions.length,
    incidents: incidents.length,
    decisions: decisions.length,
  };

  // Export RAID: CSV unificado con 4 secciones (el XLSX nativo queda como
  // follow-up; CSV cumple el uso práctico y se abre en Excel directo).
  function buildCsv(): string {
    const esc = (v: unknown) => {
      const s = v === null || v === undefined ? "" : String(v);
      return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines: string[] = [];
    lines.push("# Riesgos");
    lines.push("folio;title;status;probability;impact;severity;owner;due_date");
    for (const r of risks) {
      lines.push(
        [
          r.folio,
          r.title,
          r.status,
          r.probability ?? "",
          r.impact ?? "",
          r.severity ?? "",
          r.owner_id ?? "",
          r.due_date ?? "",
        ]
          .map(esc)
          .join(";"),
      );
    }
    for (const [section, items] of [
      ["Acciones", actions],
      ["Incidentes", incidents],
      ["Decisiones", decisions],
    ] as const) {
      lines.push("");
      lines.push(`# ${section}`);
      lines.push("folio;title;status;priority;owner;committed_date;resolution");
      for (const it of items) {
        lines.push(
          [
            it.folio,
            it.title,
            it.status,
            it.priority ?? "",
            it.owner_id ?? "",
            it.committed_date ?? "",
            it.resolution ?? "",
          ]
            .map(esc)
            .join(";"),
        );
      }
    }
    return lines.join("\n");
  }

  function downloadCsv() {
    const csv = buildCsv();
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `raid-${id}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
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
          <button
            type="button"
            onClick={downloadCsv}
            className="inline-flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-subtle)]"
          >
            <Download className="h-4 w-4" aria-hidden />
            Exportar RAID (CSV)
          </button>
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
                "inline-flex items-center gap-2 rounded-[var(--radius-md)] border px-3 py-2 text-sm transition-colors",
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

      {/* ENH-026: filtros avanzados (status + severity/priority)
          consolidados — antes vivían en /risks y /issues. */}
      <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] px-3 py-2 text-[13px]">
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
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : tab === "risks" ? (
        <RisksSection
          rows={filteredRisks}
          projectId={id}
          onRiskUpdate={(updated) =>
            setRisks((prev) =>
              prev.map((x) => (x.id === updated.id ? { ...x, ...updated } : x)),
            )
          }
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
          onIssueUpdate={(updated) =>
            setIssues((prev) =>
              prev.map((x) => (x.id === updated.id ? { ...x, ...updated } : x)),
            )
          }
        />
      )}

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
  onRiskUpdate,
}: {
  rows: Risk[];
  projectId: string;
  onRiskUpdate: (r: Partial<Risk> & { id: string }) => void;
}) {
  const [preview, setPreview] = useState<Risk | null>(null);
  // ENH-061: filtro por celda P×I de la matriz.
  const [cellFilter, setCellFilter] = useState<
    { p: number; i: number } | null
  >(null);
  void projectId;

  function toggleCell(p: number, i: number) {
    setCellFilter((prev) =>
      prev && prev.p === p && prev.i === i ? null : { p, i },
    );
  }

  const visibleRows = useMemo(() => {
    if (!cellFilter) return rows;
    return rows.filter(
      (r) => r.probability === cellFilter.p && r.impact === cellFilter.i,
    );
  }, [rows, cellFilter]);

  return (
    <div className="space-y-5">
      <RiskMatrix
        rows={rows}
        selected={cellFilter}
        onCellToggle={toggleCell}
      />
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
          <header className="border-b border-[var(--border-default)] px-4 py-3">
            <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
              <TriangleAlert className="h-4 w-4" aria-hidden /> Riesgos
            </h2>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <tr>
                  <th className="w-10 px-3 py-2" aria-label="Preview" />
                  <th className="px-3 py-2 font-medium">Folio</th>
                  <th className="px-3 py-2 font-medium">Título</th>
                  <th className="px-3 py-2 font-medium">Área</th>
                  <th className="px-3 py-2 font-medium">Severidad</th>
                  <th className="px-3 py-2 font-medium">Estado</th>
                  <th className="px-3 py-2 font-medium">F. Creación</th>
                  <th className="px-3 py-2 font-medium">F. Compromiso</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                  >
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => setPreview(r)}
                        aria-label={`Preview ${r.title}`}
                        title="Vista rápida"
                        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                      >
                        <Eye className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
                      <Link
                        href={`/pmo/projects/${projectId}/raid/${r.id}?type=risk`}
                        className="hover:text-[var(--color-accent)] hover:underline"
                      >
                        {r.folio}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        href={`/pmo/projects/${projectId}/raid/${r.id}?type=risk`}
                        className="text-[var(--color-primary)] hover:text-[var(--color-accent)] hover:underline"
                      >
                        {r.title}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-[var(--color-secondary)]">
                      {r.area?.name ?? "—"}
                    </td>
                    <td className="px-3 py-2">
                      <SeverityBadge severity={r.severity} />
                    </td>
                    <td className="px-3 py-2 text-[var(--color-secondary)]">
                      {RISK_STATUS_LABEL[r.status] ?? r.status}
                    </td>
                    <td className="px-3 py-2 text-[var(--color-secondary)]">
                      {r.identified_at ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-[var(--color-secondary)]">
                      {r.due_date ?? "—"}
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
  onIssueUpdate,
}: {
  rows: Issue[];
  projectId: string;
  sectionLabel: string;
  issueType: IssueType;
  onIssueUpdate: (i: Partial<Issue> & { id: string }) => void;
}) {
  const [preview, setPreview] = useState<Issue | null>(null);
  void projectId;
  if (rows.length === 0) {
    return (
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
        Sin {sectionLabel.toLowerCase()} registradas. Usa el botón{" "}
        <strong>+ Nueva {sectionLabel.toLowerCase().replace(/s$/, "")}</strong>
        {" "}arriba para crear la primera.
      </div>
    );
  }
  const Icon =
    issueType === "action" ? GitCommit : issueType === "decision" ? CheckCircle2 : AlertTriangle;
  const displayLabel =
    issueType === "issue" ? INCIDENT_LABEL : ISSUE_TYPE_LABEL[issueType];
  return (
    <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <header className="border-b border-[var(--border-default)] px-4 py-3">
        <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <Icon className="h-4 w-4" aria-hidden /> {sectionLabel}
        </h2>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
            <tr>
              <th className="w-10 px-3 py-2" aria-label="Preview" />
              <th className="px-3 py-2 font-medium">Folio</th>
              <th className="px-3 py-2 font-medium">Título</th>
              <th className="px-3 py-2 font-medium">Área</th>
              <th className="px-3 py-2 font-medium">Tipo</th>
              <th className="px-3 py-2 font-medium">Prioridad</th>
              <th className="px-3 py-2 font-medium">Estado</th>
              <th className="px-3 py-2 font-medium">F. Creación</th>
              <th className="px-3 py-2 font-medium">F. Compromiso</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((it) => (
              <tr
                key={it.id}
                className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
              >
                <td className="px-3 py-2">
                  <button
                    type="button"
                    onClick={() => setPreview(it)}
                    aria-label={`Preview ${it.title}`}
                    title="Vista rápida"
                    className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                  >
                    <Eye className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </td>
                <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
                  <Link
                    href={`/pmo/projects/${projectId}/raid/${it.id}?type=${issueType === "action" ? "action" : issueType === "decision" ? "decision" : "incident"}`}
                    className="hover:text-[var(--color-accent)] hover:underline"
                  >
                    {it.folio}
                  </Link>
                </td>
                <td className="px-3 py-2">
                  <Link
                    href={`/pmo/projects/${projectId}/raid/${it.id}?type=${issueType === "action" ? "action" : issueType === "decision" ? "decision" : "incident"}`}
                    className="text-[var(--color-primary)] hover:text-[var(--color-accent)] hover:underline"
                  >
                    {it.title}
                  </Link>
                </td>
                <td className="px-3 py-2 text-[var(--color-secondary)]">
                  {it.area?.name ?? "—"}
                </td>
                <td className="px-3 py-2 text-[var(--color-secondary)]">
                  {displayLabel}
                </td>
                <td className="px-3 py-2 text-[var(--color-secondary)]">
                  <PriorityBadge priority={it.priority} />
                </td>
                <td className="px-3 py-2 text-[var(--color-secondary)]">
                  {it.status}
                </td>
                <td className="px-3 py-2 text-[var(--color-secondary)]">
                  {it.reported_at
                    ? new Date(it.reported_at).toISOString().slice(0, 10)
                    : "—"}
                </td>
                <td className="px-3 py-2 text-[var(--color-secondary)]">
                  {it.committed_date ?? "—"}
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
