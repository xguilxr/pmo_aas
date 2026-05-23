"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Download,
  MessageSquare,
  Pencil,
  Plus,
  Save,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { MinuteRaidSuggestionsEditor } from "@/components/minute-raid-suggestions-editor";
import { ApiError } from "@/lib/api";
import {
  deleteMinute,
  exportMinute,
  getMinute,
  updateMinute,
  type MeetingMinute,
  type MinuteAgreement,
  type MinuteExportFormat,
  type MinuteParticipant,
  type MinuteTopic,
} from "@/lib/api/modules";

/**
 * ENH-090 — preview de minuta in-platform.
 *
 * Render HTML embebido (sin pop-up) con secciones colapsables: Resumen,
 * Participantes, Temas, Acuerdos + el editor de Sugerencias RAID
 * (US-108). Header con acciones: Descargar (PDF/DOCX), Borrar
 * (ENH-091) y ← Volver. Botón "Pop-up" opcional para usuarios que
 * prefieran ventana externa (CA4 — diferido a cuando lo pidan).
 *
 * Layout limpio sin sidebar — dentro del shell de la app pero la página
 * ocupa todo el ancho (max-w-5xl).
 *
 * ENH-118 (2026-05-23): MD/TXT removidos del export. El backend sigue
 * aceptándolos por compat, pero la UI no los ofrece más.
 */
const EXPORT_FORMATS: Array<{ key: MinuteExportFormat; label: string }> = [
  { key: "pdf", label: "PDF" },
  { key: "docx", label: "DOCX" },
];

export default function MinutePreviewPage() {
  const { id, minuteId } = useParams<{ id: string; minuteId: string }>();
  const router = useRouter();
  const [minute, setMinute] = useState<MeetingMinute | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyExport, setBusyExport] = useState<MinuteExportFormat | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getMinute(minuteId)
      .then((m) => {
        if (!cancelled) setMinute(m);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.status === 404
              ? "Esta minuta no existe o no tienes permiso para verla."
              : err.message
            : "No se pudo cargar la minuta",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [minuteId]);

  async function handleExport(format: MinuteExportFormat) {
    setBusyExport(format);
    try {
      await exportMinute(minuteId, format);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al exportar");
    } finally {
      setBusyExport(null);
    }
  }

  // ENH-091: borrar la minuta desde el header del preview.
  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteMinute(minuteId);
      router.replace(`/pmo/projects/${id}/minutes?deleted=1`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo borrar la minuta",
      );
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error && !minute) {
    return (
      <div className="mx-auto max-w-5xl space-y-3 p-6">
        <Link
          href={`/pmo/projects/${id}/minutes`}
          className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Volver
        </Link>
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }
  if (!minute) return null;

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <nav className="text-[11px] text-[var(--text-tertiary)]">
        <Link href={`/pmo/projects/${id}/minutes`} className="hover:underline">
          Minutas
        </Link>
        <span className="mx-1">/</span>
        <span className="font-mono text-[var(--color-secondary)]">
          {minute.folio}
        </span>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <Link
            href={`/pmo/projects/${id}/minutes`}
            className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Volver
          </Link>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            <MessageSquare className="h-6 w-6 text-[var(--color-accent)]" aria-hidden />
            {minute.title}
          </h1>
          <p className="text-[12px] text-[var(--text-tertiary)]">
            {new Date(minute.meeting_date).toLocaleString("es-MX", {
              dateStyle: "medium",
              timeStyle: "short",
            })}
            {minute.generated_by_ai ? (
              <>
                {" · "}
                <Badge variant="info">
                  <Sparkles className="h-3 w-3" aria-hidden /> IA
                </Badge>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {EXPORT_FORMATS.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={() => void handleExport(f.key)}
              disabled={busyExport !== null}
              className="inline-flex h-8 items-center gap-1 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2.5 text-[12px] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)] disabled:opacity-60"
            >
              {busyExport === f.key ? (
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--color-accent)]" />
              ) : (
                <Download className="h-3.5 w-3.5" aria-hidden />
              )}
              {f.label}
            </button>
          ))}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setConfirmDelete(true)}
            aria-label="Borrar minuta"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden /> Borrar
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {/* ENH-095 — Editor estructurado por secciones (participants / topics
          / agreements). Cada sección tiene "Editar" → forms inline →
          "Guardar / Cancelar"; al guardar, PATCH `/meeting-minutes/{id}`
          y el state local se sincroniza con la respuesta. */}
      <ParticipantsSection minute={minute} setMinute={setMinute} />
      <TopicsSection minute={minute} setMinute={setMinute} />
      <AgreementsSection minute={minute} setMinute={setMinute} />

      {/* US-108: editor de sugerencias RAID embebido en el preview. */}
      <MinuteRaidSuggestionsEditor
        minute={minute}
        onMinuteChanged={setMinute}
      />

      {/* CA4 (diferido): botón "Pop-up" para abrir en ventana externa.
          Cuando un usuario lo pida, abrir window.open con vista
          /pdf-preview o similar. */}

      <Modal
        open={confirmDelete}
        onClose={() => !deleting && setConfirmDelete(false)}
        title="¿Borrar minuta?"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setConfirmDelete(false)}
              disabled={deleting}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              loading={deleting}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden /> Borrar
            </Button>
          </>
        }
      >
        <p className="text-[13px] text-[var(--text-primary)]">
          ¿Borrar minuta <strong>{minute.title}</strong>? Esta acción no se
          puede deshacer.
        </p>
        <p className="mt-2 text-[12px] text-[var(--text-tertiary)]">
          Tickets RAID generados a partir de esta minuta NO se borrarán; solo
          se rompe el link de origen.
        </p>
      </Modal>
    </div>
  );
}

