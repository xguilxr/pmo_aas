"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Bot, CheckCircle2, Play, XCircle } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getOllamaConfig,
  testAiConnection,
  updateOllamaConfig,
  type OllamaConfigRead,
  type TestConnectionResult,
} from "@/lib/api/admin-ai";

/**
 * Sección de config del proveedor IA local (Ollama vía Tailscale tailnet).
 * Vive embebida en /admin/tenant?tab=config.
 *
 * Historia:
 * - US-045: versión original con Cloudflare Tunnel + CF-Access token.
 * - US-047: pivote a Tailscale; se eliminan los campos CF-Access.
 */
export function OllamaLocalAiForm() {
  const [cfg, setCfg] = useState<OllamaConfigRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null);

  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [timeoutSec, setTimeoutSec] = useState<number>(60);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const data = await getOllamaConfig();
      setCfg(data);
      setBaseUrl(data.base_url ?? "");
      setModel(data.model ?? "");
      setTimeoutSec(data.timeout_sec);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la config IA");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const body = {
        base_url: baseUrl || undefined,
        model: model || undefined,
        timeout_sec: timeoutSec,
      };
      const data = await updateOllamaConfig(body);
      setCfg(data);
      setNotice("Configuración IA guardada");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function onTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await testAiConnection("ollama");
      setTestResult(r);
    } catch (err) {
      setTestResult({
        ok: false,
        latency_ms: null,
        model_present: null,
        tags_count: null,
        error: err instanceof ApiError ? err.message : "Error de conexión",
        code: "UNKNOWN",
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading || !cfg) {
    return <Skeleton className="h-40 w-full" />;
  }

  return (
    <section className="space-y-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-[var(--color-accent)]" aria-hidden />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Proveedor IA local (Ollama)
          </h2>
        </div>
        <p className="text-xs text-[var(--color-tertiary)]">
          Tailscale tailnet privado · ver{" "}
          <a
            href="/docs/ai/local-ollama-setup"
            className="text-[var(--color-accent)] hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            runbook
          </a>
        </p>
      </header>

      <p className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2 text-xs text-[var(--color-tertiary)]">
        Este endpoint debe ser accesible desde el <strong>worker de Railway</strong>
        {" "}vía tailnet Tailscale (hostname MagicDNS{" "}
        <code>ollama-host.&lt;tu-tailnet&gt;.ts.net:11434</code>). El botón
        &quot;Probar conexión&quot; corre desde el servicio <code>api</code>,
        que típicamente NO está en el tailnet — un fallo aquí no implica que
        el worker no pueda alcanzarlo. La verificación real se hace al procesar
        la primera minuta IA.
      </p>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <form onSubmit={save} className="space-y-3">
        <Field label="Base URL del endpoint Ollama (tailnet)">
          <Input
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://ollama-host.<tu-tailnet>.ts.net:11434"
          />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Modelo">
            <Input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="qwen2.5:7b-instruct-q4_K_M"
            />
          </Field>
          <Field label="Timeout (segundos)">
            <Input
              type="number"
              min={5}
              max={600}
              value={timeoutSec}
              onChange={(e) => setTimeoutSec(Number(e.target.value) || 60)}
            />
          </Field>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3">
          <Button
            type="button"
            variant="secondary"
            onClick={onTest}
            loading={testing}
            disabled={!cfg.configured && !baseUrl}
          >
            <Play className="h-4 w-4" aria-hidden /> Probar conexión
          </Button>
          <Button type="submit" loading={saving}>
            Guardar
          </Button>
        </div>
      </form>

      {testResult ? <TestResultBanner result={testResult} /> : null}
    </section>
  );
}

function TestResultBanner({ result }: { result: TestConnectionResult }) {
  if (result.ok) {
    return (
      <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3 text-sm">
        <CheckCircle2 className="mt-0.5 h-4 w-4 text-[var(--color-success-fg)]" aria-hidden />
        <div>
          <div className="font-medium text-[var(--color-primary)]">
            Conexión OK
          </div>
          <div className="text-xs text-[var(--color-tertiary)]">
            Latencia {result.latency_ms} ms ·{" "}
            {result.tags_count ?? 0} modelos disponibles ·{" "}
            {result.model_present
              ? "modelo configurado presente"
              : "modelo configurado NO está en la lista"}
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-danger)] bg-[var(--color-danger-subtle)] p-3 text-sm">
      <XCircle className="mt-0.5 h-4 w-4 text-[var(--color-danger-fg)]" aria-hidden />
      <div>
        <div className="font-medium text-[var(--color-primary)]">
          Falló la conexión{result.code ? ` · ${result.code}` : ""}
        </div>
        <div className="text-xs text-[var(--color-tertiary)]">
          {result.error ?? "Sin detalle"}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
