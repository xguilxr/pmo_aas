"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getPlatformAIDefaults,
  updatePlatformAIDefaults,
  type PlatformAIDefaultsPatch,
  type PlatformAIDefaultsRead,
} from "@/lib/api/superadmin-ai";
import { getStoredUser } from "@/lib/auth-storage";

type ModeValue = "ollama" | "gemini" | "claude" | "disabled" | "";

/**
 * US-054: config de AI a nivel de plataforma.
 *
 * Superadmin puede sobrescribir AI_MODE / OLLAMA_BASE_URL / OLLAMA_MODEL /
 * AI_TIMEOUT_S sin tocar env vars ni redeploy. Los secrets (GEMINI_API_KEY,
 * ANTHROPIC_API_KEY) siguen viviendo en env para evitar guardarlos sin
 * cifrado en BD.
 *
 * Orden de prioridad que el provider aplica:
 *   tenant override (admin) > platform defaults (esta página) > env var
 */
export default function SuperadminAIPage() {
  const user = getStoredUser();
  const [data, setData] = useState<PlatformAIDefaultsRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [aiMode, setAiMode] = useState<ModeValue>("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [timeoutSec, setTimeoutSec] = useState<string>("");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const d = await getPlatformAIDefaults();
      setData(d);
      setAiMode((d.ai_mode as ModeValue | null) ?? "");
      setBaseUrl(d.ollama_base_url ?? "");
      setModel(d.ollama_model ?? "");
      setTimeoutSec(d.ai_timeout_sec != null ? String(d.ai_timeout_sec) : "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la config");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  if (user && !user.is_superadmin) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <Banner variant="danger">Solo Super Admin puede acceder a este panel.</Banner>
      </div>
    );
  }

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const body: PlatformAIDefaultsPatch = {
        ai_mode:
          aiMode === ""
            ? null
            : (aiMode as Exclude<ModeValue, "">),
        ollama_base_url: baseUrl.trim() === "" ? null : baseUrl.trim(),
        ollama_model: model.trim() === "" ? null : model.trim(),
        ai_timeout_sec: timeoutSec.trim() === "" ? null : Number(timeoutSec),
      };
      const d = await updatePlatformAIDefaults(body);
      setData(d);
      setNotice("Defaults de plataforma guardados");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-1">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            <Sparkles className="h-5 w-5 text-[var(--color-accent)]" aria-hidden />
            IA · Defaults de plataforma
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Se aplican a todos los tenants que no tengan override propio.
            Cambian sin redeploy; entran en vigor en el próximo task del worker.
          </p>
        </div>
      </header>

      {loading || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          {error ? <Banner variant="danger">{error}</Banner> : null}
          {notice ? <Banner variant="success">{notice}</Banner> : null}

          <form
            onSubmit={save}
            className="space-y-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]"
          >
            <h2 className="text-sm font-semibold text-[var(--color-primary)]">
              Defaults editables
            </h2>

            <Field
              label="Modo de cascada"
              hint={`Actual env: ${data.env.ai_mode}. Dejar vacío = usar env.`}
            >
              <select
                value={aiMode}
                onChange={(e) => setAiMode(e.target.value as ModeValue)}
                className="h-9 w-full rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-[13px] text-[var(--text-primary)]"
              >
                <option value="">— usar env ({data.env.ai_mode}) —</option>
                <option value="ollama">ollama</option>
                <option value="gemini">gemini</option>
                <option value="claude">claude</option>
                <option value="disabled">disabled</option>
              </select>
            </Field>

            <Field
              label="Ollama — Base URL"
              hint={`Env: ${data.env.ollama_base_url}. Vacío = usar env.`}
            >
              <Input
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://ollama-host.<tailnet>.ts.net:11434"
              />
            </Field>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field
                label="Ollama — Modelo"
                hint={`Env: ${data.env.ollama_model}`}
              >
                <Input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="qwen2.5:7b-instruct-q4_K_M"
                />
              </Field>
              <Field
                label="AI_TIMEOUT_S (segundos)"
                hint={`Env: ${data.env.ai_timeout_sec}s. Rango: 5–3600.`}
              >
                <Input
                  type="number"
                  min={5}
                  max={3600}
                  value={timeoutSec}
                  onChange={(e) => setTimeoutSec(e.target.value)}
                  placeholder="usar env"
                />
              </Field>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <Button type="submit" loading={saving}>
                Guardar defaults
              </Button>
            </div>
          </form>

          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 text-[13px] text-[var(--text-secondary)]">
            <h2 className="mb-2 text-sm font-semibold text-[var(--color-primary)]">
              Snapshot de variables de entorno
            </h2>
            <p className="mb-3 text-[12px] text-[var(--text-tertiary)]">
              Solo lectura. Secrets se quedan en env para evitar almacenarlos sin cifrado.
            </p>
            <dl className="grid grid-cols-[180px_1fr] gap-x-4 gap-y-1.5 font-mono text-[12px]">
              <dt className="text-[var(--text-tertiary)]">AI_MODE</dt>
              <dd>{data.env.ai_mode}</dd>
              <dt className="text-[var(--text-tertiary)]">OLLAMA_BASE_URL</dt>
              <dd>{data.env.ollama_base_url}</dd>
              <dt className="text-[var(--text-tertiary)]">OLLAMA_MODEL</dt>
              <dd>{data.env.ollama_model}</dd>
              <dt className="text-[var(--text-tertiary)]">AI_TIMEOUT_S</dt>
              <dd>{data.env.ai_timeout_sec}</dd>
              <dt className="text-[var(--text-tertiary)]">GEMINI_API_KEY</dt>
              <dd>{data.env.gemini_configured ? "configurado" : "vacío"}</dd>
              <dt className="text-[var(--text-tertiary)]">ANTHROPIC_API_KEY</dt>
              <dd>{data.env.claude_configured ? "configurado" : "vacío"}</dd>
            </dl>
          </section>
        </>
      )}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
        {label}
      </span>
      {children}
      {hint ? (
        <span className="mt-1 block text-[11px] text-[var(--text-tertiary)]">{hint}</span>
      ) : null}
    </label>
  );
}