function CollapsibleSection({
  title,
  defaultOpen,
  actions,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <details
      open={defaultOpen}
      className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]"
    >
      <summary className="flex cursor-pointer items-center justify-between gap-2 border-b border-[var(--border-default)] px-4 py-2.5 text-[13px] font-semibold text-[var(--color-primary)]">
        <span>{title}</span>
        {actions ? (
          <span
            className="flex items-center gap-1.5"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") e.stopPropagation();
            }}
          >
            {actions}
          </span>
        ) : null}
      </summary>
      <div className="px-4 py-3">{children}</div>
    </details>
  );
}

// ENH-095 helpers ----------------------------------------------------------

function useSectionSave<T>(
  minuteId: string,
  setMinute: (m: MeetingMinute) => void,
) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(field: "participants" | "topics" | "agreements", value: T) {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateMinute(minuteId, {
        [field]: value as never,
      });
      setMinute(updated);
      return true;
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudieron guardar los cambios",
      );
      return false;
    } finally {
      setSaving(false);
    }
  }
  return { save, saving, error };
}

function ParticipantsSection({
  minute,
  setMinute,
}: {
  minute: MeetingMinute;
  setMinute: (m: MeetingMinute) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<MinuteParticipant[]>(minute.participants);
  const { save, saving, error } = useSectionSave<MinuteParticipant[]>(
    minute.id,
    setMinute,
  );
  function start() {
    setDraft(minute.participants);
    setEditing(true);
  }
  async function commit() {
    const cleaned = draft
      .map((p) => ({ ...p, name: (p.name ?? "").trim() }))
      .filter((p) => p.name.length > 0);
    const ok = await save("participants", cleaned);
    if (ok) setEditing(false);
  }
  return (
    <CollapsibleSection
      title="Participantes"
      defaultOpen
      actions={
        editing ? (
          <>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={saving}>
              <X className="h-3.5 w-3.5" aria-hidden /> Cancelar
            </Button>
            <Button size="sm" onClick={commit} loading={saving}>
              <Save className="h-3.5 w-3.5" aria-hidden /> Guardar
            </Button>
          </>
        ) : (
          <Button size="sm" variant="ghost" onClick={start}>
            <Pencil className="h-3.5 w-3.5" aria-hidden /> Editar
          </Button>
        )
      }
    >
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {!editing ? (
        minute.participants.length === 0 ? (
          <p className="text-[12px] italic text-[var(--text-tertiary)]">
            Sin participantes.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-1.5">
            {minute.participants.map((p, i) => {
              // ENH-103: chip color refleja el match contra actors del
              // proyecto. matched (actor existente) = success/verde;
              // auto_created (creado on-the-fly, pending verificación) =
              // warning/amarillo. Sin match_status (legacy / minutas
              // pre-ENH-103) = neutral.
              const match = (p as { match_status?: string }).match_status;
              const variant: "success" | "warning" | "neutral" =
                match === "matched"
                  ? "success"
                  : match === "auto_created"
                    ? "warning"
                    : "neutral";
              return (
                <li key={i}>
                  <Badge variant={variant}>
                    {p.role ? `${p.name} · ${p.role}` : p.name}
                    {match === "auto_created" ? " ·  nuevo" : null}
                  </Badge>
                </li>
              );
            })}
          </ul>
        )
      ) : (
        <div className="space-y-2">
          {draft.map((p, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2">
              <Input
                className="flex-1 min-w-[180px]"
                value={p.name ?? ""}
                onChange={(e) =>
                  setDraft((d) =>
                    d.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)),
                  )
                }
                placeholder="Nombre"
              />
              <Input
                className="w-[180px]"
                value={p.role ?? ""}
                onChange={(e) =>
                  setDraft((d) =>
                    d.map((x, j) => (j === i ? { ...x, role: e.target.value } : x)),
                  )
                }
                placeholder="Rol (opcional)"
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setDraft((d) => d.filter((_, j) => j !== i))}
                aria-label={`Quitar ${p.name || "participante"}`}
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden />
              </Button>
            </div>
          ))}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setDraft((d) => [...d, { name: "", role: "" }])}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Agregar participante
          </Button>
        </div>
      )}
    </CollapsibleSection>
  );
}

