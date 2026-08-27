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
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  LESSON_CATEGORY_LABEL,
  LESSON_PHASE_LABEL,
  LESSON_PHASE_ORDER,
  deleteLesson,
  getLesson,
  updateLesson,
  type Lesson,
  type LessonCategory,
  type LessonPhase,
} from "@/lib/api/modules";

/**
 * ENH-086 — página dedicada de Lecciones aprendidas.
 *
 * Reusa el patrón "Denso" de RAID (US-100): header card + strip de
 * metadatos + cards de contenido + edición transaccional con banner
 * (ENH-069 pattern).
 *
 * Nota: el backend no provee comentarios ni historial para Lecciones
 * (ver `apps/api/app/api/v1/endpoints/modules.py` — solo GET/PATCH/POST).
 * La card "Comentarios & Historial" se renderiza con un placeholder y
 * se cablea cuando exista el endpoint correspondiente (diferido).
 */

type EditDraft = {
  title: string;
  description: string;
  category: LessonCategory;
  phase: string;
  recommendation: string;
  tags: string;
};

function draftFromLesson(l: Lesson): EditDraft {
  return {
    title: l.title,
    description: l.description ?? "",
    category: l.category ?? "improvement",
    phase: l.phase ?? "",
    recommendation: l.recommendation ?? "",
    tags: l.tags.join(", "),
  };
}

