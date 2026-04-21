"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Sparkles, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { generateMinute, type AIMinutePayload } from "@/lib/api/ai";
import { useAIJobPolling } from "@/lib/hooks/use-ai-job-polling";

export default function NewAIMinutePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [title, setTitle] = useState("Minuta (IA)");
  const [language, setLanguage] = useState<"" | "es" | "en">("");
  const [transcript, setTranscript] = useState("");
  const [dispatching, setDispatching] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [savingRequested, setSavingRequested] = useState(false);
  const [result, setResult] = useState<AIMinutePayload | null>(null);
  const [savedMinuteId, setSavedMinuteId] = useState<string | null>(null);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
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
      if (savingRequested && payload?.minute_id) {
        router.replace(`/admin/projects/${id}/minutes?created=1`);
      }
    },
    onError: (job) => {
      setError(job.error || "La generación falló");
    },
  });

  async function onFile(file: File) {
    if (file.size > 5 * 1024 * 1024) {
      setError("El archivo supera 5 MB");
      return;
    }
    const text = await file.text();
    setTranscript(text);
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
    setSavingRequested(save);
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
          <Link href="/admin/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/admin/projects/${id}`} className="hover:underline">
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/admin/projects/${id}/minutes`} className="hover:underline">
            Minutas
          </Link>
          <span className="mx-1">/</span>
          <span>Generar con IA</span>
        </nav>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          <Sparkles className="h-6 w-6 text-[var(--color-accent)]" aria-hidden />
          Minuta con IA
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Pega la transcripción (o sube un .txt). El worker procesa la cascada Ollama → Gemini →
          Claude según la configuración del tenant. Max 5 MB.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {polling.error ? <Banner variant="danger">{polling.error}</Banner> : null}

      {statusLabel ? (
        <Banner variant="info">
          {statusLabel} (job {jobId?.slice(0, 8)}…)
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

          {savedMinuteId ? (
            <Banner variant="success">
              Minuta guardada.{" "}
              <Link
                className="underline"
                href={`/admin/projects/${id}/minutes`}
              >
                Ir a minutas
              </Link>
            </Banner>
          ) : (
            <div className="flex justify-end">
              <Button onClick={() => handleGenerate(true)} loading={generating}>
                Guardar como minuta
              </Button>
            </div>
          )}
        </section>
      ) : null}
    </div>
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
