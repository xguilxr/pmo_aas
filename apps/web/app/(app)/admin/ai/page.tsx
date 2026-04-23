"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  KeyRound,
  Plug,
  Sparkles,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  BYO_PROVIDER_LABEL,
  BYO_PROVIDER_MODELS,
  type BYOProvider,
  type TenantAIMode,
  type TenantAIProviderRead,
  getTenantAIProvider,
  testTenantAIProvider,
  updateTenantAIProvider,
} from "@/lib/api/admin-ai";
import { cn } from "@/lib/cn";

const MODE_LABEL: Record<TenantAIMode, string> = {
  disabled: "Sin IA",
  platform: "IA de la plataforma (Groq)",
  byo: "Conectar mi proveedor",
};

const MODE_DESCRIPTION: Record<TenantAIMode, string> = {
  disabled:
    "Desactiva todas las funciones de IA. Los botones de 'Generar con IA' se ocultan.",
  platform:
    "Usa la IA que hostea la plataforma (Groq · llama-3.1-70b-versatile). Sólo minutas por ahora; el contenido del tenant nunca se comparte con otros tenants.",
  byo:
    "Conecta tu propia instancia de OpenAI, Claude, Perplexity, Gemini u Ollama. El costo corre por tu cuenta y puedes usar IA para minutas y reportes.",
};

