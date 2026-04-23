"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Eye, LayoutGrid, List as ListIcon, Shield } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { ApiError } from "@/lib/api";
import {
  ISSUE_STATUS_LABEL,
  ISSUE_TYPE_LABEL,
  RISK_STATUS_LABEL,
  addIssueComment,
  addRiskComment,
  type Issue,
  type IssueStatus,
  type IssueType,
  type Risk,
  type RiskStatus,
  updateIssue,
  updateRisk,
} from "@/lib/api/modules";
import {
  listTenantIssues,
  listTenantRisks,
  type TenantIssue,
  type TenantRisk,
} from "@/lib/api/tenant-cross";

type Kind = "risks" | "actions" | "issues" | "decisions";

const KIND_LABEL: Record<Kind, string> = {
  risks: "Riesgos",
  actions: "Acciones",
  issues: "Incidentes",
  decisions: "Decisiones",
};

function parseKind(v: string | null): Kind {
  return v === "actions" || v === "issues" || v === "decisions" || v === "risks"
    ? v
    : "risks";
}

function TenantRaidInner() {
  const searchParams = useSearchParams();
  // ENH-009: el KPI del dashboard puede landear directo en un kind
  // específico vía ?kind=... (risks|actions|issues|decisions).
  // severity_min permite el caso "Riesgos severos".
  const severityMin = Number(searchParams.get("severity_min") ?? "") || null;
  const [kind, setKind] = useState<Kind>(parseKind(searchParams.get("kind")));
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  // ENH-018: toggle Lista/Kanban. La URL conserva la selección.
  const [view, setView] = useState<"list" | "board">(
    searchParams.get("view") === "board" ? "board" : "list",
  );
  // ENH-019: filtros avanzados server-side (además de la cascada org/program/project).
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityMinFilter, setSeverityMinFilter] = useState<string>("");
  const [priorityMinFilter, setPriorityMinFilter] = useState<string>("");
  const [risks, setRisks] = useState<TenantRisk[]>([]);
  const [issues, setIssues] = useState<TenantIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewRisk, setPreviewRisk] = useState<TenantRisk | null>(null);
  const [previewIssue, setPreviewIssue] = useState<TenantIssue | null>(null);

  // Al cambiar el Tipo se limpian los filtros de estado/severidad/prioridad
  // para evitar combinaciones inválidas (p. ej. estado de riesgo aplicado a
  // una Acción, cuyos estados son distintos).
  useEffect(() => {
    setStatusFilter("");
    setSeverityMinFilter("");
    setPriorityMinFilter("");
  }, [kind]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const issueType: IssueType | undefined =
      kind === "actions" ? "action" : kind === "decisions" ? "decision" : kind === "issues" ? "issue" : undefined;
    const severityMinNum = Number(severityMinFilter);
    const priorityMinNum = Number(priorityMinFilter);
    const promise =
      kind === "risks"
        ? listTenantRisks({
            ...filter,
            status: (statusFilter || undefined) as
              | Risk["status"]
              | undefined,
            severity_min: severityMinNum > 0 ? severityMinNum : undefined,
          }).then((r) => {
            if (!cancelled) {
              setRisks(r);
              setIssues([]);
            }
          })
        : listTenantIssues({
            ...filter,
            type: issueType,
            status: (statusFilter || undefined) as
              | Issue["status"]
              | undefined,
            priority_min: priorityMinNum > 0 ? priorityMinNum : undefined,
          }).then((r) => {
            if (!cancelled) {
              setIssues(r);
              setRisks([]);
            }
          });
    promise
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar RAID");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kind, filter, statusFilter, severityMinFilter, priorityMinFilter]);

  // ENH-009: cuando el link trae ?severity_min=N (típicamente 13 para
  // "Riesgos severos" desde el dashboard), filtramos client-side.
  const visibleRisks = useMemo(
    () => (severityMin ? risks.filter((r) => (r.severity ?? 0) >= severityMin) : risks),
    [risks, severityMin],
  );
  const rows = kind === "risks" ? visibleRisks : issues;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <Shield
              className="h-6 w-6 text-[var(--color-tertiary)]"
              aria-hidden
            />
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              RAID · Tenant
            </h1>
          </div>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Vista consolidada de Riesgos · Acciones · Incidentes · Decisiones de
            todos los proyectos accesibles.
          </p>
        </div>
        {/* ENH-018: toggle Lista/Kanban, mismo patrón que /admin/projects. */}
        <div className="inline-flex rounded-[10px] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-1">
          <button
            type="button"
            onClick={() => setView("list")}
            aria-pressed={view === "list"}
            className={cn(
              "inline-flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[12px] font-medium transition-colors",
              view === "list"
                ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
            )}
          >
            <ListIcon className="h-3.5 w-3.5" aria-hidden /> Lista
          </button>
          <button
            type="button"
            onClick={() => setView("board")}
            aria-pressed={view === "board"}
            className={cn(
              "inline-flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[12px] font-medium transition-colors",
              view === "board"
                ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" aria-hidden /> Kanban
          </button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        {/* ENH-017: orden horizontal Tipo → Proyecto → Programa → Organización. */}
        <TenantCrossFilters
          value={filter}
          onChange={setFilter}
          reverse
          leading={
            <Select
              aria-label="Tipo"
              className="h-9 min-w-[160px]"
              value={kind}
              onChange={(e) => setKind(e.target.value as Kind)}
            >
              {(Object.keys(KIND_LABEL) as Kind[]).map((k) => (
                <option key={k} value={k}>
                  {KIND_LABEL[k]}
                </option>
              ))}
            </Select>
          }
        />
        {/* ENH-019: filtros avanzados (status + severity/priority). */}
        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Estado"
            className="h-9 min-w-[160px]"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Todos los estados</option>
            {kind === "risks"
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
          </Select>
          {kind === "risks" ? (
            <Select
              aria-label="Severidad mínima"
              className="h-9 min-w-[160px]"
              value={severityMinFilter}
              onChange={(e) => setSeverityMinFilter(e.target.value)}
            >
              <option value="">Cualquier severidad</option>
              <option value="13">Alta (≥ 13)</option>
              <option value="6">Media (≥ 6)</option>
              <option value="1">Baja (≥ 1)</option>
            </Select>
          ) : (
            <Select
              aria-label="Prioridad mínima"
              className="h-9 min-w-[160px]"
              value={priorityMinFilter}
              onChange={(e) => setPriorityMinFilter(e.target.value)}
            >
              <option value="">Cualquier prioridad</option>
              <option value="4">P4+ (Alta)</option>
              <option value="3">P3+ (Media-alta)</option>
              <option value="2">P2+ (Media)</option>
              <option value="1">P1+ (Todas)</option>
            </Select>
          )}
        </div>
      </section>

      <section
        className={cn(
          "rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]",
          view === "list" ? "overflow-hidden" : "",
        )}
      >
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin registros para los filtros actuales.
          </div>
        ) : view === "board" ? (
          kind === "risks" ? (
            <RiskBoard rows={visibleRisks} onPreview={setPreviewRisk} />
          ) : (
            <IssueBoard rows={issues} kind={kind} onPreview={setPreviewIssue} />
          )
        ) : kind === "risks" ? (
          <RiskTable rows={visibleRisks} onPreview={setPreviewRisk} />
        ) : (
          <IssueTable rows={issues} kind={kind} onPreview={setPreviewIssue} />
        )}
      </section>

      <ItemPreviewModal
        open={previewRisk !== null}
        onClose={() => setPreviewRisk(null)}
        title={previewRisk?.title ?? ""}
        subtitle={previewRisk?.folio}
        fields={
          previewRisk
            ? [
                { label: "ID", value: previewRisk.id, mono: true },
                {
                  label: "Proyecto",
                  value: `${previewRisk.project_folio} — ${previewRisk.project_name}`,
                },
                { label: "Severidad", value: previewRisk.severity ?? "—" },
                { label: "Fecha límite", value: previewRisk.due_date ?? "—" },
              ]
            : []
        }
        description={previewRisk?.description ?? null}
        extra={
          previewRisk ? (
            <RiskDetailBody
              risk={previewRisk}
              onUpdated={(r) => {
                setPreviewRisk({ ...previewRisk, ...r });
                setRisks((prev) =>
                  prev.map((x) =>
                    x.id === r.id ? { ...x, ...r } : x,
                  ),
                );
              }}
            />
          ) : null
        }
      />

      <ItemPreviewModal
        open={previewIssue !== null}
        onClose={() => setPreviewIssue(null)}
        title={previewIssue?.title ?? ""}
        subtitle={previewIssue?.folio}
        fields={
          previewIssue
            ? [
                { label: "ID", value: previewIssue.id, mono: true },
                {
                  label: "Proyecto",
                  value: `${previewIssue.project_folio} — ${previewIssue.project_name}`,
                },
                { label: "Tipo", value: ISSUE_TYPE_LABEL[previewIssue.type] ?? previewIssue.type },
                { label: "Prioridad", value: previewIssue.priority ?? "—" },
                { label: "Compromiso", value: previewIssue.committed_date ?? "—" },
              ]
            : []
        }
        description={previewIssue?.description ?? null}
        extra={
          previewIssue ? (
            <IssueDetailBody
              issue={previewIssue}
              onUpdated={(i) => {
                setPreviewIssue({ ...previewIssue, ...i });
                setIssues((prev) =>
                  prev.map((x) =>
                    x.id === i.id ? { ...x, ...i } : x,
                  ),
                );
              }}
            />
          ) : null
        }
      />
    </div>
  );
}

