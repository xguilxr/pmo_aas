"use client";

/**
 * US-142 — Generador unificado de minutas (reemplaza ai-minutes/new).
 *
 * 3 modos en la misma página, toggle al inicio:
 * - Transcript: textarea + uploader. IA estructura desde transcript de reunión.
 * - Minuta: textarea + uploader de minuta YA redactada. IA normaliza al modelo
 *   canónico (US-143 `source_type=minute`).
 * - Manual: form con las 6 secciones EP019. NO invoca IA — persiste directo
 *   (US-143 `source_type=manual`).
 *
 * Modal "Confirma título" antes de generar (ENH-104). Preview editable con
 * sugerencias RAID (US-108). Guardar → redirect a /minutes/[newId].
 */
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, FileText, MessageSquare, Plus, Sparkles, Trash2, Upload, Wand2, X } from "lucide-react";

import { MinuteSaveModal } from "@/components/minute-save-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  cancelAIJob,
  generateMinute,
  type AIMinutePayload,
  type ManualMinuteData,
  type ManualSaveResult,
  type MinuteSourceType,
} from "@/lib/api/ai";
import {
  createMinute,
} from "@/lib/api/modules";
import { useAIJobPolling } from "@/lib/hooks/use-ai-job-polling";

type Attendee = { name: string; role?: string; area?: string };
type ManualTopic = { title: string; bullets: string };
type ManualRaid = {
  type: "A" | "R" | "D" | "I";
  description: string;
  responsible: string;
  due_date: string;
};

// BUG-063: mapping entre la letra A/R/D/I y el bucket persistible.
const TYPE_LETTER_TO_BUCKET: Record<ManualRaid["type"], "actions" | "risks" | "decisions" | "issues"> = {
  A: "actions",
  R: "risks",
  D: "decisions",
  I: "issues",
};

