"use client";

// ENH-186: la vista de Cambios hereda estructura/funcionalidades de las
// listas RAID (sort por columna, filtros, edición inline, export propio),
// quedándose a nivel proyecto. El flujo de aprobación (EP019) se mantiene
// intacto — el estado NO se edita inline.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Download, GitPullRequest, XCircle } from "lucide-react";

import { InlineSelectCell, InlineTextCell } from "@/components/inline-select-cell";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { SortableTh } from "@/components/ui/sortable-th";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiBase } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { cn } from "@/lib/cn";
import {
  CHANGE_FINAL_STATUSES,
  CHANGE_STATUS_BADGE,
  CHANGE_STATUS_LABEL,
  CHANGE_TYPE_LABEL,
  approveChange,
  createChange,
  listChanges,
  rejectChange,
  updateChange,
  type ChangeRequest,
  type ChangeRequestUpdateBody,
  type ChangeStatus,
  type ChangeType,
} from "@/lib/api/modules";

export default function ChangesPage() {
  const { id } = useParams<{ id: string }>();
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

  // ENH-186: filtros estilo RAID (estado + tipo) + toggle finalizados.
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [includeFinalized, setIncludeFinalized] = useState(false);
  const [exporting, setExporting] = useState(false);

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

  // ENH-186: edición inline (título/tipo), patrón US-178 de RAID — update
  // optimista + revert si el PATCH falla. El estado NO se edita aquí.
  async function patchChange(changeId: string, patch: ChangeRequestUpdateBody) {
    setError(null);
    const prev = rows.find((r) => r.id === changeId);
    setRows((rs) => rs.map((r) => (r.id === changeId ? ({ ...r, ...patch } as ChangeRequest) : r)));
    try {
      const updated = await updateChange(changeId, patch);
      setRows((rs) => rs.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)));
    } catch (err) {
      if (prev) setRows((rs) => rs.map((r) => (r.id === changeId ? prev : r)));
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el cambio");
    }
  }

  // ENH-186: export propio (1 hoja "Cambios"), misma descarga autenticada
  // que RAID (ENH-152/168) vía /changes/export.
  async function downloadChanges() {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const token = getAccessToken();
      const headers: Record<string, string> = { Accept: "application/octet-stream" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${apiBase()}/api/v1/projects/${id}/changes/export`, {
        method: "GET",
        headers,
        credentials: "include",
      });
      if (!res.ok) {
        throw new ApiError(res.status, "EXPORT_FAILED", `Exportación falló (HTTP ${res.status})`);
      }
      const cd = res.headers.get("Content-Disposition") ?? "";
      const match = /filename="([^"]+)"/.exec(cd);
      const name = match ? match[1] : `cambios-${id}.xlsx`;
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
      setError(err instanceof ApiError ? err.message : "No se pudo exportar los cambios");
    } finally {
      setExporting(false);
    }
  }

  // ENH-186: filtros (estado/tipo) + oculta finalizados por default.
  const filteredRows = useMemo(() => {
    return rows.filter((r) => {
      if (!includeFinalized && CHANGE_FINAL_STATUSES.includes(r.status)) return false;
      if (statusFilter && r.status !== statusFilter) return false;
      if (typeFilter && r.type !== typeFilter) return false;
      return true;
    });
  }, [rows, statusFilter, typeFilter, includeFinalized]);

  const { sortedRows, ctrl: sortCtrl } = useSortableRows<ChangeRequest>(filteredRows);

  return (
    <>
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
              <span>Cambios</span>
            </nav>
            <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              <GitPullRequest className="h-5 w-5" aria-hidden />
              Cambios
            </h1>
            <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
              Control de cambios de alcance, tiempo, costo o recursos.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="inline-flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] bg-[var(--color-primary)] px-3 text-sm font-medium text-[var(--color-inverse)] shadow-[var(--shadow-sm)] hover:bg-[var(--color-primary-hover)]"
            >
              + Nuevo cambio
            </button>
            <button
              type="button"
              onClick={() => void downloadChanges()}
              disabled={exporting}
              className="inline-flex h-9 shrink-0 items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-subtle)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Download className="h-4 w-4" aria-hidden />
              {exporting ? "Exportando…" : "Exportar"}
            </button>
          </div>
        </header>

        {error ? <Banner variant="danger">{error}</Banner> : null}

        {/* ENH-186: filtros estilo RAID (estado + tipo) + toggle finalizados. */}
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
            {(Object.keys(CHANGE_STATUS_LABEL) as ChangeStatus[]).map((s) => (
              <option key={s} value={s}>
                {CHANGE_STATUS_LABEL[s]}
              </option>
            ))}
          </select>
          <select
            aria-label="Tipo"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-8 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[12px] text-[var(--color-primary)]"
          >
            <option value="">Todos los tipos</option>
            {(Object.keys(CHANGE_TYPE_LABEL) as ChangeType[]).map((t) => (
              <option key={t} value={t}>
                {CHANGE_TYPE_LABEL[t]}
              </option>
            ))}
          </select>
          {/* ENH-186: oculta finalizados (approved/rejected/cancelled) por default. */}
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
        ) : rows.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin cambios registrados. Usa el botón <strong>+ Nuevo cambio</strong> arriba para
            crear el primero.
          </div>
        ) : sortedRows.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
            Ningún cambio coincide con los filtros activos.
          </div>
        ) : (
          <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
            <div className="overflow-x-auto">
              <table className="w-full text-[13px]">
                <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                  <tr>
                    <SortableTh<ChangeRequest> sortKey="folio" getter={(r) => r.folio} ctrl={sortCtrl}>
                      Folio
                    </SortableTh>
                    <SortableTh<ChangeRequest> sortKey="title" getter={(r) => r.title} ctrl={sortCtrl}>
                      Cambio
                    </SortableTh>
                    <SortableTh<ChangeRequest> sortKey="type" getter={(r) => r.type} ctrl={sortCtrl}>
                      Tipo
                    </SortableTh>
                    <SortableTh<ChangeRequest> sortKey="status" getter={(r) => r.status} ctrl={sortCtrl}>
                      Estado
                    </SortableTh>
                    <SortableTh<ChangeRequest>
                      sortKey="requested"
                      getter={(r) => r.requested_at}
                      ctrl={sortCtrl}
                    >
                      Solicitado por
                    </SortableTh>
                    <SortableTh<ChangeRequest>
                      sortKey="approved"
                      getter={(r) => r.approved_at ?? ""}
                      ctrl={sortCtrl}
                    >
                      Aprobado por
                    </SortableTh>
                    <th className="px-2 py-1.5 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRows.map((r) => (
                    <tr
                      key={r.id}
                      className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                    >
                      {/* US-178 (patrón RAID): folio = único link que abre el detalle. */}
                      <td className="px-2 py-1.5 font-mono text-xs text-[var(--color-tertiary)]">
                        <Link
                          href={`/pmo/projects/${id}/changes/${r.id}`}
                          className="hover:text-[var(--color-accent)] hover:underline"
                        >
                          {r.folio}
                        </Link>
                      </td>
                      {/* ENH-186: título editable inline. */}
                      <td className="px-2 py-1.5 text-[var(--color-primary)]">
                        <InlineTextCell
                          value={r.title}
                          onChange={(v) => patchChange(r.id, { title: v })}
                          title="Título"
                          ariaLabel={`Título de ${r.folio}`}
                        />
                      </td>
                      {/* ENH-186: tipo editable inline. */}
                      <td className="px-2 py-1.5 text-[var(--color-secondary)]">
                        <InlineSelectCell
                          value={r.type}
                          options={(Object.keys(CHANGE_TYPE_LABEL) as ChangeType[]).map((t) => ({
                            value: t,
                            label: CHANGE_TYPE_LABEL[t],
                          }))}
                          onChange={(v) => patchChange(r.id, { type: v as ChangeType })}
                          title="Tipo"
                          ariaLabel={`Tipo de ${r.folio}`}
                        />
                      </td>
                      {/* Estado: chip de color, NO editable inline — el flujo de
                          aprobación (EP019) gobierna la transición. */}
                      <td className="px-2 py-1.5">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold",
                            CHANGE_STATUS_BADGE[r.status] ?? "bg-[var(--color-subtle)]",
                          )}
                        >
                          {CHANGE_STATUS_LABEL[r.status] ?? r.status}
                        </span>
                      </td>
                      <td className="px-2 py-1.5">
                        <div className="text-[12px] leading-tight">
                          <div className="text-[var(--text-primary)]">
                            {r.requester?.full_name ?? r.requester?.email ?? "—"}
                          </div>
                          <div className="text-[var(--text-tertiary)]">
                            {new Date(r.requested_at).toLocaleDateString("es-MX")}
                          </div>
                        </div>
                      </td>
                      <td className="px-2 py-1.5">
                        {r.approver ? (
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
                        )}
                      </td>
                      {/* Aprobar/Rechazar se conservan igual que antes (EP019). */}
                      <td className="px-2 py-1.5">
                        {r.status === "in_review" ? (
                          <div className="flex justify-end gap-1.5">
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
                          <span className="flex justify-end text-[11px] text-[var(--text-tertiary)]">
                            —
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>

      <Modal
        open={open}
        onClose={() => !submitting && setOpen(false)}
        title="Solicitar cambio"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)} disabled={submitting}>
              Cancelar
            </Button>
            <Button onClick={submit} loading={submitting} disabled={!form.title.trim()}>
              Solicitar
            </Button>
          </>
        }
      >
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
      </Modal>

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
