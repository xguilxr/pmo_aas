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

import { MinuteRaidSuggestionsEditor } from "@/components/minute-raid-suggestions-editor";
import { MinuteSaveModal } from "@/components/minute-save-modal";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  EMPTY_RAID_BLOCK,
  cancelAIJob,
  generateMinute,
  type AIMinutePayload,
  type AIRaidBlock,
  type ManualMinuteData,
  type ManualSaveResult,
  type MinuteSourceType,
} from "@/lib/api/ai";
import {
  createMinute,
  getMinute,
  type MeetingMinute,
} from "@/lib/api/modules";
import { useAIJobPolling } from "@/lib/hooks/use-ai-job-polling";

type Attendee = { name: string; role?: string };
type ManualTopic = { title: string; bullets: string };
type ManualRaid = {
  type: "A" | "R" | "D" | "I";
  description: string;
  responsible: string;
  due_date: string;
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
  const [pendingSave, setPendingSave] = useState<null | "preview" | "manual">(null);
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
  const [result, setResult] = useState<AIMinutePayload | null>(null);
  const [savedMinuteId, setSavedMinuteId] = useState<string | null>(null);
  const [savedMinute, setSavedMinute] = useState<MeetingMinute | null>(null);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [savingPreview, setSavingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discardedRaid, setDiscardedRaid] = useState<Set<string>>(new Set());

  const toggleDiscardRaid = (key: string, next: boolean) => {
    setDiscardedRaid((prev) => {
      const out = new Set(prev);
      if (next) out.add(key);
      else out.delete(key);
      return out;
    });
  };

  const polling = useAIJobPolling({
    jobId,
    enabled: !!jobId,
    onSuccess: (job) => {
      const payload = (job.output ?? null) as (AIMinutePayload & { minute_id?: string | null }) | null;
      if (payload) {
        setResult(payload);
        setSavedMinuteId(payload.minute_id ?? null);
      }
      setModelUsed(job.model);
      if (payload?.minute_id) {
        getMinute(payload.minute_id)
          .then((m) => setSavedMinute(m))
          .catch(() => {});
      }
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
    setResult(null);
    setSavedMinuteId(null);
    setSavedMinute(null);
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
      setPendingSave("preview");
      setTitleModalOpen(true);
      return;
    }
    setDispatching(true);
    setError(null);
    setResult(null);
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

  // Guarda la preview (modos transcript/minute) tras IA.
  async function savePreview(titleOverride?: string) {
    if (!result) return;
    const effectiveTitle = (titleOverride ?? title).trim();
    if (!effectiveTitle) {
      setPendingSave("preview");
      setTitleModalOpen(true);
      return;
    }
    setSavingPreview(true);
    setError(null);
    try {
      const raidIn = result.raid ?? EMPTY_RAID_BLOCK;
      const persistKind = (
        kind: "risks" | "issues" | "lessons" | "changes",
        items: typeof raidIn.risks,
      ) =>
        items.map((it, idx) => {
          const base = {
            short_desc: (it.short_desc ?? "").trim(),
            suggested_owner_name: it.suggested_owner_name ?? null,
            suggested_priority: it.suggested_priority ?? null,
            raw_quote: it.raw_quote ?? null,
            status: "pending" as const,
            ticket_id: null,
            ticket_type: null,
          };
          if (discardedRaid.has(`${kind}:${idx}`)) {
            return { ...base, status: "discarded" as const };
          }
          return base;
        });
      const raidPersisted = {
        risks: persistKind("risks", raidIn.risks),
        issues: persistKind("issues", raidIn.issues),
        lessons: persistKind("lessons", raidIn.lessons),
        changes: persistKind("changes", raidIn.changes),
      };
      const created = await createMinute(id, {
        title: effectiveTitle,
        meeting_date: new Date().toISOString(),
        participants: result.participants ?? [],
        topics: result.topics ?? [],
        agreements: result.agreements ?? [],
        generated_by_ai: true,
        raid_suggestions: raidPersisted,
      });
      setSavedMinuteId(created.id);
      setSavedMinute(created);
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

            <ArrayEditor
              title="RAID (Acción / Riesgo / Decisión / Issue)"
              items={mRaid}
              onAdd={() =>
                setMRaid([...mRaid, { type: "A", description: "", responsible: "", due_date: "" }])
              }
              onRemove={(i) => setMRaid(mRaid.filter((_, idx) => idx !== i))}
              render={(r, i) => (
                <div className="grid gap-2 sm:grid-cols-[80px_1fr_1fr_140px]">
                  <Select
                    value={r.type}
                    onChange={(e) => {
                      const next = [...mRaid];
                      next[i] = { ...r, type: e.target.value as ManualRaid["type"] };
                      setMRaid(next);
                    }}
                  >
                    <option value="A">A</option>
                    <option value="R">R</option>
                    <option value="D">D</option>
                    <option value="I">I</option>
                  </Select>
                  <Input
                    placeholder="Descripción"
                    value={r.description}
                    onChange={(e) => {
                      const next = [...mRaid];
                      next[i] = { ...r, description: e.target.value };
                      setMRaid(next);
                    }}
                  />
                  <Input
                    placeholder="Responsable"
                    value={r.responsible}
                    onChange={(e) => {
                      const next = [...mRaid];
                      next[i] = { ...r, responsible: e.target.value };
                      setMRaid(next);
                    }}
                  />
                  <Input
                    type="date"
                    value={r.due_date}
                    onChange={(e) => {
                      const next = [...mRaid];
                      next[i] = { ...r, due_date: e.target.value };
                      setMRaid(next);
                    }}
                  />
                </div>
              )}
            />

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

      {/* Preview tras IA (modos transcript|minute) */}
      {result ? (
        <section className="space-y-4 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6">
          <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">Previsualización</h2>

          <MinuteSection title="Resumen">
            <p className="whitespace-pre-wrap text-[13px] text-[var(--text-primary)]">
              {result.summary || "—"}
            </p>
          </MinuteSection>

          <MinuteSection title="Participantes">
            {result.participants?.length ? (
              <ul className="flex flex-wrap gap-1.5">
                {result.participants.map((p, i) => (
                  <li key={i}>
                    <Badge>{p.name}</Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[13px] text-[var(--text-tertiary)]">—</p>
            )}
          </MinuteSection>

          <MinuteSection title="Temas">
            <ul className="space-y-2">
              {result.topics?.map((t, i) => (
                <li
                  key={i}
                  className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3"
                >
                  <p className="text-[13px] font-medium text-[var(--text-primary)]">{t.title}</p>
                  <p className="mt-1 whitespace-pre-wrap text-[12px] text-[var(--text-secondary)]">
                    {t.notes}
                  </p>
                </li>
              ))}
              {!result.topics?.length ? (
                <p className="text-[13px] text-[var(--text-tertiary)]">—</p>
              ) : null}
            </ul>
          </MinuteSection>

          {savedMinute ? (
            <MinuteRaidSuggestionsEditor
              minute={savedMinute}
              onMinuteChanged={setSavedMinute}
            />
          ) : (
            <RaidPreview
              raid={result.raid ?? EMPTY_RAID_BLOCK}
              discarded={discardedRaid}
              onToggle={toggleDiscardRaid}
            />
          )}

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
          ) : (
            <div className="flex items-center justify-between gap-2 pt-2">
              <p className="text-[11px] text-[var(--text-tertiary)]">
                {modelUsed ? (
                  <>
                    Modelo: <Badge>{modelUsed}</Badge>
                  </>
                ) : null}
              </p>
              <Button
                onClick={() => savePreview()}
                loading={savingPreview}
                disabled={generating}
              >
                Guardar Minuta
              </Button>
            </div>
          )}
        </section>
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
            if (pending === "preview") void handleGenerateAI(newTitle);
            else if (pending === "manual") void handleGenerateManual(newTitle);
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

const RAID_SECTION_META: Array<{
  key: keyof AIRaidBlock;
  label: string;
  emptyHint: string;
}> = [
  { key: "risks", label: "Riesgos", emptyHint: "Sin riesgos detectados." },
  { key: "issues", label: "Issues", emptyHint: "Sin issues detectados." },
  { key: "lessons", label: "Lecciones", emptyHint: "Sin lecciones detectadas." },
  { key: "changes", label: "Cambios", emptyHint: "Sin cambios detectados." },
];

function RaidPreview({
  raid,
  discarded,
  onToggle,
}: {
  raid: AIRaidBlock;
  discarded: Set<string>;
  onToggle: (key: string, next: boolean) => void;
}) {
  const total = raid.risks.length + raid.issues.length + raid.lessons.length + raid.changes.length;
  const kept = total - discarded.size;
  return (
    <section className="space-y-3 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 p-4">
      <header className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Sugerencias RAID detectadas
        </h3>
        <Badge variant={total === 0 ? "neutral" : "info"}>
          {kept} de {total} {total === 1 ? "item" : "items"} se crearán
        </Badge>
      </header>
      <p className="text-[11px] italic text-[var(--text-tertiary)]">
        Desmarca los items que no quieras crear como tickets reales al guardar.
      </p>
      <div className="grid gap-3 lg:grid-cols-2">
        {RAID_SECTION_META.map((meta) => {
          const items = raid[meta.key];
          return (
            <details
              key={meta.key}
              open={items.length > 0}
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-3"
            >
              <summary className="flex cursor-pointer items-center justify-between text-[12px] font-medium text-[var(--text-primary)]">
                <span>{meta.label}</span>
                <Badge variant={items.length === 0 ? "neutral" : "info"}>{items.length}</Badge>
              </summary>
              <div className="mt-2 space-y-2">
                {items.length === 0 ? (
                  <p className="text-[12px] italic text-[var(--text-tertiary)]">{meta.emptyHint}</p>
                ) : (
                  items.map((it, i) => {
                    const key = `${meta.key}:${i}`;
                    const isDiscarded = discarded.has(key);
                    return (
                      <label
                        key={i}
                        className={`flex cursor-pointer gap-2 rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-2.5 py-2 ${
                          isDiscarded
                            ? "bg-[var(--color-surface)] opacity-60"
                            : "bg-[var(--color-subtle)]"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={!isDiscarded}
                          onChange={(e) => onToggle(key, !e.target.checked)}
                          className="mt-0.5 h-4 w-4 shrink-0"
                        />
                        <div className="flex-1">
                          <p
                            className={`text-[12px] font-medium ${
                              isDiscarded
                                ? "text-[var(--text-tertiary)] line-through"
                                : "text-[var(--text-primary)]"
                            }`}
                          >
                            {it.short_desc}
                          </p>
                          {it.raw_quote ? (
                            <p className="mt-1 line-clamp-2 italic text-[11px] text-[var(--text-tertiary)]">
                              “{it.raw_quote}”
                            </p>
                          ) : null}
                        </div>
                      </label>
                    );
                  })
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}

function MinuteSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
        {title}
      </h3>
      {children}
    </section>
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
