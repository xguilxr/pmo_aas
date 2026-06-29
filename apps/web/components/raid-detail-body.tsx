"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
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
 * Originalmente vivía solo en /pmo/raid (vista consolidada tenant).
 * ENH-027 extrae los componentes para reusarlos en
 * /pmo/projects/[id]/raid (vista por-proyecto). Ambas páginas pasan
 * el mismo recurso `Risk` o `Issue` al panel y obtienen el mismo UX:
 * cambiar estado + agregar comentario, con persistencia compartida.
 *
 * `TenantRisk` extiende `Risk` (mismo set de campos + project_*),
 * por eso el componente acepta el tipo base `Risk` y el caller pasa
 * los datos directamente.
 */

type CommentAuthor = {
  id: string;
  full_name?: string | null;
  email?: string | null;
};
type Comment = {
  text: string;
  author_id?: string;
  created_at?: string;
  author?: CommentAuthor | null;
};

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

function commentAuthorLabel(c: Comment): string {
  // BUG-035: prefiere full_name → email → "Usuario eliminado" (cuando
  // hay author_id pero el user fue borrado) → "—".
  const a = c.author;
  if (a) {
    return a.full_name?.trim() || a.email?.trim() || "Usuario eliminado";
  }
  if (c.author_id) return "Usuario eliminado";
  return "—";
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
  const [closurePending, setClosurePending] = useState<RiskStatus | null>(null);
  const [closureNote, setClosureNote] = useState("");
  const [closureError, setClosureError] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    setStatus(risk.status);
    setComments(risk.comments ?? []);
    setComment("");
    setError(null);
  }, [risk.id, risk.status, risk.comments]);

  useEffect(() => {
    if (!savedFlash) return;
    const t = setTimeout(() => setSavedFlash(false), 1500);
    return () => clearTimeout(t);
  }, [savedFlash]);

  async function applyStatusChange(
    next: RiskStatus,
    onHoldReasonValue?: string,
  ) {
    setSavingStatus(true);
    setError(null);
    try {
      // US-179: al pasar a On Hold se envía la razón de detención.
      const payload: { status: RiskStatus; on_hold_reason?: string | null } = {
        status: next,
      };
      if (next === "on_hold" && onHoldReasonValue)
        payload.on_hold_reason = onHoldReasonValue;
      const updated = await updateRisk(risk.id, payload);
      setStatus(updated.status);
      setSavedFlash(true);
      onUpdated({ id: updated.id, status: updated.status });
      return true;
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al guardar el estado",
      );
      setStatus(risk.status);
      return false;
    } finally {
      setSavingStatus(false);
    }
  }

  function changeStatus(next: RiskStatus) {
    if (next === status) return;
    // US-179: On Hold requiere razón de detención (modal).
    if (next === "on_hold") {
      setStatus(next);
      setClosureNote("");
      setClosureError(null);
      setClosurePending(next);
      return;
    }
    void applyStatusChange(next);
  }

  function cancelClosure() {
    setClosurePending(null);
    setClosureNote("");
    setClosureError(null);
    setStatus(risk.status);
  }

  async function confirmClosure() {
    if (!closurePending) return;
    const trimmed = closureNote.trim();
    if (trimmed.length < 2) {
      setClosureError("La razón de detención es obligatoria (mín. 2 caracteres).");
      return;
    }
    const ok = await applyStatusChange(closurePending, trimmed);
    if (ok) {
      setClosurePending(null);
      setClosureNote("");
      setClosureError(null);
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
        <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <span>Estado</span>
          {savingStatus ? (
            <Loader2
              className="h-3 w-3 animate-spin text-[var(--color-tertiary)]"
              aria-label="Guardando"
            />
          ) : savedFlash ? (
            <Check
              className="h-3 w-3 text-[var(--color-success-fg)]"
              aria-label="Guardado"
            />
          ) : null}
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
      <Modal
        open={closurePending !== null}
        onClose={cancelClosure}
        title="Razón de detención"
        description="Documenta por qué el ítem queda On Hold (mín. 2 caracteres). La dependencia (área/responsable) se completa en el form de edición."
        footer={
          <>
            <Button
              variant="ghost"
              onClick={cancelClosure}
              disabled={savingStatus}
            >
              Cancelar
            </Button>
            <Button onClick={confirmClosure} disabled={savingStatus}>
              {savingStatus ? "Guardando…" : "Confirmar"}
            </Button>
          </>
        }
      >
        <Textarea
          value={closureNote}
          onChange={(e) => setClosureNote(e.target.value)}
          placeholder="Nota de cierre…"
          rows={4}
          autoFocus
          disabled={savingStatus}
        />
        {closureError ? (
          <p className="mt-2 text-xs text-[var(--color-danger-fg)]">
            {closureError}
          </p>
        ) : null}
      </Modal>
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
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    setStatus(issue.status);
    setComments(issue.comments ?? []);
    setComment("");
    setError(null);
  }, [issue.id, issue.status, issue.comments]);

  useEffect(() => {
    if (!savedFlash) return;
    const t = setTimeout(() => setSavedFlash(false), 1500);
    return () => clearTimeout(t);
  }, [savedFlash]);

  async function changeStatus(next: IssueStatus) {
    if (next === status) return;
    setSavingStatus(true);
    setError(null);
    try {
      const updated = await updateIssue(issue.id, { status: next });
      setStatus(updated.status);
      setSavedFlash(true);
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
        <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <span>Estado</span>
          {savingStatus ? (
            <Loader2
              className="h-3 w-3 animate-spin text-[var(--color-tertiary)]"
              aria-label="Guardando"
            />
          ) : savedFlash ? (
            <Check
              className="h-3 w-3 text-[var(--color-success-fg)]"
              aria-label="Guardado"
            />
          ) : null}
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
                <span className="font-medium text-[var(--color-secondary)]">
                  {commentAuthorLabel(c)}
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