export function LessonDetailPage({
  lessonId,
  breadcrumb,
}: {
  lessonId: string;
  breadcrumb: React.ReactNode;
}) {
  const router = useRouter();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<EditDraft | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  // ENH-112: borrar la lección.
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getLesson(lessonId)
      .then((l) => {
        if (!cancelled) setLesson(l);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.status === 404
              ? "Esta lección no existe o no tienes permiso para verla."
              : err.message
            : "No se pudo cargar la lección",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lessonId]);

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

  if (!lesson) return null;

  function startEdit() {
    if (!lesson) return;
    setDraft(draftFromLesson(lesson));
    setEditError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setEditError(null);
    setDraft(null);
  }

  async function saveEdit() {
    if (!draft || !lesson || saving) return;
    if (draft.title.trim().length < 2) {
      setEditError("El título es obligatorio (mín. 2 caracteres).");
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      const tags = draft.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const updated = await updateLesson(lesson.id, {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        category: draft.category,
        phase: draft.phase || null,
        recommendation: draft.recommendation.trim() || null,
        tags,
      });
      setLesson(updated);
      setEditing(false);
    } catch (err) {
      setEditError(
        err instanceof ApiError ? err.message : "No se pudo guardar los cambios",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!lesson || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      const projectId = lesson.project_id;
      await deleteLesson(lesson.id);
      router.replace(`/pmo/projects/${projectId}/lessons?deleted=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar la lección");
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  const categoryLabel = lesson.category
    ? LESSON_CATEGORY_LABEL[lesson.category]
    : "—";
  const categoryVariant: "success" | "danger" | "warning" =
    lesson.category === "success"
      ? "success"
      : lesson.category === "error"
        ? "danger"
        : "warning";

  return (
    <div className="mx-auto max-w-5xl space-y-3 p-6">
      <div className="flex items-center justify-between gap-2 px-0">
        <div className="min-w-0 flex-1">{breadcrumb}</div>
        <div className="flex flex-none items-center gap-2">
          <Button
            type="button"
            variant={editing ? "secondary" : "primary"}
            size="sm"
            onClick={() => (editing ? cancelEdit() : startEdit())}
            disabled={saving}
          >
            {editing ? "Editando…" : "Editar"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setConfirmDelete(true)}
            disabled={saving}
            aria-label="Borrar lección"
          >
            <Icono nombre="bin" size={14} /> Borrar
          </Button>
        </div>
      </div>

      {/* Header card + strip */}
      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="flex flex-col gap-2 px-4.5 py-3.5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 flex-none items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)]">
              <Icono nombre="info" size={20} className="text-[var(--color-tertiary)]" />
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-[11px] text-[var(--color-tertiary)]">
                    {lesson.folio}
                  </span>
                  <span className="text-[var(--color-tertiary)]">·</span>
                  <span className="rounded border border-[var(--chrome-soft-border)] bg-[var(--chrome-soft-bg)] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--chrome-soft-text)]">
                    Lección
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {lesson.category ? (
                    <Badge variant={categoryVariant}>{categoryLabel}</Badge>
                  ) : null}
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
                  {lesson.title}
                </h1>
              )}
            </div>
          </div>
        </header>

        <div className="grid gap-4 border-t border-[var(--border-default)] bg-[var(--chrome-soft-bg)] px-4.5 py-3 grid-cols-2 sm:grid-cols-3">
          <StripCell label="Categoría">
            {editing && draft ? (
              <Select
                value={draft.category}
                onChange={(e) =>
                  setDraft({ ...draft, category: e.target.value as LessonCategory })
                }
              >
                {(Object.keys(LESSON_CATEGORY_LABEL) as LessonCategory[]).map((c) => (
                  <option key={c} value={c}>
                    {LESSON_CATEGORY_LABEL[c]}
                  </option>
                ))}
              </Select>
            ) : (
              categoryLabel
            )}
          </StripCell>
          <StripCell label="Fase">
            {editing && draft ? (
              <Select
                value={draft.phase}
                onChange={(e) => setDraft({ ...draft, phase: e.target.value })}
              >
                <option value="">— sin fase —</option>
                {LESSON_PHASE_ORDER.map((f) => (
                  <option key={f} value={f}>
                    {LESSON_PHASE_LABEL[f]}
                  </option>
                ))}
              </Select>
            ) : lesson.phase ? (
              (LESSON_PHASE_LABEL[lesson.phase as LessonPhase] ?? lesson.phase)
            ) : (
              <Empty />
            )}
          </StripCell>
          <StripCell label="Tags">
            {editing && draft ? (
              <Input
                value={draft.tags}
                onChange={(e) => setDraft({ ...draft, tags: e.target.value })}
                placeholder="comma, separated"
              />
            ) : lesson.tags.length ? (
              <div className="flex flex-wrap gap-1">
                {lesson.tags.map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            ) : (
              <Empty />
            )}
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

      {/* Descripción */}
      <DetailCard title="Descripción">
        {editing && draft ? (
          <Textarea
            value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            rows={4}
          />
        ) : lesson.description ? (
          <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
            {lesson.description}
          </p>
        ) : (
          <p className="text-[13px] italic text-[var(--color-tertiary)]">
            Sin descripción.
          </p>
        )}
      </DetailCard>

      {/* Recomendación */}
      <DetailCard title="Recomendación">
        {editing && draft ? (
          <Textarea
            value={draft.recommendation}
            onChange={(e) =>
              setDraft({ ...draft, recommendation: e.target.value })
            }
            rows={3}
          />
        ) : lesson.recommendation ? (
          <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
            {lesson.recommendation}
          </p>
        ) : (
          <p className="text-[13px] italic text-[var(--color-tertiary)]">
            Sin recomendación.
          </p>
        )}
      </DetailCard>

      {/* Proyecto */}
      <DetailCard title="Proyecto">
        <div className="flex items-center gap-2 text-[13px]">
          <Link
            href={`/pmo/projects/${lesson.project_id}`}
            className="font-mono text-[12px] text-[var(--color-accent)] underline-offset-2 hover:underline"
          >
            {lesson.project_id.slice(0, 8)}…
          </Link>
        </div>
      </DetailCard>

      {/* Comentarios & Historial — placeholder hasta endpoint backend. */}
      <DetailCard title="Comentarios & Historial">
        <p className="text-[12px] italic text-[var(--color-tertiary)]">
          Próximamente. Esta lección aún no tiene comentarios ni historial
          registrado.
        </p>
      </DetailCard>

      <Modal
        open={confirmDelete}
        onClose={() => !deleting && setConfirmDelete(false)}
        title="¿Borrar lección?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              <Icono nombre="bin" size={14} /> Borrar
            </Button>
          </>
        }
      >
        <p className="text-[13px] text-[var(--color-primary)]">
          ¿Borrar la lección <strong>{lesson.folio}</strong>? Esta acción la
          retira de la lista y no se puede deshacer.
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

export function LessonBackLink({ href, label }: { href: string; label: string }) {
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
