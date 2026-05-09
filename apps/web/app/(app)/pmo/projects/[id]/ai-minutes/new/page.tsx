"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Sparkles, Wand2, X } from "lucide-react";

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
} from "@/lib/api/ai";
import {
  createMinute,
  getMinute,
  type MeetingMinute,
} from "@/lib/api/modules";
import { MinuteRaidSuggestionsEditor } from "@/components/minute-raid-suggestions-editor";
import { useAIJobPolling } from "@/lib/hooks/use-ai-job-polling";

export default function NewAIMinutePage() {
  const { id } = useParams<{ id: string }>();
  const [title, setTitle] = useState("Minuta (IA)");
  const [language, setLanguage] = useState<"" | "es" | "en">("");
  const [transcript, setTranscript] = useState("");
  const [dispatching, setDispatching] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<AIMinutePayload | null>(null);
  const [savedMinuteId, setSavedMinuteId] = useState<string | null>(null);
  const [savedMinute, setSavedMinute] = useState<MeetingMinute | null>(null);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [savingPreview, setSavingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      // US-108: si la minuta se guardó, traemos el objeto persistido
      // (incluye `raid_suggestions`) para alimentar el editor in-place.
      // Antes redirigíamos directo a /minutes; ahora dejamos al PM
      // revisar/aprobar las sugerencias antes de salir.
      if (payload?.minute_id) {
        getMinute(payload.minute_id)
          .then((m) => setSavedMinute(m))
          .catch(() => {
            /* no-fatal: queda el read-only del result */
          });
      }
    },
    onError: (job) => {
      // BUG-061: el worker codifica rate-limit como `AI_RATE_LIMITED: ...`.
      // Mostramos solo la parte legible para el usuario.
      const raw = job.error || "La generación falló";
      const rateLimited = raw.startsWith("AI_RATE_LIMITED:");
      setError(
        rateLimited
          ? raw.replace("AI_RATE_LIMITED:", "").trim()
          : raw,
      );
    },
  });

  async function savePreview() {
    if (!result) return;
    setSavingPreview(true);
    setError(null);
    try {
      // BUG-058: mapear el output crudo del LLM al shape persistible de
      // `raid_suggestions` (cada item con status="pending"). Sin esto,
      // la preview mostraba items pero el detalle de la minuta los
      // perdía al guardar.
      const raidIn = result.raid ?? EMPTY_RAID_BLOCK;
      const raidPersisted = {
        risks: raidIn.risks.map(toPersistedRaid),
        issues: raidIn.issues.map(toPersistedRaid),
        lessons: raidIn.lessons.map(toPersistedRaid),
        changes: raidIn.changes.map(toPersistedRaid),
      };
      const created = await createMinute(id, {
        title: title.trim() || "Minuta (IA)",
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

  function toPersistedRaid(it: {
    short_desc: string;
    suggested_owner_name?: string | null;
    suggested_priority?: number | null;
    raw_quote?: string | null;
  }) {
    return {
      short_desc: (it.short_desc ?? "").trim(),
      suggested_owner_name: it.suggested_owner_name ?? null,
      suggested_priority: it.suggested_priority ?? null,
      raw_quote: it.raw_quote ?? null,
      status: "pending" as const,
      ticket_id: null,
      ticket_type: null,
    };
  }

  async function onFile(file: File) {
    if (file.size > 5 * 1024 * 1024) {
      setError("El archivo supera 5 MB");
      return;
    }
    const text = await file.text();
    setTranscript(text);
  }

  // BUG-055: cancela el job activo y resetea al estado pre-generación.
  // El backend marca el AIJob como `cancelled` y el worker omite la
  // persistencia al detectar el flag (CA4: sin minutas huérfanas).
  async function handleCancel() {
    const id_to_cancel = jobId;
    setJobId(null); // detiene el polling localmente (CA2)
    if (id_to_cancel) {
      try {
        await cancelAIJob(id_to_cancel);
      } catch {
        /* el worker queda con el flag o termina solo; UX no se bloquea */
      }
    }
    setDispatching(false);
    setResult(null);
    setSavedMinuteId(null);
    setSavedMinute(null);
    setModelUsed(null);
    setError(null);
  }

  async function handleGenerate(save: boolean) {
    if (transcript.trim().length < 20) {
      setError("La transcripción es demasiado corta");
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
        transcript,
        language: language || undefined,
        save_as_minute: save,
        title: title.trim() || "Minuta (IA)",
      });
      setJobId(res.job_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo despachar el job");
    } finally {
      setDispatching(false);
    }
  }

  const generating = dispatching || polling.isPolling;
  const statusLabel =
    polling.status === "queued"
      ? "En cola..."
      : polling.status === "running"
      ? "Generando minuta..."
      : null;

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
          <span>Generar con IA</span>
        </nav>
        {/* BUG-055 CA3: ← Volver en cabecera, navega a la lista de
            minutas sin guardar nada. */}
        <Link
          href={`/pmo/projects/${id}/minutes`}
          className="mt-2 inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Volver
        </Link>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          <Sparkles className="h-6 w-6 text-[var(--color-accent)]" aria-hidden />
          Minuta con IA
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Pega la transcripción (o sube un .txt). El worker procesa con el
          proveedor IA del tenant (Groq plataforma o BYO). Max 5 MB.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {polling.error ? <Banner variant="danger">{polling.error}</Banner> : null}

      {/* BUG-055 CA1+CA2: banner con botón Cancelar visible mientras
          la generación está corriendo. */}
      {statusLabel ? (
        <Banner variant="info">
          <div className="flex items-center justify-between gap-3">
            <span>
              {statusLabel} (job {jobId?.slice(0, 8)}…)
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleCancel}
              aria-label="Cancelar generación"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
              Cancelar
            </Button>
          </div>
        </Banner>
      ) : null}

      <section className="grid gap-4 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
            <Field label="Título">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Idioma">
              <Select value={language} onChange={(e) => setLanguage(e.target.value as "" | "es" | "en")}>
                <option value="">Autodetectar</option>
                <option value="es">Español</option>
                <option value="en">English</option>
              </Select>
            </Field>
          </div>
          <Field label="Transcripción">
            <Textarea
              rows={16}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Pega aquí la transcripción de la reunión…"
            />
          </Field>
          <div className="flex items-center gap-2 text-[12px] text-[var(--text-tertiary)]">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] px-3 py-2 hover:bg-[var(--color-subtle)]">
              <input
                type="file"
                accept=".txt,.srt,.md"
                className="hidden"
                onChange={(e) => e.target.files && onFile(e.target.files[0])}
              />
              Subir archivo…
            </label>
            <span>{transcript ? `${transcript.length.toLocaleString("es-MX")} caracteres` : "—"}</span>
          </div>
        </div>
        <aside className="space-y-3 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 p-4">
          <p className="text-[12px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
            Cómo se genera
          </p>
          <ol className="space-y-2 text-[13px] text-[var(--text-secondary)]">
            <li>1. El worker trocea la transcripción con overlap.</li>
            <li>2. Cada chunk alimenta al LLM en cascada.</li>
            <li>3. Los objetos JSON se fusionan y validan.</li>
            <li>4. Puedes guardar como minuta o descartar.</li>
          </ol>
          {modelUsed ? (
            <p className="mt-3 text-[12px] text-[var(--text-tertiary)]">
              Último modelo usado: <Badge>{modelUsed}</Badge>
            </p>
          ) : null}
          <div className="flex flex-col gap-2 pt-2">
            <Button onClick={() => handleGenerate(false)} loading={generating}>
              <Wand2 className="h-4 w-4" aria-hidden /> Previsualizar
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleGenerate(true)}
              loading={generating}
              disabled={transcript.trim().length < 20}
            >
              Generar y guardar
            </Button>
          </div>
        </aside>
      </section>

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
                <li key={i} className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3">
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

          <div className="grid gap-4 lg:grid-cols-2">
            <MinuteSection title="Acuerdos">
              <ul className="space-y-1.5 text-[13px] text-[var(--text-primary)]">
                {result.agreements?.map((a, i) => (
                  <li key={i}>
                    · {a.description}
                    {a.owner ? (
                      <span className="ml-1 text-[var(--text-tertiary)]">({a.owner})</span>
                    ) : null}
                    {a.due_date ? (
                      <span className="ml-1 text-[var(--text-tertiary)]">→ {a.due_date}</span>
                    ) : null}
                  </li>
                ))}
                {!result.agreements?.length ? <li>—</li> : null}
              </ul>
            </MinuteSection>
            <MinuteSection title="Decisiones">
              <ul className="space-y-1.5 text-[13px] text-[var(--text-primary)]">
                {result.decisions?.map((d, i) => (
                  <li key={i}>· {d.description}</li>
                ))}
                {!result.decisions?.length ? <li>—</li> : null}
              </ul>
            </MinuteSection>
            <MinuteSection title="Próximos pasos">
              <ul className="space-y-1.5 text-[13px] text-[var(--text-primary)]">
                {result.next_steps?.map((n, i) => (
                  <li key={i}>· {n.action}</li>
                ))}
                {!result.next_steps?.length ? <li>—</li> : null}
              </ul>
            </MinuteSection>
            <MinuteSection title="Riesgos / bloqueos">
              <ul className="space-y-1.5 text-[13px] text-[var(--text-primary)]">
                {result.risks_blockers?.map((r, i) => (
                  <li key={i}>· {r.description}</li>
                ))}
                {!result.risks_blockers?.length ? <li>—</li> : null}
              </ul>
            </MinuteSection>
          </div>

          {/* ENH-084 + US-108: 4 secciones RAID. Antes de guardar la
              minuta, render read-only desde el output crudo del job;
              tras guardar, switch al editor con persistencia (edit /
              discard / approve bulk con creación de tickets reales). */}
          {savedMinute ? (
            <MinuteRaidSuggestionsEditor
              minute={savedMinute}
              onMinuteChanged={setSavedMinute}
            />
          ) : (
            <RaidSuggestionsSection raid={result.raid ?? EMPTY_RAID_BLOCK} />
          )}

          {savedMinuteId ? (
            <Banner variant="success">
              Minuta guardada.{" "}
              <Link
                className="underline"
                href={`/pmo/projects/${id}/minutes/${savedMinuteId}`}
              >
                Ver minuta
              </Link>{" "}
              ·{" "}
              <Link
                className="underline"
                href={`/pmo/projects/${id}/minutes`}
              >
                Ir a minutas
              </Link>
            </Banner>
          ) : (
            <div className="flex justify-end">
              <Button onClick={savePreview} loading={savingPreview} disabled={generating}>
                Guardar como minuta
              </Button>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

/**
 * ENH-084: render de las 4 secciones RAID estandarizadas en bloques
 * colapsables (CA5). En modo solo lectura aquí; US-108 hace estas filas
 * editables y aprobables.
 */
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

function RaidSuggestionsSection({ raid }: { raid: AIRaidBlock }) {
  const total =
    raid.risks.length +
    raid.issues.length +
    raid.lessons.length +
    raid.changes.length;
  return (
    <section className="space-y-3 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 p-4">
      <header className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Sugerencias RAID detectadas
        </h3>
        <Badge variant={total === 0 ? "neutral" : "info"}>
          {total} {total === 1 ? "item" : "items"}
        </Badge>
      </header>
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
                <Badge variant={items.length === 0 ? "neutral" : "info"}>
                  {items.length}
                </Badge>
              </summary>
              <div className="mt-2 space-y-2">
                {items.length === 0 ? (
                  <p className="text-[12px] italic text-[var(--text-tertiary)]">
                    {meta.emptyHint}
                  </p>
                ) : (
                  items.map((it, i) => (
                    <div
                      key={i}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-2.5 py-2"
                    >
                      <p className="text-[12px] font-medium text-[var(--text-primary)]">
                        {it.short_desc}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                        {it.suggested_owner_name ? (
                          <span>👤 {it.suggested_owner_name}</span>
                        ) : null}
                        {it.suggested_priority ? (
                          <span>⚑ P{it.suggested_priority}</span>
                        ) : null}
                      </div>
                      {it.raw_quote ? (
                        <p className="mt-1 line-clamp-2 italic text-[11px] text-[var(--text-tertiary)]">
                          “{it.raw_quote}”
                        </p>
                      ) : null}
                    </div>
                  ))
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
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
    </label>
  );
}