/* =================== Editable body (US-058) =================== */

function fmtCommentDate(iso: string | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("es-MX", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function RiskDetailBody({
  risk,
  onUpdated,
}: {
  risk: TenantRisk;
  onUpdated: (r: Partial<Risk> & { id: string }) => void;
}) {
  const [status, setStatus] = useState<RiskStatus>(risk.status);
  const [savingStatus, setSavingStatus] = useState(false);
  const [comment, setComment] = useState("");
  const [addingComment, setAddingComment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comments, setComments] = useState(risk.comments ?? []);

  useEffect(() => {
    setStatus(risk.status);
    setComments(risk.comments ?? []);
    setComment("");
    setError(null);
  }, [risk.id, risk.status, risk.comments]);

  async function changeStatus(next: RiskStatus) {
    if (next === status) return;
    setSavingStatus(true);
    setError(null);
    try {
      const payload: { status: RiskStatus; closure_note?: string | null } = {
        status: next,
      };
      if ((next === "closed" || next === "materialized") && !risk.closure_note) {
        const note = window.prompt(
          "Nota de cierre obligatoria para cerrar/materializar el riesgo:",
        );
        if (!note || !note.trim()) {
          setSavingStatus(false);
          return;
        }
        payload.closure_note = note.trim();
      }
      const updated = await updateRisk(risk.id, payload);
      setStatus(updated.status);
      onUpdated({ id: updated.id, status: updated.status });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al guardar el estado",
      );
      setStatus(risk.status);
    } finally {
      setSavingStatus(false);
    }
  }

  async function submitComment() {
    if (!comment.trim()) return;
    setAddingComment(true);
    setError(null);
    try {
      const updated = await addRiskComment(risk.id, { text: comment.trim() });
      setComments(updated.comments);
      setComment("");
      onUpdated({ id: updated.id, comments: updated.comments });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al agregar comentario",
      );
    } finally {
      setAddingComment(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          Estado
        </div>
        <Select
          value={status}
          onChange={(e) => changeStatus(e.target.value as RiskStatus)}
          disabled={savingStatus}
          aria-label="Estado del riesgo"
        >
          {(Object.keys(RISK_STATUS_LABEL) as RiskStatus[]).map((s) => (
            <option key={s} value={s}>
              {RISK_STATUS_LABEL[s]}
            </option>
          ))}
        </Select>
      </div>
      {error ? <Banner variant="danger">{error}</Banner> : null}
      <CommentsBlock
        comments={comments}
        value={comment}
        onChange={setComment}
        onSubmit={submitComment}
        busy={addingComment}
      />
    </div>
  );
}

function IssueDetailBody({
  issue,
  onUpdated,
}: {
  issue: TenantIssue;
  onUpdated: (i: Partial<Issue> & { id: string }) => void;
}) {
  const [status, setStatus] = useState<IssueStatus>(issue.status);
  const [savingStatus, setSavingStatus] = useState(false);
  const [comment, setComment] = useState("");
  const [addingComment, setAddingComment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comments, setComments] = useState(issue.comments ?? []);

  useEffect(() => {
    setStatus(issue.status);
    setComments(issue.comments ?? []);
    setComment("");
    setError(null);
  }, [issue.id, issue.status, issue.comments]);

  async function changeStatus(next: IssueStatus) {
    if (next === status) return;
    setSavingStatus(true);
    setError(null);
    try {
      const updated = await updateIssue(issue.id, { status: next });
      setStatus(updated.status);
      onUpdated({ id: updated.id, status: updated.status });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
      setStatus(issue.status);
    } finally {
      setSavingStatus(false);
    }
  }

  async function submitComment() {
    if (!comment.trim()) return;
    setAddingComment(true);
    setError(null);
    try {
      const updated = await addIssueComment(issue.id, { text: comment.trim() });
      setComments(updated.comments);
      setComment("");
      onUpdated({ id: updated.id, comments: updated.comments });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al agregar comentario",
      );
    } finally {
      setAddingComment(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          Estado
        </div>
        <Select
          value={status}
          onChange={(e) => changeStatus(e.target.value as IssueStatus)}
          disabled={savingStatus}
          aria-label="Estado del ítem"
        >
          {(Object.keys(ISSUE_STATUS_LABEL) as IssueStatus[]).map((s) => (
            <option key={s} value={s}>
              {ISSUE_STATUS_LABEL[s]}
            </option>
          ))}
        </Select>
      </div>
      {error ? <Banner variant="danger">{error}</Banner> : null}
      <CommentsBlock
        comments={comments}
        value={comment}
        onChange={setComment}
        onSubmit={submitComment}
        busy={addingComment}
      />
    </div>
  );
}

function CommentsBlock({
  comments,
  value,
  onChange,
  onSubmit,
  busy,
}: {
  comments: Array<{ text: string; author_id?: string; created_at?: string }>;
  value: string;
  onChange: (s: string) => void;
  onSubmit: () => void;
  busy: boolean;
}) {
  return (
    <div>
      <div className="mb-1 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
        Comentarios
      </div>
      {comments.length === 0 ? (
        <p className="mb-2 text-[13px] text-[var(--color-tertiary)]">
          Sin comentarios todavía.
        </p>
      ) : (
        <ul className="mb-2 space-y-2">
          {comments.map((c, i) => (
            <li
              key={i}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-2"
            >
              <div className="mb-0.5 flex items-center justify-between gap-2 text-[11px] text-[var(--color-tertiary)]">
                <span className="font-mono">
                  {c.author_id ? c.author_id.slice(0, 8) : "—"}
                </span>
                <span>{fmtCommentDate(c.created_at)}</span>
              </div>
              <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
                {c.text}
              </p>
            </li>
          ))}
        </ul>
      )}
      <div className="space-y-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={2}
          placeholder="Escribe un comentario…"
          className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 py-1.5 text-[13px] text-[var(--color-primary)] focus:border-[var(--color-accent)] focus:outline-none"
        />
        <div className="flex justify-end">
          <Button
            type="button"
            size="sm"
            onClick={onSubmit}
            loading={busy}
            disabled={!value.trim()}
          >
            Agregar
          </Button>
        </div>
      </div>
    </div>
  );
}

function RiskTable({
  rows,
  onPreview,
}: {
  rows: TenantRisk[];
  onPreview: (r: TenantRisk) => void;
}) {
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
        <tr>
          <th className="w-10 px-3 py-2" />
          <th className="px-3 py-2 font-medium">Folio</th>
          <th className="px-3 py-2 font-medium">Título</th>
          <th className="px-3 py-2 font-medium">Severidad</th>
          <th className="px-3 py-2 font-medium">Estado</th>
          <th className="px-3 py-2 font-medium">Proyecto</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
            <td className="px-3 py-2">
              <button
                type="button"
                onClick={() => onPreview(r)}
                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                aria-label="Preview"
              >
                <Eye className="h-3.5 w-3.5" aria-hidden />
              </button>
            </td>
            <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
              {r.folio}
            </td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}/raid?tab=risks`}
                className="text-[var(--color-primary)] hover:underline"
              >
                {r.title}
              </Link>
            </td>
            <td className="px-3 py-2">
              <Badge variant={(r.severity ?? 0) >= 13 ? "danger" : (r.severity ?? 0) >= 6 ? "warning" : "success"}>
                {r.severity ?? "—"}
              </Badge>
            </td>
            <td className="px-3 py-2 text-[var(--color-secondary)]">
              {RISK_STATUS_LABEL[r.status] ?? r.status}
            </td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}`}
                className="text-xs text-[var(--color-accent)] hover:underline"
                title={r.project_name}
              >
                <span className="font-mono">{r.project_folio}</span>
                <span className="ml-1 text-[var(--color-secondary)]">
                  — {r.project_name}
                </span>
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function IssueTable({
  rows,
  kind,
  onPreview,
}: {
  rows: TenantIssue[];
  kind: Kind;
  onPreview: (r: TenantIssue) => void;
}) {
  const typeLabel = useMemo(
    () =>
      kind === "actions"
        ? "Acción"
        : kind === "decisions"
          ? "Decisión"
          : "Incidente",
    [kind],
  );
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
        <tr>
          <th className="w-10 px-3 py-2" />
          <th className="px-3 py-2 font-medium">Folio</th>
          <th className="px-3 py-2 font-medium">Título</th>
          <th className="px-3 py-2 font-medium">Tipo</th>
          <th className="px-3 py-2 font-medium">Estado</th>
          <th className="px-3 py-2 font-medium">Proyecto</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
            <td className="px-3 py-2">
              <button
                type="button"
                onClick={() => onPreview(r)}
                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                aria-label="Preview"
              >
                <Eye className="h-3.5 w-3.5" aria-hidden />
              </button>
            </td>
            <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
              {r.folio}
            </td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}/raid?tab=${kind}`}
                className="text-[var(--color-primary)] hover:underline"
              >
                {r.title}
              </Link>
            </td>
            <td className="px-3 py-2 text-[var(--color-secondary)]">{typeLabel}</td>
            <td className="px-3 py-2 text-[var(--color-secondary)]">{r.status}</td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}`}
                className="text-xs text-[var(--color-accent)] hover:underline"
                title={r.project_name}
              >
                <span className="font-mono">{r.project_folio}</span>
                <span className="ml-1 text-[var(--color-secondary)]">
                  — {r.project_name}
                </span>
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ============================== Kanban views ============================= */

// ENH-018: vista Kanban — agrupa por `status` en columnas. Read-only por
// ahora (el drag-drop para cambiar status vive en la página del proyecto
// cuando se implemente, ver US-058 / EP006). Mantener coherencia con el
// diseño del toggle de /admin/projects (mismo look & feel).

const RISK_STATUS_ORDER: RiskStatus[] = [
  "identified",
  "analyzing",
  "mitigating",
  "materialized",
  "closed",
];

const ISSUE_STATUS_ORDER: IssueStatus[] = [
  "open",
  "in_progress",
  "resolved",
  "closed",
];

function BoardColumn({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-[240px] flex-1 flex-col rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]">
      <header className="flex items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-secondary)]">
          {title}
        </span>
        <Badge variant="neutral">{count}</Badge>
      </header>
      <div className="space-y-2 p-2">{children}</div>
    </div>
  );
}