export default function TenantAdminAIPage() {
  const [data, setData] = useState<TenantAIProviderRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [pendingMode, setPendingMode] = useState<TenantAIMode | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  // BYO form state (solo válido cuando mode === "byo").
  const [byoProvider, setByoProvider] = useState<BYOProvider>("openai");
  const [byoKey, setByoKey] = useState<string>("");
  const [byoKeyDirty, setByoKeyDirty] = useState(false);
  const [byoModel, setByoModel] = useState<string>("");
  const [byoBaseUrl, setByoBaseUrl] = useState<string>("");

  // Test connection state.
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<
    | { ok: boolean; latency_ms: number | null; error: string | null }
    | null
  >(null);

  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const d = await getTenantAIProvider();
      setData(d);
      setPendingMode(d.mode);
      if (d.byo) {
        setByoProvider(d.byo.provider);
        setByoModel(d.byo.model ?? "");
        setByoBaseUrl(d.byo.base_url ?? "");
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al cargar config IA",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function chooseMode(next: TenantAIMode) {
    setPendingMode(next);
    setNotice(null);
    // Si cambia de modo real, abrir el modal de confirmación.
    if (data && next !== data.mode) {
      setConfirmOpen(true);
    }
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!pendingMode) return;
    // Si viene del form y cambia de modo, requerir confirmación primero.
    if (data && pendingMode !== data.mode && !confirmOpen) {
      setConfirmOpen(true);
      return;
    }
    await persist();
  }

  async function persist() {
    if (!pendingMode) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const body: Parameters<typeof updateTenantAIProvider>[0] = {
        mode: pendingMode,
      };
      if (pendingMode === "byo") {
        body.byo = {
          provider: byoProvider,
          // Sólo mandamos la api_key si el user la tocó (o no hay una previa).
          api_key: byoKeyDirty ? byoKey : undefined,
          model: byoModel || null,
          base_url: byoBaseUrl || null,
        };
      }
      const updated = await updateTenantAIProvider(body);
      setData(updated);
      setByoKey("");
      setByoKeyDirty(false);
      setConfirmOpen(false);
      setNotice("Configuración guardada.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function runTest() {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const body =
        pendingMode === "byo"
          ? {
              byo: {
                provider: byoProvider,
                api_key: byoKeyDirty ? byoKey : undefined,
                model: byoModel || null,
                base_url: byoBaseUrl || null,
              },
            }
          : {};
      const r = await testTenantAIProvider(body);
      setTestResult({
        ok: r.ok,
        latency_ms: r.latency_ms,
        error: r.error,
      });
    } catch (err) {
      setTestResult({
        ok: false,
        latency_ms: null,
        error: err instanceof ApiError ? err.message : "Error al probar conexión",
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading || !data || !pendingMode) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const modeChanged = pendingMode !== data.mode;
  const currentBadge =
    data.mode === "disabled" ? (
      <Badge variant="neutral">Sin IA</Badge>
    ) : data.mode === "platform" ? (
      <Badge variant="info">Plataforma · Groq</Badge>
    ) : (
      <Badge variant="success">
        BYO · {data.byo ? BYO_PROVIDER_LABEL[data.byo.provider] : "?"}
      </Badge>
    );

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="space-y-2">
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/admin/tenant" className="hover:underline">
            Gestión de Tenant
          </Link>
          <span className="mx-1">/</span>
          <span>IA</span>
        </nav>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles
                className="h-6 w-6 text-[var(--color-accent)]"
                aria-hidden
              />
              <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                Configuración de IA
              </h1>
            </div>
            <p className="mt-1 text-sm text-[var(--color-tertiary)]">
              Elige cómo procesa minutas y reportes tu tenant. Los cambios
              pueden interrumpir la conexión activa — confírmalos en el
              diálogo antes de guardar.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--color-tertiary)]">Estado actual:</span>
            {currentBadge}
          </div>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <form onSubmit={submit} className="space-y-4">
        <section className="space-y-2">
          {(Object.keys(MODE_LABEL) as TenantAIMode[]).map((m) => {
            const checked = pendingMode === m;
            return (
              <label
                key={m}
                className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-[var(--radius-xl)] border p-4 shadow-[var(--shadow-sm)] transition-colors",
                  checked
                    ? "border-[var(--color-accent)] bg-[var(--color-subtle)]"
                    : "border-[var(--border-default)] bg-[var(--color-surface)]",
                )}
              >
                <input
                  type="radio"
                  name="mode"
                  value={m}
                  checked={checked}
                  onChange={() => chooseMode(m)}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[var(--color-primary)]">
                      {MODE_LABEL[m]}
                    </span>
                    {m === data.mode ? (
                      <Badge variant="neutral">Actual</Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 text-[13px] text-[var(--color-secondary)]">
                    {MODE_DESCRIPTION[m]}
                  </p>
                </div>
              </label>
            );
          })}
        </section>

        {pendingMode === "byo" ? (
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <div className="mb-3 flex items-center gap-2">
              <Plug
                className="h-4 w-4 text-[var(--color-tertiary)]"
                aria-hidden
              />
              <h2 className="text-sm font-semibold text-[var(--color-primary)]">
                Conectar proveedor
              </h2>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="byo-provider"
                  className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
                >
                  Proveedor
                </label>
                <Select
                  id="byo-provider"
                  value={byoProvider}
                  onChange={(e) =>
                    setByoProvider(e.target.value as BYOProvider)
                  }
                >
                  {(Object.keys(BYO_PROVIDER_LABEL) as BYOProvider[]).map(
                    (p) => (
                      <option key={p} value={p}>
                        {BYO_PROVIDER_LABEL[p]}
                      </option>
                    ),
                  )}
                </Select>
              </div>
              <div>
                <label
                  htmlFor="byo-model"
                  className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
                >
                  Modelo
                </label>
                <Input
                  id="byo-model"
                  list={`byo-model-suggestions-${byoProvider}`}
                  value={byoModel}
                  onChange={(e) => setByoModel(e.target.value)}
                  placeholder="Ej. gpt-4o-mini"
                />
                <datalist id={`byo-model-suggestions-${byoProvider}`}>
                  {BYO_PROVIDER_MODELS[byoProvider].map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </div>
              {byoProvider === "ollama" || byoProvider === "openai" ? (
                <div className="sm:col-span-2">
                  <label
                    htmlFor="byo-base-url"
                    className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
                  >
                    Base URL{byoProvider === "ollama" ? "" : " (opcional)"}
                  </label>
                  <Input
                    id="byo-base-url"
                    value={byoBaseUrl}
                    onChange={(e) => setByoBaseUrl(e.target.value)}
                    placeholder={
                      byoProvider === "ollama"
                        ? "http://host.ts.net:11434"
                        : "https://api.openai.com/v1"
                    }
                  />
                </div>
              ) : null}
              {byoProvider !== "ollama" ? (
                <div className="sm:col-span-2">
                  <label
                    htmlFor="byo-key"
                    className="mb-1.5 flex items-center gap-2 text-sm font-medium text-[var(--color-secondary)]"
                  >
                    <KeyRound className="h-3.5 w-3.5" aria-hidden />
                    API key
                    {data.byo?.has_api_key ? (
                      <span className="text-[11px] font-normal text-[var(--color-tertiary)]">
                        (actual: {data.byo.api_key_mask ?? "•••"})
                      </span>
                    ) : null}
                  </label>
                  <Input
                    id="byo-key"
                    type="password"
                    value={byoKey}
                    onChange={(e) => {
                      setByoKey(e.target.value);
                      setByoKeyDirty(true);
                    }}
                    placeholder={
                      data.byo?.has_api_key
                        ? "Dejar vacío para conservar la actual"
                        : "sk-..."
                    }
                    autoComplete="off"
                  />
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex items-center gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={runTest}
                loading={testing}
              >
                Probar conexión
              </Button>
              {testResult ? (
                <span className="inline-flex items-center gap-1 text-[13px]">
                  {testResult.ok ? (
                    <>
                      <CheckCircle2
                        className="h-4 w-4 text-[var(--color-success-fg)]"
                        aria-hidden
                      />
                      <span className="text-[var(--color-success-fg)]">
                        Conexión OK
                        {testResult.latency_ms !== null
                          ? ` (${testResult.latency_ms} ms)`
                          : ""}
                      </span>
                    </>
                  ) : (
                    <>
                      <XCircle
                        className="h-4 w-4 text-[var(--color-danger-fg)]"
                        aria-hidden
                      />
                      <span className="text-[var(--color-danger-fg)]">
                        {testResult.error ?? "Falló la conexión"}
                      </span>
                    </>
                  )}
                </span>
              ) : null}
            </div>
          </section>
        ) : null}

        <div className="flex items-center justify-end gap-2">
          <Button
            type="submit"
            loading={saving}
            disabled={!modeChanged && pendingMode !== "byo"}
          >
            Guardar
          </Button>
        </div>
      </form>

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Confirmar cambio de modo"
      >
        <div className="space-y-3">
          <div className="flex items-start gap-2 text-[13px] text-[var(--color-secondary)]">
            <AlertTriangle
              className="h-5 w-5 shrink-0 text-[var(--color-warning-fg)]"
              aria-hidden
            />
            <p>
              Cambiar de <strong>{MODE_LABEL[data.mode]}</strong> a{" "}
              <strong>{MODE_LABEL[pendingMode]}</strong> puede interrumpir la
              conexión activa con tu proveedor actual. Las minutas en proceso
              podrían fallar. ¿Continuar?
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setConfirmOpen(false);
                setPendingMode(data.mode); // revert
              }}
            >
              Cancelar
            </Button>
            <Button type="button" onClick={persist} loading={saving}>
              Sí, cambiar modo
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
