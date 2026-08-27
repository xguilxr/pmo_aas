"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  CHANGE_STATUS_LABEL,
  CHANGE_TYPE_LABEL,
  cancelChange,
  deleteChange,
  getChange,
  updateChange,
  type ChangeRequest,
  type ChangeStatus,
} from "@/lib/api/modules";

// ENH-186 (rediseño 7a): mismo mapeo de tono que la lista de Cambios —
// in_review -> warning (no "info"), cancelled -> neutral (no "info").
const CHANGE_STATUS_VARIANT: Record<ChangeStatus, "warning" | "success" | "danger" | "neutral"> = {
  in_review: "warning",
  approved: "success",
  rejected: "danger",
  implemented: "success",
  cancelled: "neutral",
};

/**
 * ENH-087 — página dedicada de Cambios.
 *
 * Mismo patrón "Denso" de RAID/Lecciones: header card + strip de
 * metadatos + cards Descripción / Impacto / Aprobadores (placeholder
 * EP019) / Comentarios&Historial (placeholder hasta backend).
 *
 * Edición transaccional aplica solo a `title/description/impact` y
 * únicamente cuando el status es `in_review`. Las transiciones de
 * status (approve/reject) siguen gobernadas por los endpoints
 * dedicados — ver `/pmo/projects/[id]/changes` para el flujo de
 * aprobación.
 */

type EditDraft = {
  title: string;
  description: string;
  impact: string;
};

function draftFromChange(c: ChangeRequest): EditDraft {
  return {
    title: c.title,
    description: c.description ?? "",
    impact: c.impact ?? "",
  };
}

