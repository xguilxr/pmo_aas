"use client";

import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import {
  ISSUE_STATUS_LABEL,
  RISK_STATUS_LABEL,
  addIssueComment,
  addRiskComment,
  updateIssue,
  updateRisk,
  type Issue,
  type IssueStatus,
  type Risk,
  type RiskStatus,
} from "@/lib/api/modules";

/**
 * Cuerpo editable del panel RAID (US-058 + ENH-027).
 *
 * Originalmente vivía solo en /admin/raid (vista consolidada tenant).
 * ENH-027 extrae los componentes para reusarlos en
 * /admin/projects/[id]/raid (vista por-proyecto). Ambas páginas pasan
 * el mismo recurso `Risk` o `Issue` al panel y obtienen el mismo UX:
 * cambiar estado + agregar comentario, con persistencia compartida.
 *
 * `TenantRisk` extiende `Risk` (mismo set de campos + project_*),
 * por eso el componente acepta el tipo base `Risk` y el caller pasa
 * los datos directamente.
 */

type Comment = { text: string; author_id?: string; created_at?: string };

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

export function RiskDetailBody({
  risk,
  onUpdated,
}: {
  risk: Risk;
  onUpdated: (r: Partial<Risk> & { id: string }) => void;
}) {
  const [status, setStatus] = useState<RiskStatus>(risk.status);
  const [savingStatus, setSavingStatus] = useState(false);
  const [comment, setComment] = useState("");
  const [addingComment, setAddingComment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comments, setComments] = useState<Comment[]>(risk.comments ?? []);

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

export function IssueDetailBody({
  issue,
  onUpdated,
}: {
  issue: Issue;
  onUpdated: (i: Partial<Issue> & { id: string }) => void;
}) {
  const [status, setStatus] = useState<IssueStatus>(issue.status);
  const [savingStatus, setSavingStatus] = useState(false);
  const [comment, setComment] = useState("");
  const [addingComment, setAddingComment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comments, setComments] = useState<Comment[]>(issue.comments ?? []);

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
  comments: Comment[];
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