function TopicsSection({
  minute,
  setMinute,
}: {
  minute: MeetingMinute;
  setMinute: (m: MeetingMinute) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<MinuteTopic[]>(minute.topics);
  const { save, saving, error } = useSectionSave<MinuteTopic[]>(
    minute.id,
    setMinute,
  );
  function start() {
    setDraft(minute.topics);
    setEditing(true);
  }
  async function commit() {
    const cleaned = draft
      .map((t) => ({
        ...t,
        title: (t.title ?? "").trim(),
        notes: (t.notes ?? "").trim(),
      }))
      .filter((t) => t.title.length > 0 || t.notes.length > 0);
    const ok = await save("topics", cleaned);
    if (ok) setEditing(false);
  }
  return (
    <CollapsibleSection
      title={`Temas (${minute.topics.length})`}
      defaultOpen
      actions={
        editing ? (
          <>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={saving}>
              <X className="h-3.5 w-3.5" aria-hidden /> Cancelar
            </Button>
            <Button size="sm" onClick={commit} loading={saving}>
              <Save className="h-3.5 w-3.5" aria-hidden /> Guardar
            </Button>
          </>
        ) : (
          <Button size="sm" variant="ghost" onClick={start}>
            <Pencil className="h-3.5 w-3.5" aria-hidden /> Editar
          </Button>
        )
      }
    >
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {!editing ? (
        minute.topics.length === 0 ? (
          <p className="text-[12px] italic text-[var(--text-tertiary)]">
            Sin temas.
          </p>
        ) : (
          <ul className="space-y-2">
            {minute.topics.map((t, i) => (
              <li
                key={i}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3"
              >
                <p className="text-[13px] font-medium text-[var(--text-primary)]">
                  {t.title}
                </p>
                {t.notes ? (
                  <p className="mt-1 whitespace-pre-wrap text-[12px] text-[var(--text-secondary)]">
                    {t.notes}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )
      ) : (
        <div className="space-y-3">
          {draft.map((t, i) => (
            <div
              key={i}
              className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3"
            >
              <Input
                value={t.title ?? ""}
                onChange={(e) =>
                  setDraft((d) =>
                    d.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)),
                  )
                }
                placeholder="Título del tema"
              />
              <Textarea
                rows={4}
                value={t.notes ?? ""}
                onChange={(e) =>
                  setDraft((d) =>
                    d.map((x, j) => (j === i ? { ...x, notes: e.target.value } : x)),
                  )
                }
                placeholder="Notas (2-5 oraciones con contexto, responsables, fechas, próximos pasos)"
              />
              <div className="flex justify-end">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDraft((d) => d.filter((_, j) => j !== i))}
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden /> Quitar tema
                </Button>
              </div>
            </div>
          ))}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setDraft((d) => [...d, { title: "", notes: "" }])}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Agregar tema
          </Button>
        </div>
      )}
    </CollapsibleSection>
  );
}

function AgreementsSection({
  minute,
  setMinute,
}: {
  minute: MeetingMinute;
  setMinute: (m: MeetingMinute) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<MinuteAgreement[]>(minute.agreements);
  const { save, saving, error } = useSectionSave<MinuteAgreement[]>(
    minute.id,
    setMinute,
  );
  function start() {
    setDraft(minute.agreements);
    setEditing(true);
  }
  async function commit() {
    const cleaned = draft
      .map((a) => ({
        ...a,
        description: (a.description ?? "").trim(),
      }))
      .filter((a) => a.description.length > 0);
    const ok = await save("agreements", cleaned);
    if (ok) setEditing(false);
  }
  return (
    <CollapsibleSection
      title={`Acuerdos (${minute.agreements.length})`}
      actions={
        editing ? (
          <>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={saving}>
              <X className="h-3.5 w-3.5" aria-hidden /> Cancelar
            </Button>
            <Button size="sm" onClick={commit} loading={saving}>
              <Save className="h-3.5 w-3.5" aria-hidden /> Guardar
            </Button>
          </>
        ) : (
          <Button size="sm" variant="ghost" onClick={start}>
            <Pencil className="h-3.5 w-3.5" aria-hidden /> Editar
          </Button>
        )
      }
    >
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {!editing ? (
        minute.agreements.length === 0 ? (
          <p className="text-[12px] italic text-[var(--text-tertiary)]">
            Sin acuerdos.
          </p>
        ) : (
          <ul className="space-y-1.5 text-[13px] text-[var(--text-primary)]">
            {minute.agreements.map((a, i) => (
              <li key={i}>
                · {a.description}
                {a.due_date ? (
                  <span className="ml-1 text-[var(--text-tertiary)]">
                    → {a.due_date}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )
      ) : (
        <div className="space-y-2">
          {draft.map((a, i) => (
            <div
              key={i}
              className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3"
            >
              <Textarea
                rows={2}
                value={a.description ?? ""}
                onChange={(e) =>
                  setDraft((d) =>
                    d.map((x, j) =>
                      j === i ? { ...x, description: e.target.value } : x,
                    ),
                  )
                }
                placeholder="Descripción del acuerdo"
              />
              <div className="flex flex-wrap gap-2">
                <Input
                  className="w-[180px]"
                  value={a.owner ?? ""}
                  onChange={(e) =>
                    setDraft((d) =>
                      d.map((x, j) => (j === i ? { ...x, owner: e.target.value } : x)),
                    )
                  }
                  placeholder="Responsable"
                />
                <Input
                  className="w-[160px]"
                  type="date"
                  value={a.due_date ?? ""}
                  onChange={(e) =>
                    setDraft((d) =>
                      d.map((x, j) =>
                        j === i ? { ...x, due_date: e.target.value || undefined } : x,
                      ),
                    )
                  }
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDraft((d) => d.filter((_, j) => j !== i))}
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden /> Quitar
                </Button>
              </div>
            </div>
          ))}
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              setDraft((d) => [
                ...d,
                { description: "", owner: undefined, due_date: undefined },
              ])
            }
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Agregar acuerdo
          </Button>
        </div>
      )}
    </CollapsibleSection>
  );
}