export function ChangeDetailPage({
  changeId,
  breadcrumb,
}: {
  changeId: string;
  breadcrumb: React.ReactNode;
}) {
  const router = useRouter();
  const [change, setChange] = useState<ChangeRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<EditDraft | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  // ENH-112: borrar / cancelar el cambio.
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getChange(changeId)
      .then((c) => {
        if (!cancelled) setChange(c);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.status === 404
              ? "Este cambio no existe o no tienes permiso para verlo."
              : err.message
            : "No se pudo cargar el cambio",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [changeId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        {breadcrumb}
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (!change) return null;

  const editable = change.status === "in_review";

  function startEdit() {
    if (!change) return;
    setDraft(draftFromChange(change));
    setEditError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setEditError(null);
    setDraft(null);
  }

  async function saveEdit() {
    if (!draft || !change || saving) return;
    if (draft.title.trim().length < 2) {
      setEditError("El título es obligatorio (mín. 2 caracteres).");
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      const updated = await updateChange(change.id, {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        impact: draft.impact.trim() || null,
      });
      setChange(updated);
      setEditing(false);
    } catch (err) {
      setEditError(
        err instanceof ApiError ? err.message : "No se pudo guardar los cambios",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleCancel() {
    if (!change || cancelling) return;
    setCancelling(true);
    setError(null);
    try {
      const updated = await cancelChange(change.id);
      setChange(updated);
      setConfirmCancel(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cancelar el cambio");
    } finally {
      setCancelling(false);
    }
  }

  async function handleDelete() {
    if (!change || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      const projectId = change.project_id;
      await deleteChange(change.id);
      router.replace(`/pmo/projects/${projectId}/changes?deleted=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar el cambio");
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  // Se puede cancelar mientras no esté implementado ni ya cancelado.
  const cancellable =
    change.status !== "implemented" && change.status !== "cancelled";

  const statusLabel = CHANGE_STATUS_LABEL[change.status as ChangeStatus] ?? change.status;
  const statusVariant = CHANGE_STATUS_VARIANT[change.status as ChangeStatus] ?? "neutral";

  const fmtDate = (iso: string | null | undefined) => {
    if (!iso) return null;
    try {
      return new Date(iso).toLocaleDateString("es-MX");
    } catch {
      return iso;
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-3 p-6">
      <div className="flex items-center justify-between gap-2 px-0">
        <div className="min-w-0 flex-1">{breadcrumb}</div>
        <div className="flex flex-none items-center gap-2">
          {editable ? (
            <Button
              type="button"
              variant={editing ? "secondary" : "primary"}
              size="sm"
              onClick={() => (editing ? cancelEdit() : startEdit())}
              disabled={saving}
            >
              {editing ? "Editando…" : "Editar"}
            </Button>
          ) : null}
          {cancellable ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setConfirmCancel(true)}
              disabled={saving}
            >
              <Icono nombre="circle-off" size={14} /> Cancelar
            </Button>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setConfirmDelete(true)}
            disabled={saving}
            aria-label="Borrar cambio"
          >
            <Icono nombre="bin" size={14} /> Borrar
          </Button>
        </div>
      </div>

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="flex flex-col gap-2 px-4.5 py-3.5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 flex-none items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)]">
              <Icono nombre="git-branch" size={20} className="text-[var(--color-tertiary)]" />
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-[12px] tracking-[0.01em] text-[var(--color-tertiary)]">
                    {change.folio}
                  </span>
                  <span className="text-[var(--color-tertiary)]">·</span>
                  <span className="rounded border border-[var(--chrome-soft-border)] bg-[var(--chrome-soft-bg)] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--chrome-soft-text)]">
                    Cambio
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant}>{statusLabel}</Badge>
                  <Badge>{CHANGE_TYPE_LABEL[change.type] ?? change.type}</Badge>
                </div>
              </div>
              {editing && draft ? (
                <Input
                  value={draft.title}
                  onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  className="text-[17px] font-semibold"
                />
              ) : (
                <h1
                  className="text-[17px] font-semibold leading-snug text-[var(--color-primary)]"
                  style={{ lineHeight: 1.4 }}
                >
                  {change.title}
                </h1>
              )}
            </div>
          </div>
        </header>

        <div className="grid gap-4 border-t border-[var(--border-default)] bg-[var(--chrome-soft-bg)] px-4.5 py-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
          <StripCell label="Tipo">
            {CHANGE_TYPE_LABEL[change.type] ?? change.type}
          </StripCell>
          <StripCell label="Estado">{statusLabel}</StripCell>
          <StripCell label="Solicitado por">
            {change.requester?.full_name || change.requester?.email || <Empty />}
          </StripCell>
          <StripCell label="F. Solicitud">
            {fmtDate(change.requested_at) ?? <Empty />}
          </StripCell>
          <StripCell label="F. Decisión">
            {fmtDate(change.approved_at) ?? <Empty />}
          </StripCell>
        </div>
      </section>

      {editing ? (
        <section className="flex items-center justify-between gap-3 rounded-[var(--radius-xl)] border border-[var(--color-info-border)] bg-[var(--color-info-bg)] px-4.5 py-2.5">
          <p className="text-[13px] text-[var(--color-info-fg)]">
            Modo edición activo.
          </p>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={cancelEdit}
              disabled={saving}
            >
              Cancelar
            </Button>
            <Button type="button" size="sm" onClick={saveEdit} loading={saving}>
              Guardar
            </Button>
          </div>
        </section>
      ) : null}

      {editError ? <Banner variant="danger">{editError}</Banner> : null}

      <DetailCard title="Descripción">
        {editing && draft ? (
          <Textarea
            value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            rows={4}
          />
        ) : change.description ? (
          <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
            {change.description}
          </p>
        ) : (
          <p className="text-[13px] italic text-[var(--color-tertiary)]">
            Sin descripción.
          </p>
        )}
      </DetailCard>

      <DetailCard title="Impacto esperado">
        {editing && draft ? (
          <Textarea
            value={draft.impact}
            onChange={(e) => setDraft({ ...draft, impact: e.target.value })}
            rows={3}
          />
        ) : change.impact ? (
          <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
            {change.impact}
          </p>
        ) : (
          <p className="text-[13px] italic text-[var(--color-tertiary)]">
            Sin impacto registrado.
          </p>
        )}
      </DetailCard>

      {/* CA6: placeholder Aprobadores hasta EP019 (US-112/US-113). */}
      <DetailCard title="Aprobadores">
        {change.approver ? (
          <div className="space-y-1 text-[13px]">
            <p className="text-[var(--color-primary)]">
              <span className="font-semibold">
                {change.approver.full_name || change.approver.email}
              </span>{" "}
              <span className="text-[var(--color-tertiary)]">
                · {fmtDate(change.approved_at)}
              </span>
            </p>
            <p className="text-[12px] text-[var(--color-tertiary)]">
              Decisión: {statusLabel}
            </p>
          </div>
        ) : (
          <p className="text-[12px] italic text-[var(--color-tertiary)]">
            Sin aprobadores registrados. El workflow multi-aprobador llega
            con EP019 (US-112/US-113).
          </p>
        )}
      </DetailCard>

      <DetailCard title="Proyecto">
        <div className="flex items-center gap-2 text-[13px]">
          <Link
            href={`/pmo/projects/${change.project_id}`}
            className="font-mono text-[12px] text-[var(--color-accent)] underline-offset-2 hover:underline"
          >
            {change.project_id.slice(0, 8)}…
          </Link>
        </div>
      </DetailCard>

      {/* Comentarios & Historial — placeholder hasta endpoints backend. */}
      <DetailCard title="Comentarios & Historial">
        <p className="text-[12px] italic text-[var(--color-tertiary)]">
          Próximamente. Este cambio aún no tiene comentarios ni historial
          registrado.
        </p>
      </DetailCard>

      <Modal
        open={confirmCancel}
        onClose={() => !cancelling && setConfirmCancel(false)}
        title="¿Cancelar cambio?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmCancel(false)} disabled={cancelling}>
              Volver
            </Button>
            <Button variant="danger" onClick={handleCancel} loading={cancelling}>
              <Icono nombre="circle-off" size={14} /> Cancelar cambio
            </Button>
          </>
        }
      >
        <p className="text-[13px] text-[var(--color-primary)]">
          El cambio <strong>{change.folio}</strong> quedará con estado
          “Cancelado”. Permanece visible para trazabilidad y se invalidan los
          links de aprobación pendientes.
        </p>
      </Modal>

      <Modal
        open={confirmDelete}
        onClose={() => !deleting && setConfirmDelete(false)}
        title="¿Borrar cambio?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Volver
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              <Icono nombre="bin" size={14} /> Borrar
            </Button>
          </>
        }
      >
        <p className="text-[13px] text-[var(--color-primary)]">
          ¿Borrar el cambio <strong>{change.folio}</strong>? Se retira de la
          lista. Si querés conservar la trazabilidad de aprobaciones, usá
          “Cancelar” en su lugar.
        </p>
      </Modal>
    </div>
  );
}

function DetailCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <header className="border-b border-[var(--border-default)] px-4 py-2.5">
        <h2 className="text-[13px] font-semibold text-[var(--color-primary)]">
          {title}
        </h2>
      </header>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}

function StripCell({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
        {label}
      </p>
      <div className="mt-0.5 break-words text-[13px] text-[var(--color-primary)]">
        {children}
      </div>
    </div>
  );
}

function Empty() {
  return <span className="text-[var(--color-tertiary)]">—</span>;
}

export function ChangeBackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
    >
      <Icono nombre="arrow-left" size={14} />
      {label}
    </Link>
  );
}
