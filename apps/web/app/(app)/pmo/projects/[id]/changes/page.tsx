"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckCircle2, GitPullRequest, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  CHANGE_STATUS_LABEL,
  CHANGE_TYPE_LABEL,
  approveChange,
  createChange,
  listChanges,
  rejectChange,
  type ChangeRequest,
  type ChangeStatus,
  type ChangeType,
} from "@/lib/api/modules";

export default function ChangesPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rows, setRows] = useState<ChangeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<{
    title: string;
    description: string;
    type: ChangeType;
    impact: string;
  }>({ title: "", description: "", type: "scope", impact: "" });

  const [reviewFor, setReviewFor] = useState<ChangeRequest | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"approve" | "reject">("approve");
  const [reviewComment, setReviewComment] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listChanges(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los cambios");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submit() {
    setSubmitting(true);
    try {
      await createChange(id, {
        title: form.title,
        description: form.description || null,
        type: form.type,
        impact: form.impact || null,
      });
      setForm({ title: "", description: "", type: "scope", impact: "" });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el cambio");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitReview() {
    if (!reviewFor) return;
    setReviewSubmitting(true);
    try {
      if (reviewDecision === "approve") {
        await approveChange(reviewFor.id, reviewComment ? { comment: reviewComment } : undefined);
      } else {
        if (!reviewComment.trim()) {
          setError("El motivo de rechazo es obligatorio");
          return;
        }
        await rejectChange(reviewFor.id, { comment: reviewComment });
      }
      setReviewFor(null);
      setReviewComment("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la decisión");
    } finally {
      setReviewSubmitting(false);
    }
  }

  return (
    <>
      <ModuleShell<ChangeRequest>
        projectId={id}
        title="Cambios"
        subtitle="Control de cambios de alcance, tiempo, costo o recursos."
        icon={<GitPullRequest className="h-5 w-5" aria-hidden />}
        records={rows}
        loading={loading}
        error={error}
        onRowClick={(r) => router.push(`/pmo/projects/${id}/changes/${r.id}`)}
        newButtonLabel="Nuevo cambio"
        newModalTitle="Solicitar cambio"
        newModalOpen={open}
        setNewModalOpen={setOpen}
        newModalForm={() => (
          <div className="space-y-3">
            <Field label="Título">
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Descripción">
              <Textarea
                rows={3}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </Field>
            <Field label="Tipo">
              <Select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value as ChangeType })}
              >
                {(Object.keys(CHANGE_TYPE_LABEL) as ChangeType[]).map((t) => (
                  <option key={t} value={t}>
                    {CHANGE_TYPE_LABEL[t]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Impacto esperado">
              <Textarea
                rows={2}
                value={form.impact}
                onChange={(e) => setForm({ ...form, impact: e.target.value })}
              />
            </Field>
          </div>
        )}
        newModalFooter={(close) => (
          <>
            <Button variant="secondary" onClick={close} disabled={submitting}>
              Cancelar
            </Button>
            <Button onClick={submit} loading={submitting} disabled={!form.title.trim()}>
              Solicitar
            </Button>
          </>
        )}
        columns={[
          {
            key: "title",
            label: "Cambio",
            render: (r) => <span className="font-medium">{r.title}</span>,
          },
          {
            key: "type",
            label: "Tipo",
            render: (r) => <Badge>{CHANGE_TYPE_LABEL[r.type]}</Badge>,
          },
          {
            key: "status",
            label: "Estado",
            render: (r) => (
              <Badge
                variant={
                  r.status === "approved"
                    ? "success"
                    : r.status === "rejected"
                      ? "danger"
                      : r.status === "implemented"
                        ? "success"
                        : "info"
                }
              >
                {CHANGE_STATUS_LABEL[r.status as ChangeStatus]}
              </Badge>
            ),
          },
          {
            key: "requested",
            label: "Solicitado por",
            render: (r) => (
              <div className="text-[12px] leading-tight">
                <div className="text-[var(--text-primary)]">
                  {r.requester?.full_name ?? r.requester?.email ?? "—"}
                </div>
                <div className="text-[var(--text-tertiary)]">
                  {new Date(r.requested_at).toLocaleDateString("es-MX")}
                </div>
              </div>
            ),
          },
          {
            key: "approved",
            label: "Aprobado por",
            render: (r) =>
              r.approver ? (
                <div className="text-[12px] leading-tight">
                  <div className="text-[var(--text-primary)]">
                    {r.approver.full_name ?? r.approver.email}
                  </div>
                  <div className="text-[var(--text-tertiary)]">
                    {r.approved_at ? new Date(r.approved_at).toLocaleDateString("es-MX") : ""}
                  </div>
                </div>
              ) : (
                <span className="text-[11px] text-[var(--text-tertiary)]">—</span>
              ),
          },
          {
            key: "actions",
            label: "",
            render: (r) =>
              r.status === "in_review" ? (
                <div className="flex gap-1.5">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      setReviewFor(r);
                      setReviewDecision("approve");
                    }}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                    Aprobar
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      setReviewFor(r);
                      setReviewDecision("reject");
                    }}
                  >
                    <XCircle className="h-3.5 w-3.5" aria-hidden />
                    Rechazar
                  </Button>
                </div>
              ) : (
                <span className="text-[11px] text-[var(--text-tertiary)]">—</span>
              ),
          },
        ]}
      />

      <Modal
        open={reviewFor !== null}
        onClose={() => !reviewSubmitting && setReviewFor(null)}
        title={reviewDecision === "approve" ? "Aprobar cambio" : "Rechazar cambio"}
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setReviewFor(null)}
              disabled={reviewSubmitting}
            >
              Cancelar
            </Button>
            <Button onClick={submitReview} loading={reviewSubmitting}>
              Confirmar
            </Button>
          </>
        }
      >
        <Field
          label={reviewDecision === "approve" ? "Comentario (opcional)" : "Motivo del rechazo"}
        >
          <Textarea
            rows={3}
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
          />
        </Field>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
    </label>
  );
}