export default function NewMinutePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  // US-142: 3 modos en lugar de upload|paste.
  const [mode, setMode] = useState<MinuteSourceType>("transcript");

  // Estado compartido (transcript + minuta — son textos crudos).
  const [title, setTitle] = useState("");
  const [titleTouched, setTitleTouched] = useState(false);
  const [titleModalOpen, setTitleModalOpen] = useState(false);
  const [pendingSave, setPendingSave] = useState<null | "generate" | "manual" | "save">(null);
  const [language, setLanguage] = useState<"" | "es" | "en">("");
  const [textInput, setTextInput] = useState("");
  const [textSource, setTextSource] = useState<"upload" | "paste">("paste");

  // Estado modo manual (form con 6 secciones).
  const [mHeaderDate, setMHeaderDate] = useState("");
  const [mAttendees, setMAttendees] = useState<Attendee[]>([]);
  const [mSummary, setMSummary] = useState("");
  const [mTopics, setMTopics] = useState<ManualTopic[]>([]);
  const [mRaid, setMRaid] = useState<ManualRaid[]>([]);
  const [mFreeNotes, setMFreeNotes] = useState("");

  // Flujo IA (modos transcript / minute).
  const [dispatching, setDispatching] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [aiPayload, setAiPayload] = useState<AIMinutePayload | null>(null);
  const [savedMinuteId, setSavedMinuteId] = useState<string | null>(null);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [savingPreview, setSavingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const polling = useAIJobPolling({
    jobId,
    enabled: !!jobId,
    onSuccess: (job) => {
      const payload = (job.output ?? null) as (AIMinutePayload & { minute_id?: string | null }) | null;
      if (!payload) return;
      setAiPayload(payload);
      setModelUsed(job.model);
      // BUG-063: hidratar el form editable con el output IA para que el
      // PM pueda editar antes de guardar. Reusa los mismos campos que el
      // modo manual; el botón "Guardar Minuta" persiste el estado actual
      // del form (no el `aiPayload` original).
      if (payload.summary) setMSummary(payload.summary);
      if (payload.header && typeof payload.header === "object") {
        const h = payload.header as { date?: string };
        if (h.date && !mHeaderDate) setMHeaderDate(String(h.date));
      }
      if (Array.isArray(payload.participants) && payload.participants.length) {
        setMAttendees(
          payload.participants.map((p) => ({
            name: p.name ?? "",
            role: p.role ?? "",
            area: p.area ?? "",
          })),
        );
      }
      if (Array.isArray(payload.topics) && payload.topics.length) {
        setMTopics(
          payload.topics.map((t) => {
            const bullets = Array.isArray(t.bullets)
              ? t.bullets.join("\n")
              : (t.notes ?? "");
            return { title: t.title ?? "", bullets };
          }),
        );
      }
      const raid = payload.raid_suggestions ?? payload.raid;
      if (raid) {
        const flat: ManualRaid[] = [];
        const pushFromBucket = (kind: ManualRaid["type"], items?: { short_desc?: string; suggested_owner_name?: string | null; suggested_due_date?: string | null }[]) => {
          if (!Array.isArray(items)) return;
          for (const it of items) {
            const desc = (it.short_desc ?? "").trim();
            if (!desc) continue;
            flat.push({
              type: kind,
              description: desc,
              responsible: it.suggested_owner_name ?? "",
              due_date: it.suggested_due_date ?? "",
            });
          }
        };
        pushFromBucket("A", raid.actions);
        pushFromBucket("R", raid.risks);
        pushFromBucket("D", raid.decisions);
        pushFromBucket("I", raid.issues);
        if (flat.length) setMRaid(flat);
      }
      if (payload.free_notes) setMFreeNotes(payload.free_notes);
      if (payload.minute_id) setSavedMinuteId(payload.minute_id);
    },
    onError: (job) => {
      const raw = job.error || "La generación falló";
      const rateLimited = raw.startsWith("AI_RATE_LIMITED:");
      setError(rateLimited ? raw.replace("AI_RATE_LIMITED:", "").trim() : raw);
    },
  });

  async function onFile(file: File) {
    if (file.size > 5 * 1024 * 1024) {
      setError("El archivo supera 5 MB");
      return;
    }
    const text = await file.text();
    setTextInput(text);
    if (!titleTouched) {
      const stem = file.name.replace(/\.[^.]+$/, "");
      setTitle(stem);
    }
  }

  async function handleCancel() {
    const j = jobId;
    setJobId(null);
    if (j) {
      try {
        await cancelAIJob(j);
      } catch {}
    }
    setDispatching(false);
    setAiPayload(null);
    setSavedMinuteId(null);
    setModelUsed(null);
    setError(null);
  }

  // Genera con IA (transcript | minute).
  async function handleGenerateAI(titleOverride?: string) {
    const effectiveTitle = (titleOverride ?? title).trim();
    if (textInput.trim().length < 20) {
      setError("El texto es demasiado corto");
      return;
    }
    if (!effectiveTitle) {
      setPendingSave("generate");
      setTitleModalOpen(true);
      return;
    }
    setDispatching(true);
    setError(null);
    setAiPayload(null);
    setSavedMinuteId(null);
    setModelUsed(null);
    try {
      const res = await generateMinute({
        project_id: id,
        source_type: mode, // transcript | minute
        transcript: textInput,
        language: language || undefined,
        save_as_minute: false, // preview primero; guardado explícito después
        title: effectiveTitle,
      });
      if ("job_id" in res) setJobId(res.job_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo despachar el job");
    } finally {
      setDispatching(false);
    }
  }

  // Modo manual: persiste directo, redirect a detail.
  async function handleGenerateManual(titleOverride?: string) {
    const effectiveTitle = (titleOverride ?? title).trim();
    if (!effectiveTitle) {
      setPendingSave("manual");
      setTitleModalOpen(true);
      return;
    }
    setDispatching(true);
    setError(null);
    try {
      const structured: ManualMinuteData = {
        header: {
          title: effectiveTitle,
          date: mHeaderDate || null,
        },
        participants: { attendees: mAttendees.filter((a) => a.name.trim()) },
        summary: mSummary,
        topics: mTopics
          .filter((t) => t.title.trim())
          .map((t) => ({
            title: t.title,
            bullets: t.bullets
              .split(/\r?\n/)
              .map((b) => b.trim())
              .filter(Boolean),
          })),
        agreements: mRaid
          .filter((r) => r.description.trim())
          .map((r) => ({
            description: `[${r.type}] ${r.description}`,
            owner: r.responsible || undefined,
            due_date: r.due_date || undefined,
          })),
        free_notes: mFreeNotes || null,
      };
      const res = (await generateMinute({
        project_id: id,
        source_type: "manual",
        structured_data: structured,
        title: effectiveTitle,
      })) as ManualSaveResult;
      router.push(`/pmo/projects/${id}/minutes/${res.minute_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la minuta");
    } finally {
      setDispatching(false);
    }
  }

  // BUG-063: guarda la minuta desde el form editable (post-IA o manual).
  // Toma el estado actual del form — el PM puede haber editado cualquier
  // sección antes de pulsar "Guardar".
  async function savePreview(titleOverride?: string) {
    const effectiveTitle = (titleOverride ?? title).trim();
    if (!effectiveTitle) {
      setPendingSave("save");
      setTitleModalOpen(true);
      return;
    }
    setSavingPreview(true);
    setError(null);
    try {
      type SuggestionShape = {
        short_desc: string;
        suggested_owner_name: string | null;
        suggested_due_date: string | null;
        suggested_priority: number | null;
        raw_quote: string | null;
        status: "pending" | "approved" | "discarded";
        ticket_id: string | null;
        ticket_type: null;
      };
      const raidPersisted: Record<"actions" | "risks" | "decisions" | "issues", SuggestionShape[]> = {
        actions: [], risks: [], decisions: [], issues: [],
      };
      for (const r of mRaid) {
        const desc = r.description.trim();
        if (!desc) continue;
        const bucket = TYPE_LETTER_TO_BUCKET[r.type];
        raidPersisted[bucket].push({
          short_desc: desc,
          suggested_owner_name: r.responsible || null,
          suggested_due_date: r.due_date || null,
          suggested_priority: null,
          raw_quote: null,
          status: "pending",
          ticket_id: null,
          ticket_type: null,
        });
      }
      // BUG-068: si la IA devuelve `header.date` en formato no-ISO, el
      // backend ya lo normaliza, pero el PM también puede haber pegado
      // basura en el input. Defensa: intentamos construir el ISO; si
      // falla caemos a "hoy" en lugar de explotar con RangeError
      // (que termina mostrando el genérico "No se pudo guardar la
      // minuta" porque el throw no es un ApiError).
      let meetingDateIso: string;
      try {
        const candidate = mHeaderDate
          ? new Date(`${mHeaderDate}T12:00:00`)
          : new Date();
        if (Number.isNaN(candidate.getTime())) throw new Error("invalid date");
        meetingDateIso = candidate.toISOString();
      } catch {
        meetingDateIso = new Date().toISOString();
      }
      const created = await createMinute(id, {
        title: effectiveTitle,
        meeting_date: meetingDateIso,
        summary: mSummary || null,
        free_notes: mFreeNotes || null,
        participants: mAttendees
          .filter((a) => a.name.trim())
          .map((a) => ({
            name: a.name.trim(),
            role: a.role || null,
            area: a.area || null,
          })),
        topics: mTopics
          .filter((t) => t.title.trim())
          .map((t) => ({
            title: t.title.trim(),
            bullets: t.bullets
              .split(/\r?\n/)
              .map((b) => b.trim())
              .filter(Boolean),
          })),
        agreements: [],
        generated_by_ai: !!aiPayload,
        raid_suggestions: raidPersisted,
      });
      setSavedMinuteId(created.id);
      // Redirect al detalle para que el PM continúe trabajando ahí.
      router.push(`/pmo/projects/${id}/minutes/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la minuta");
    } finally {
      setSavingPreview(false);
    }
  }

  const generating = dispatching || polling.isPolling;
  const statusLabel =
    polling.status === "queued"
      ? "En cola..."
      : polling.status === "running"
      ? mode === "minute"
        ? "Normalizando minuta..."
        : "Generando minuta..."
      : null;

  const modeMeta: Record<MinuteSourceType, { label: string; icon: React.ReactNode; hint: string }> = {
    transcript: {
      label: "Transcript",
      icon: <FileText className="h-4 w-4" aria-hidden />,
      hint: "Sube o pega el transcript de la reunión. IA estructura la minuta.",
    },
    minute: {
      label: "Minuta",
      icon: <MessageSquare className="h-4 w-4" aria-hidden />,
      hint: "Sube o pega una minuta ya redactada. IA la normaliza al modelo canónico preservando contenido.",
    },
    manual: {
      label: "Manual",
      icon: <Wand2 className="h-4 w-4" aria-hidden />,
      hint: "Form vacío con las 6 secciones. Sin IA — persiste directo al guardar.",
    },
  };

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/pmo/projects/${id}`} className="hover:underline">
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/pmo/projects/${id}/minutes`} className="hover:underline">
            Minutas
          </Link>
          <span className="mx-1">/</span>
          <span>Generar Minuta</span>
        </nav>
        <Link
          href={`/pmo/projects/${id}/minutes`}
          className="mt-2 inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Volver
        </Link>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          <Sparkles className="h-6 w-6 text-[var(--color-accent)]" aria-hidden />
          Generar Minuta
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          {modeMeta[mode].hint}
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {polling.error ? <Banner variant="danger">{polling.error}</Banner> : null}
      {statusLabel ? (
        <Banner variant="info">
          <div className="flex items-center justify-between gap-3">
            <span>
              {statusLabel} (job {jobId?.slice(0, 8)}…)
            </span>
            <Button size="sm" variant="secondary" onClick={handleCancel}>
              <X className="h-3.5 w-3.5" aria-hidden /> Cancelar
            </Button>
          </div>
        </Banner>
      ) : null}

      {/* US-142: toggle 3 modos */}
      <div
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-0.5 text-[12px]"
        role="tablist"
        aria-label="Modo de generación"
      >
        {(["transcript", "minute", "manual"] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            disabled={generating}
            className={`inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] px-3 py-1.5 ${
              mode === m
                ? "bg-[var(--color-surface)] font-medium shadow-sm"
                : "text-[var(--text-secondary)]"
            }`}
          >
            {modeMeta[m].icon}
            {modeMeta[m].label}
          </button>
        ))}
      </div>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6">
        <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
          <Field label="Título">
            <Input
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setTitleTouched(true);
              }}
              placeholder="Ej.: Reunión semanal de avance"
            />
          </Field>
          {mode !== "manual" ? (
            <Field label="Idioma">
              <Select
                value={language}
                onChange={(e) => setLanguage(e.target.value as "" | "es" | "en")}
              >
                <option value="">Autodetectar</option>
                <option value="es">Español</option>
                <option value="en">English</option>
              </Select>
            </Field>
          ) : (
            <Field label="Fecha de reunión">
              <Input
                type="date"
                value={mHeaderDate}
                onChange={(e) => setMHeaderDate(e.target.value)}
              />
            </Field>
          )}
        </div>

        {/* Modos IA — Transcript / Minuta */}
        {mode !== "manual" ? (
          <div className="mt-4 space-y-3">
            <div
              className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-0.5 text-[12px]"
              role="tablist"
              aria-label="Fuente del texto"
            >
              <button
                type="button"
                role="tab"
                aria-selected={textSource === "paste"}
                onClick={() => setTextSource("paste")}
                className={`rounded-[var(--radius-sm)] px-3 py-1.5 ${
                  textSource === "paste"
                    ? "bg-[var(--color-surface)] font-medium shadow-sm"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Pegar texto
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={textSource === "upload"}
                onClick={() => setTextSource("upload")}
                className={`rounded-[var(--radius-sm)] px-3 py-1.5 ${
                  textSource === "upload"
                    ? "bg-[var(--color-surface)] font-medium shadow-sm"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                Subir archivo
              </button>
            </div>

            {textSource === "paste" ? (
              <Field
                label={mode === "minute" ? "Pega aquí la minuta ya redactada" : "Pega aquí el transcript completo"}
              >
                <Textarea
                  rows={16}
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder={
                    mode === "minute"
                      ? "Pega la minuta original (texto plano, markdown, o extraído de DOCX/PDF). La IA preservará lo que pueda."
                      : "Pega aquí la transcripción de la reunión. Sin límite duro de tamaño; aviso al pasar 50,000 caracteres."
                  }
                />
                <div className="mt-1 flex items-center justify-between text-[11px] text-[var(--text-tertiary)]">
                  <span>{textInput.length.toLocaleString("es-MX")} caracteres</span>
                  {textInput.length > 50000 ? (
                    <span className="text-[var(--color-warning-fg)]">⚠ Texto muy largo: tardará.</span>
                  ) : null}
                </div>
              </Field>
            ) : (
              <Field label={mode === "minute" ? "Archivo de minuta" : "Archivo de transcript"}>
                <label className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] px-3 py-3 hover:bg-[var(--color-subtle)]">
                  <Upload className="h-4 w-4 text-[var(--text-tertiary)]" aria-hidden />
                  <input
                    type="file"
                    accept=".txt,.srt,.md,.vtt"
                    className="hidden"
                    onChange={(e) => e.target.files && onFile(e.target.files[0])}
                  />
                  <span className="text-[12px] text-[var(--text-secondary)]">
                    {textInput
                      ? `Archivo cargado · ${textInput.length.toLocaleString("es-MX")} caracteres. Click para reemplazar.`
                      : "Sube .txt, .srt, .md o .vtt (máx 5 MB)"}
                  </span>
                </label>
              </Field>
            )}

            <div className="flex justify-end pt-2">
              <Button
                onClick={() => handleGenerateAI()}
                loading={generating}
                disabled={textInput.trim().length < 20}
              >
                <Wand2 className="h-4 w-4" aria-hidden /> Generar Minuta
              </Button>
            </div>
          </div>
        ) : (
          /* Modo Manual — form con 6 secciones */
          <div className="mt-4 space-y-4">
            <Field label="Resumen">
              <Textarea
                rows={3}
                value={mSummary}
                onChange={(e) => setMSummary(e.target.value)}
                placeholder="2-3 oraciones que sintetizan el objetivo de la sesión."
              />
            </Field>

            <ArrayEditor
              title="Participantes"
              items={mAttendees}
              onAdd={() => setMAttendees([...mAttendees, { name: "", role: "" }])}
              onRemove={(i) => setMAttendees(mAttendees.filter((_, idx) => idx !== i))}
              render={(p, i) => (
                <div className="grid gap-2 sm:grid-cols-2">
                  <Input
                    placeholder="Nombre"
                    value={p.name}
                    onChange={(e) => {
                      const next = [...mAttendees];
                      next[i] = { ...p, name: e.target.value };
                      setMAttendees(next);
                    }}
                  />
                  <Input
                    placeholder="Rol (opcional)"
                    value={p.role ?? ""}
                    onChange={(e) => {
                      const next = [...mAttendees];
                      next[i] = { ...p, role: e.target.value };
                      setMAttendees(next);
                    }}
                  />
                </div>
              )}
            />

            <ArrayEditor
              title="Temas tratados"
              items={mTopics}
              onAdd={() => setMTopics([...mTopics, { title: "", bullets: "" }])}
              onRemove={(i) => setMTopics(mTopics.filter((_, idx) => idx !== i))}
              render={(t, i) => (
                <div className="space-y-1.5">
                  <Input
                    placeholder="Título del tema"
                    value={t.title}
                    onChange={(e) => {
                      const next = [...mTopics];
                      next[i] = { ...t, title: e.target.value };
                      setMTopics(next);
                    }}
                  />
                  <Textarea
                    rows={3}
                    placeholder="Bullets (uno por línea)"
                    value={t.bullets}
                    onChange={(e) => {
                      const next = [...mTopics];
                      next[i] = { ...t, bullets: e.target.value };
                      setMTopics(next);
                    }}
                  />
                </div>
              )}
            />

            <RaidPanels items={mRaid} setItems={setMRaid} />

            <Field label="Notas libres">
              <Textarea
                rows={3}
                value={mFreeNotes}
                onChange={(e) => setMFreeNotes(e.target.value)}
                placeholder="Cualquier nota que no encaje en las otras secciones."
              />
            </Field>

            <div className="flex justify-end pt-2">
              <Button
                onClick={() => handleGenerateManual()}
                loading={dispatching}
                disabled={
                  !title.trim() && mAttendees.length === 0 && mTopics.length === 0 && !mSummary.trim()
                }
              >
                Guardar Minuta Manual
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* BUG-063: preview editable post-IA — reusa el form del modo manual
          con los datos pre-cargados. El PM puede ajustar cualquier
          sección antes de pulsar "Guardar Minuta". */}
      {aiPayload && !savedMinuteId ? (
        <section className="space-y-4 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6">
          <header className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">
                Previsualización (editable)
              </h2>
              <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                Ajusta cualquier sección antes de guardar. La IA pre-cargó los campos basándose en el {mode === "minute" ? "texto de la minuta" : "transcript"}.
              </p>
            </div>
            {modelUsed ? (
              <Badge>Modelo: {modelUsed}</Badge>
            ) : null}
          </header>

          <Field label="Resumen">
            <Textarea
              rows={3}
              value={mSummary}
              onChange={(e) => setMSummary(e.target.value)}
              placeholder="2-3 oraciones que sintetizan el objetivo de la sesión."
            />
          </Field>

          <ArrayEditor
            title="Participantes"
            items={mAttendees}
            onAdd={() => setMAttendees([...mAttendees, { name: "", role: "", area: "" }])}
            onRemove={(i) => setMAttendees(mAttendees.filter((_, idx) => idx !== i))}
            render={(p, i) => (
              <div className="grid gap-2 sm:grid-cols-3">
                <Input
                  placeholder="Nombre"
                  value={p.name}
                  onChange={(e) => {
                    const next = [...mAttendees];
                    next[i] = { ...p, name: e.target.value };
                    setMAttendees(next);
                  }}
                />
                <Input
                  placeholder="Rol"
                  value={p.role ?? ""}
                  onChange={(e) => {
                    const next = [...mAttendees];
                    next[i] = { ...p, role: e.target.value };
                    setMAttendees(next);
                  }}
                />
                <Input
                  placeholder="Área"
                  value={p.area ?? ""}
                  onChange={(e) => {
                    const next = [...mAttendees];
                    next[i] = { ...p, area: e.target.value };
                    setMAttendees(next);
                  }}
                />
              </div>
            )}
          />

          <ArrayEditor
            title="Temas tratados"
            items={mTopics}
            onAdd={() => setMTopics([...mTopics, { title: "", bullets: "" }])}
            onRemove={(i) => setMTopics(mTopics.filter((_, idx) => idx !== i))}
            render={(t, i) => (
              <div className="space-y-1.5">
                <Input
                  placeholder="Título del tema"
                  value={t.title}
                  onChange={(e) => {
                    const next = [...mTopics];
                    next[i] = { ...t, title: e.target.value };
                    setMTopics(next);
                  }}
                />
                <Textarea
                  rows={Math.min(8, Math.max(3, t.bullets.split(/\r?\n/).length))}
                  placeholder="Bullets factuales (uno por línea)"
                  value={t.bullets}
                  onChange={(e) => {
                    const next = [...mTopics];
                    next[i] = { ...t, bullets: e.target.value };
                    setMTopics(next);
                  }}
                />
              </div>
            )}
          />

          <RaidPanels items={mRaid} setItems={setMRaid} />

          <Field label="Notas libres">
            <Textarea
              rows={3}
              value={mFreeNotes}
              onChange={(e) => setMFreeNotes(e.target.value)}
              placeholder="Próximos pasos calendarizados u otras notas que no encajan en RAID."
            />
          </Field>

          <div className="flex items-center justify-between gap-2 pt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCancel}
            >
              Descartar previsualización
            </Button>
            <Button
              onClick={() => savePreview()}
              loading={savingPreview}
              disabled={generating}
            >
              Guardar Minuta
            </Button>
          </div>
        </section>
      ) : null}

      {savedMinuteId ? (
        <Banner variant="success">
          Minuta guardada.{" "}
          <Link
            className="underline"
            href={`/pmo/projects/${id}/minutes/${savedMinuteId}`}
          >
            Ver minuta
          </Link>
        </Banner>
      ) : null}

      <MinuteSaveModal
        open={titleModalOpen}
        initial={title}
        onConfirm={(newTitle) => {
          setTitle(newTitle);
          setTitleTouched(true);
          setTitleModalOpen(false);
          const pending = pendingSave;
          setPendingSave(null);
          queueMicrotask(() => {
            if (pending === "generate") void handleGenerateAI(newTitle);
            else if (pending === "manual") void handleGenerateManual(newTitle);
            else if (pending === "save") void savePreview(newTitle);
          });
        }}
        onCancel={() => {
          setTitleModalOpen(false);
          setPendingSave(null);
        }}
      />
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}

// BUG-063 — UX feedback owner: la minuta no es ARDI ordenada (eso es
// para reportes). El estado interno es flat `ManualRaid[]` (orden libre,
// se llena conforme la IA o el PM va detectando items), pero la UX
// muestra **4 paneles dedicados** filtrando por tipo. El owner edita
// cada bucket como una mini-tabla, agrega items con botón "+ Agregar
// [tipo]" en el panel respectivo. Internamente todo sigue siendo un
// solo array; al guardar, agrupamos en `raid_suggestions` buckets.
const RAID_PANEL_META: Array<{ type: ManualRaid["type"]; label: string; hint: string }> = [
  { type: "A", label: "Acciones", hint: "Compromisos accionables con responsable y fecha." },
  { type: "R", label: "Riesgos", hint: "Preocupaciones, posibles retrasos, dependencias." },
  { type: "D", label: "Decisiones", hint: "Acuerdos cerrados o pendientes de definir." },
  { type: "I", label: "Issues", hint: "Problemas abiertos o pendientes de claridad." },
];

function RaidPanels({
  items,
  setItems,
}: {
  items: ManualRaid[];
  setItems: (next: ManualRaid[]) => void;
}) {
  const updateAt = (globalIdx: number, patch: Partial<ManualRaid>) => {
    const next = [...items];
    next[globalIdx] = { ...next[globalIdx], ...patch };
    setItems(next);
  };
  const removeAt = (globalIdx: number) => {
    setItems(items.filter((_, i) => i !== globalIdx));
  };
  const addOfType = (type: ManualRaid["type"]) => {
    setItems([...items, { type, description: "", responsible: "", due_date: "" }]);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium text-[var(--text-secondary)]">
          RAID — Acciones / Riesgos / Decisiones / Issues
        </span>
        <span className="text-[11px] text-[var(--text-tertiary)]">
          {items.length} item{items.length === 1 ? "" : "s"} en total
        </span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {RAID_PANEL_META.map((meta) => {
          const indexed = items
            .map((r, idx) => ({ r, idx }))
            .filter((x) => x.r.type === meta.type);
          return (
            <div
              key={meta.type}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 p-3"
            >
              <div className="mb-2 flex items-center justify-between">
                <div>
                  <p className="text-[12px] font-semibold text-[var(--text-primary)]">
                    {meta.type} · {meta.label}
                    <span className="ml-1.5 text-[11px] font-normal text-[var(--text-tertiary)]">
                      ({indexed.length})
                    </span>
                  </p>
                  <p className="text-[10.5px] text-[var(--text-tertiary)]">{meta.hint}</p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => addOfType(meta.type)}>
                  <Plus className="h-3.5 w-3.5" aria-hidden /> Agregar
                </Button>
              </div>
              <div className="space-y-2">
                {indexed.length === 0 ? (
                  <p className="text-[11px] italic text-[var(--text-tertiary)]">
                    Sin {meta.label.toLowerCase()} aún.
                  </p>
                ) : (
                  indexed.map(({ r, idx }) => (
                    <div
                      key={idx}
                      className="space-y-1.5 rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-2"
                    >
                      <div className="flex items-start gap-1.5">
                        <Textarea
                          rows={Math.max(2, Math.ceil(r.description.length / 60))}
                          placeholder="Descripción"
                          value={r.description}
                          onChange={(e) => updateAt(idx, { description: e.target.value })}
                          className="text-[12px]"
                        />
                        <button
                          type="button"
                          onClick={() => removeAt(idx)}
                          aria-label="Quitar"
                          className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-danger-fg)]"
                        >
                          <Trash2 className="h-3.5 w-3.5" aria-hidden />
                        </button>
                      </div>
                      <div className="grid gap-1.5 sm:grid-cols-2">
                        <Input
                          placeholder="Responsable"
                          value={r.responsible}
                          onChange={(e) => updateAt(idx, { responsible: e.target.value })}
                          className="text-[12px]"
                        />
                        <Input
                          placeholder="Fecha (ej. 25 mar / Inmediato)"
                          value={r.due_date}
                          onChange={(e) => updateAt(idx, { due_date: e.target.value })}
                          className="text-[12px]"
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
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
