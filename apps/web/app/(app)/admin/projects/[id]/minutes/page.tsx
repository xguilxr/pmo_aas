"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { MessageSquare, Plus, Sparkles, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  createMinute,
  listMinutes,
  type MeetingMinute,
  type MinuteAgreement,
  type MinuteParticipant,
  type MinuteTopic,
} from "@/lib/api/modules";

export default function MinutesPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<MeetingMinute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    <ModuleShell<MeetingMinute>
      projectId={id}
      title="Minutas"
      subtitle="Minutas de reunión con temas, participantes y acuerdos."
      icon={<MessageSquare className="h-5 w-5" aria-hidden />}
      records={rows}
      loading={loading}
      error={error}
      headerExtras={
        <Link href={`/admin/projects/${id}/ai-minutes/new`}>
          <Button variant="secondary">
            <Sparkles className="h-4 w-4" aria-hidden /> Generar con IA
          </Button>
        </Link>
      }
      newButtonLabel="Nueva minuta"
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
      ]}
    />
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