function RiskBoard({
  rows,
  onPreview,
}: {
  rows: TenantRisk[];
  onPreview: (r: TenantRisk) => void;
}) {
  const byStatus = useMemo(() => {
    const groups: Record<RiskStatus, TenantRisk[]> = {
      identified: [],
      analyzing: [],
      mitigating: [],
      materialized: [],
      closed: [],
    };
    for (const r of rows) groups[r.status].push(r);
    return groups;
  }, [rows]);

  return (
    <div className="flex gap-3 overflow-x-auto p-3">
      {RISK_STATUS_ORDER.map((st) => {
        const items = byStatus[st];
        return (
          <BoardColumn
            key={st}
            title={RISK_STATUS_LABEL[st]}
            count={items.length}
          >
            {items.length === 0 ? (
              <p className="px-2 py-3 text-center text-[11px] text-[var(--color-tertiary)]">
                Sin ítems
              </p>
            ) : (
              items.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => onPreview(r)}
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-2 text-left shadow-[var(--shadow-sm)] hover:border-[var(--color-accent)]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[11px] text-[var(--color-tertiary)]">
                      {r.folio}
                    </span>
                    <Badge
                      variant={
                        (r.severity ?? 0) >= 13
                          ? "danger"
                          : (r.severity ?? 0) >= 6
                            ? "warning"
                            : "success"
                      }
                    >
                      {r.severity ?? "—"}
                    </Badge>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[13px] text-[var(--color-primary)]">
                    {r.title}
                  </p>
                  <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
                    {r.project_folio} — {r.project_name}
                  </p>
                </button>
              ))
            )}
          </BoardColumn>
        );
      })}
    </div>
  );
}

