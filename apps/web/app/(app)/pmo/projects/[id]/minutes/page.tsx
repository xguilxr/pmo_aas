"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Download, Eye, MessageSquare, Plus, Sparkles, Trash2 } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  createMinute,
  exportMinute,
  listMinutes,
  type MeetingMinute,
  type MinuteAgreement,
  type MinuteExportFormat,
  type MinuteParticipant,
  type MinuteTopic,
} from "@/lib/api/modules";

export default function MinutesPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<MeetingMinute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<MeetingMinute | null>(null);

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [participants, setParticipants] = useState<MinuteParticipant[]>([]);
  const [topics, setTopics] = useState<MinuteTopic[]>([]);
  const [agreements, setAgreements] = useState<MinuteAgreement[]>([]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listMinutes(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las minutas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function reset() {
    setTitle("");
    setMeetingDate("");
    setParticipants([]);
    setTopics([]);
    setAgreements([]);
  }

  async function submit() {
    setSubmitting(true);
    try {
      await createMinute(id, {
        title,
        meeting_date: new Date(meetingDate || Date.now()).toISOString(),
        participants,
        topics,
        agreements,
      });
      reset();
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la minuta");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
    <ModuleShell<MeetingMinute>
      projectId={id}
      title="Minutas"
      subtitle="Minutas de reunión con temas, participantes y acuerdos."
      icon={<MessageSquare className="h-5 w-5" aria-hidden />}
      records={rows}
      loading={loading}
      error={error}
      headerExtras={
        <Link href={`/pmo/projects/${id}/ai-minutes/new`} title="Sube la transcripción y la IA genera la minuta automáticamente.">
          <Button>
            <Sparkles className="h-4 w-4" aria-hidden /> Generar con IA
          </Button>
        </Link>
      }
      newButtonLabel="Llenar manualmente"
      newButtonVariant="secondary"
      newModalTitle="Registrar minuta"
      newModalOpen={open}
      setNewModalOpen={setOpen}
      newModalForm={() => (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Título">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Fecha de reunión">
              <Input
                type="datetime-local"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
              />
            </Field>
          </div>

          <ArrayEditor
            title="Participantes"
            items={participants}
            onAdd={() => setParticipants([...participants, { name: "", email: "" }])}
            onRemove={(i) => setParticipants(participants.filter((_, idx) => idx !== i))}
            render={(p, i) => (
              <div className="grid gap-2 sm:grid-cols-2">
                <Input
                  placeholder="Nombre"
                  value={p.name}
                  onChange={(e) => {
                    const next = [...participants];
                    next[i] = { ...p, name: e.target.value };
                    setParticipants(next);
                  }}
                />
                <Input
                  placeholder="email@empresa.com"
                  value={p.email ?? ""}
                  onChange={(e) => {
                    const next = [...participants];
                    next[i] = { ...p, email: e.target.value };
                    setParticipants(next);
                  }}
                />
              </div>
            )}
          />

          <ArrayEditor
            title="Temas tratados"
            items={topics}
            onAdd={() => setTopics([...topics, { title: "", notes: "" }])}
            onRemove={(i) => setTopics(topics.filter((_, idx) => idx !== i))}
            render={(t, i) => (
              <div className="space-y-1.5">
                <Input
                  placeholder="Tema"
                  value={t.title}
                  onChange={(e) => {
                    const next = [...topics];
                    next[i] = { ...t, title: e.target.value };
                    setTopics(next);
                  }}
                />
                <Textarea
                  rows={2}
                  placeholder="Notas"
                  value={t.notes}
                  onChange={(e) => {
                    const next = [...topics];
                    next[i] = { ...t, notes: e.target.value };
                    setTopics(next);
                  }}
                />
              </div>
            )}
          />

          <ArrayEditor
            title="Acuerdos"
            items={agreements}
            onAdd={() => setAgreements([...agreements, { description: "", due_date: "" }])}
            onRemove={(i) => setAgreements(agreements.filter((_, idx) => idx !== i))}
            render={(a, i) => (
              <div className="grid gap-2 sm:grid-cols-[2fr_1fr]">
                <Input
                  placeholder="Descripción"
                  value={a.description}
                  onChange={(e) => {
                    const next = [...agreements];
                    next[i] = { ...a, description: e.target.value };
                    setAgreements(next);
                  }}
                />
                <Input
                  type="date"
                  value={a.due_date ?? ""}
                  onChange={(e) => {
                    const next = [...agreements];
                    next[i] = { ...a, due_date: e.target.value };
                    setAgreements(next);
                  }}
                />
              </div>
            )}
          />
        </div>
      )}
      newModalFooter={(close) => (
        <>
          <Button variant="secondary" onClick={close} disabled={submitting}>
            Cancelar
          </Button>
          <Button
            onClick={submit}
            loading={submitting}
            disabled={!title.trim() || !meetingDate}
          >
            Registrar
          </Button>
        </>
      )}
      columns={[
        {
          key: "eye",
          label: "",
          render: (r) => (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setPreview(r);
              }}
              aria-label={`Preview ${r.title}`}
              title="Vista rápida"
              className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
            >
              <Eye className="h-3.5 w-3.5" aria-hidden />
            </button>
          ),
        },
        {
          key: "title",
          label: "Minuta",
          render: (r) => (
            <div>
              <p className="font-medium">{r.title}</p>
              <p className="text-[11px] text-[var(--text-tertiary)]">
                {r.participants.length} participantes · {r.topics.length} temas ·{" "}
                {r.agreements.length} acuerdos
              </p>
            </div>
          ),
        },
        {
          key: "date",
          label: "Fecha",
          render: (r) => new Date(r.meeting_date).toLocaleDateString("es-MX"),
        },
        {
          key: "ai",
          label: "",
          render: (r) =>
            r.generated_by_ai ? <Badge variant="info">IA</Badge> : <span>—</span>,
        },
        {
          key: "export",
          label: "Exportar",
          render: (r) => <ExportMinuteButtons minuteId={r.id} />,
        },
      ]}
    />
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
              {
                label: "Fecha",
                value: new Date(preview.meeting_date).toLocaleDateString("es-MX"),
              },
              { label: "Participantes", value: preview.participants.length },
              { label: "Temas", value: preview.topics.length },
              { label: "Acuerdos", value: preview.agreements.length },
              {
                label: "Origen",
                value: preview.generated_by_ai ? "IA" : "Manual",
              },
            ]
          : []
      }
      description={
        preview
          ? preview.topics.map((t) => `• ${t.title}`).join("\n") || null
          : null
      }
    />
    </>
  );
}

function ArrayEditor<T>({
  title,
  items,
  onAdd,
  onRemove,
  render,
}: {
  title: string;
  items: T[];
  onAdd: () => void;
  onRemove: (i: number) => void;
  render: (item: T, index: number) => React.ReactNode;
}) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[12px] font-medium text-[var(--text-secondary)]">{title}</span>
        <Button size="sm" variant="ghost" onClick={onAdd}>
          <Plus className="h-3.5 w-3.5" aria-hidden /> Agregar
        </Button>
      </div>
      <div className="space-y-2">
        {items.map((it, i) => (
          <div key={i} className="flex items-start gap-2">
            <div className="min-w-0 flex-1">{render(it, i)}</div>
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="mt-1 inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
              aria-label={`Quitar ${title.toLowerCase()} ${i + 1}`}
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        ))}
        {items.length === 0 ? (
          <p className="text-[12px] text-[var(--text-tertiary)]">Sin elementos.</p>
        ) : null}
      </div>
    </div>
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

const EXPORT_FORMATS: Array<{ key: MinuteExportFormat; label: string }> = [
  { key: "pdf", label: "PDF" },
  { key: "docx", label: "DOCX" },
  { key: "md", label: "MD" },
  { key: "txt", label: "TXT" },
];

function ExportMinuteButtons({ minuteId }: { minuteId: string }) {
  const [busy, setBusy] = useState<MinuteExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(format: MinuteExportFormat) {
    setBusy(format);
    setError(null);
    try {
      await exportMinute(minuteId, format);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al exportar");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1">
      {EXPORT_FORMATS.map((f) => (
        <button
          key={f.key}
          type="button"
          onClick={() => void download(f.key)}
          disabled={busy !== null}
          className="inline-flex h-7 items-center gap-1 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[11px] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)] disabled:opacity-60"
          aria-label={`Descargar minuta en ${f.label}`}
        >
          {busy === f.key ? (
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--color-accent)]" />
          ) : (
            <Download className="h-3 w-3" aria-hidden />
          )}
          {f.label}
        </button>
      ))}
      {error ? (
        <span className="text-[10px] text-[var(--color-danger-fg)]">{error}</span>
      ) : null}
    </div>
  );
}