function IssueBoard({
  rows,
  kind,
  onPreview,
}: {
  rows: TenantIssue[];
  kind: Kind;
  onPreview: (r: TenantIssue) => void;
}) {
  const byStatus = useMemo(() => {
    const groups: Record<IssueStatus, TenantIssue[]> = {
      open: [],
      in_progress: [],
      resolved: [],
      closed: [],
    };
    for (const r of rows) groups[r.status].push(r);
    return groups;
  }, [rows]);

  void kind; // kind-specific styling podría agregarse después.

  return (
    <div className="flex gap-3 overflow-x-auto p-3">
      {ISSUE_STATUS_ORDER.map((st) => {
        const items = byStatus[st];
        return (
          <BoardColumn
            key={st}
            title={ISSUE_STATUS_LABEL[st]}
            count={items.length}
          >
            {items.length === 0 ? (
              <p className="px-2 py-3 text-center text-[11px] text-[var(--color-tertiary)]">
                Sin ítems
              </p>
            ) : (
              items.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => onPreview(r)}
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-2 text-left shadow-[var(--shadow-sm)] hover:border-[var(--color-accent)]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-[11px] text-[var(--color-tertiary)]">
                      {r.folio}
                    </span>
                    {r.priority ? (
                      <Badge
                        variant={
                          r.priority >= 4
                            ? "danger"
                            : r.priority >= 2
                              ? "warning"
                              : "neutral"
                        }
                      >
                        P{r.priority}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 line-clamp-2 text-[13px] text-[var(--color-primary)]">
                    {r.title}
                  </p>
                  <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
                    {r.project_folio} — {r.project_name}
                  </p>
                </button>
              ))
            )}
          </BoardColumn>
        );
      })}
    </div>
  );
}

export default function TenantRaidPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-[var(--color-tertiary)]">Cargando…</div>}>
      <TenantRaidInner />
    </Suspense>
  );
}
