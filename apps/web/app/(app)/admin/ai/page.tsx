"use client";

import Link from "next/link";
import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useState,
} from "react";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ExternalLink,
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
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  type BYOProvider,
  type BYOProviderInfo,
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
  byo: "Conectar tu propio proveedor",
};

const MODE_DESCRIPTION: Record<TenantAIMode, string> = {
  disabled:
    "Desactiva todas las funciones de IA. Los botones de 'Generar con IA' se ocultan. Default para tenants nuevos.",
  platform:
    "Usa la IA que hostea la plataforma (Groq · llama-3.3-70b-versatile). Por ahora sólo minutas; el contenido del tenant nunca se comparte con otros tenants.",
  byo: "Conecta tu cuenta de OpenAI, Claude, Gemini o Perplexity. El costo corre por tu cuenta y puedes usar IA para minutas y reportes.",
};

export default function TenantAdminAIPage() {
  const [data, setData] = useState<TenantAIProviderRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [pendingMode, setPendingMode] = useState<TenantAIMode | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  // Wizard "conectar proveedor".
  const [wizardProvider, setWizardProvider] = useState<BYOProviderInfo | null>(
    null,
  );

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const d = await getTenantAIProvider();
      setData(d);
      setPendingMode(d.mode);
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

  async function saveMode(next: TenantAIMode) {
    if (!data) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateTenantAIProvider({ mode: next });
      setData(updated);
      setPendingMode(updated.mode);
      setConfirmOpen(false);
      setNotice(`Modo cambiado a "${MODE_LABEL[next]}".`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  function chooseMode(next: TenantAIMode) {
    if (!data) return;
    setPendingMode(next);
    if (next === data.mode) return;
    setConfirmOpen(true);
  }

  if (loading || !data || !pendingMode) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const currentBadge =
    data.mode === "disabled" ? (
      <Badge variant="neutral">Sin IA</Badge>
    ) : data.mode === "platform" ? (
      <Badge variant="info">Plataforma · Groq</Badge>
    ) : (
      <Badge variant="success">
        BYO
        {data.byo ? ` · ${data.byo.provider}` : ""}
      </Badge>
    );

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="space-y-2">
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/admin" className="hover:underline">
            Admin
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
            <span className="text-xs text-[var(--color-tertiary)]">
              Estado actual:
            </span>
            {currentBadge}
          </div>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="space-y-2">
        <ModeCard
          mode="disabled"
          pending={pendingMode}
          current={data.mode}
          onChoose={chooseMode}
        />
        <ModeCard
          mode="platform"
          pending={pendingMode}
          current={data.mode}
          onChoose={chooseMode}
        />
        <ModeCard
          mode="byo"
          pending={pendingMode}
          current={data.mode}
          onChoose={chooseMode}
        />
      </section>

      {pendingMode === "byo" ? (
        <BYOSection
          data={data}
          onOpenWizard={(p) => setWizardProvider(p)}
        />
      ) : null}

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
                setPendingMode(data.mode);
              }}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={() => saveMode(pendingMode)}
              loading={saving}
            >
              Sí, cambiar modo
            </Button>
          </div>
        </div>
      </Modal>

      {wizardProvider ? (
        <BYOConnectWizard
          provider={wizardProvider}
          onClose={() => setWizardProvider(null)}
          onConnected={() => {
            setWizardProvider(null);
            void refresh();
            setNotice("Proveedor conectado.");
          }}
        />
      ) : null}
    </div>
  );
}

/* ======================= ModeCard ======================= */

function ModeCard({
  mode,
  pending,
  current,
  onChoose,
}: {
  mode: TenantAIMode;
  pending: TenantAIMode;
  current: TenantAIMode;
  onChoose: (m: TenantAIMode) => void;
}) {
  const checked = pending === mode;
  return (
    <label
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
        value={mode}
        checked={checked}
        onChange={() => onChoose(mode)}
        className="mt-1"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[var(--color-primary)]">
            {MODE_LABEL[mode]}
          </span>
          {mode === current ? <Badge variant="neutral">Actual</Badge> : null}
        </div>
        <p className="mt-1 text-[13px] text-[var(--color-secondary)]">
          {MODE_DESCRIPTION[mode]}
        </p>
      </div>
    </label>
  );
}

/* ======================= BYOSection ======================= */

function BYOSection({
  data,
  onOpenWizard,
}: {
  data: TenantAIProviderRead;
  onOpenWizard: (p: BYOProviderInfo) => void;
}) {
  return (
    <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <div className="flex items-center gap-2">
        <Plug
          className="h-4 w-4 text-[var(--color-tertiary)]"
          aria-hidden
        />
        <h2 className="text-sm font-semibold text-[var(--color-primary)]">
          Conectar tu proveedor
        </h2>
      </div>
      <p className="text-[12px] text-[var(--color-tertiary)]">
        Elige tu proveedor favorito. Te abriremos un asistente para pegar
        la API key y probar la conexión.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        {data.byo_catalog.map((p) => (
          <ProviderCard
            key={p.key}
            info={p}
            connected={data.byo?.provider === p.key && data.byo.has_api_key}
            disabled={false}
            onClick={() => onOpenWizard(p)}
          />
        ))}
      </div>

      {data.byo ? (
        <div className="mt-3 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3 text-[12px]">
          <div className="font-medium text-[var(--color-primary)]">
            Conexión activa
          </div>
          <div className="mt-1 text-[var(--color-secondary)]">
            Proveedor: <strong>{data.byo.provider}</strong> · Modelo:{" "}
            <strong>{data.byo.model ?? "—"}</strong> · Key:{" "}
            <span className="font-mono">
              {data.byo.api_key_mask ?? "sin key"}
            </span>
          </div>
          {data.byo.last_test_status ? (
            <div className="mt-1 text-[var(--color-tertiary)]">
              Último test:{" "}
              {data.byo.last_test_status === "ok" ? "OK" : "FAIL"} ·{" "}
              {data.byo.last_test_at
                ? new Date(data.byo.last_test_at).toLocaleString()
                : "—"}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function ProviderCard({
  info,
  connected,
  disabled,
  onClick,
}: {
  info: BYOProviderInfo;
  connected: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex flex-col items-start gap-2 rounded-[var(--radius-lg)] border p-3 text-left shadow-[var(--shadow-sm)] transition-colors",
        disabled
          ? "cursor-not-allowed border-[var(--border-subtle)] bg-[var(--color-subtle)] opacity-70"
          : "border-[var(--border-default)] bg-[var(--color-surface)] hover:border-[var(--color-accent)]",
      )}
    >
      <div className="flex w-full items-center justify-between gap-2">
        <span className="font-medium text-[var(--color-primary)]">
          {info.label}
        </span>
        {connected ? (
          <Badge variant="success">
            <Check className="mr-1 h-3 w-3" aria-hidden />
            Conectado
          </Badge>
        ) : disabled ? (
          <Badge variant="neutral">Próximamente</Badge>
        ) : (
          <Badge variant="info">Conectar</Badge>
        )}
      </div>
      <p className="text-[11px] leading-tight text-[var(--color-tertiary)]">
        {info.description}
      </p>
    </button>
  );
}

/* ======================= BYOConnectWizard ======================= */

function BYOConnectWizard({
  provider,
  onClose,
  onConnected,
}: {
  provider: BYOProviderInfo;
  onClose: () => void;
  onConnected: () => void;
}) {
  type Step = "intro" | "key" | "test" | "save";
  const [step, setStep] = useState<Step>("intro");

  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(provider.suggested_models[0] ?? "");
  const [baseUrl, setBaseUrl] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<
    | { ok: boolean; latency_ms: number | null; error: string | null }
    | null
  >(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runTest() {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const r = await testTenantAIProvider({
        byo: {
          provider: provider.key,
          api_key: apiKey,
          model: model || null,
          base_url: baseUrl || null,
        },
      });
      setTestResult({
        ok: r.ok,
        latency_ms: r.latency_ms,
        error: r.error,
      });
      if (r.ok) setStep("save");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al probar");
    } finally {
      setTesting(false);
    }
  }

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await updateTenantAIProvider({
        mode: "byo",
        byo: {
          provider: provider.key,
          api_key: apiKey,
          model: model || null,
          base_url: baseUrl || null,
        },
      });
      onConnected();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={`Conectar ${provider.label}`}
    >
      {step === "intro" ? (
        <WizardIntro
          info={provider}
          onBack={onClose}
          onNext={() => setStep("key")}
        />
      ) : step === "key" ? (
        <WizardKey
          info={provider}
          apiKey={apiKey}
          setApiKey={setApiKey}
          model={model}
          setModel={setModel}
          baseUrl={baseUrl}
          setBaseUrl={setBaseUrl}
          onBack={() => setStep("intro")}
          onNext={() => setStep("test")}
        />
      ) : step === "test" ? (
        <WizardTest
          testing={testing}
          result={testResult}
          onBack={() => setStep("key")}
          onTest={runTest}
          onNext={() => setStep("save")}
        />
      ) : (
        <WizardSave
          provider={provider}
          model={model}
          apiKeyPreview={apiKey.slice(-4)}
          saving={saving}
          error={error}
          onBack={() => setStep("test")}
          onSave={save}
        />
      )}
    </Modal>
  );
}

function WizardIntro({
  info,
  onBack,
  onNext,
}: {
  info: BYOProviderInfo;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-3">
      <p className="text-[13px] text-[var(--color-secondary)]">
        Vamos a conectar <strong>{info.label}</strong>. En 3 pasos:
      </p>
      <ol className="list-inside list-decimal space-y-1 text-[13px] text-[var(--color-secondary)]">
        <li>Generas una API key en la consola del proveedor.</li>
        <li>La pegas aquí y elegimos el modelo.</li>
        <li>Probamos la conexión y la guardamos cifrada.</li>
      </ol>
      <DeepLinks info={info} />
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onBack}>
          Cancelar
        </Button>
        <Button onClick={onNext}>Continuar</Button>
      </div>
    </div>
  );
}

function WizardKey({
  info,
  apiKey,
  setApiKey,
  model,
  setModel,
  baseUrl,
  setBaseUrl,
  onBack,
  onNext,
}: {
  info: BYOProviderInfo;
  apiKey: string;
  setApiKey: (s: string) => void;
  model: string;
  setModel: (s: string) => void;
  baseUrl: string;
  setBaseUrl: (s: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const canAdvance = apiKey.trim().length > 5;
  return (
    <div className="space-y-3">
      <div>
        <label
          htmlFor="wiz-key"
          className="mb-1.5 flex items-center gap-1 text-sm font-medium text-[var(--color-secondary)]"
        >
          <KeyRound className="h-3.5 w-3.5" aria-hidden />
          API key
        </label>
        <Input
          id="wiz-key"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          autoComplete="off"
          autoFocus
          placeholder="Pega aquí tu API key"
        />
        <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
          La guardamos cifrada con Fernet. Nunca volverás a ver la key en
          claro después de guardar.
        </p>
      </div>
      <div>
        <label
          htmlFor="wiz-model"
          className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
        >
          Modelo
        </label>
        <Input
          id="wiz-model"
          list="wiz-model-suggestions"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="Ej. gpt-4o-mini"
        />
        <datalist id="wiz-model-suggestions">
          {info.suggested_models.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
      </div>
      {info.requires_base_url ? (
        <div>
          <label
            htmlFor="wiz-url"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Base URL (opcional)
          </label>
          <Input
            id="wiz-url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api..."
          />
        </div>
      ) : null}
      <DeepLinks info={info} compact />
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onBack}>
          Atrás
        </Button>
        <Button onClick={onNext} disabled={!canAdvance}>
          Continuar
        </Button>
      </div>
    </div>
  );
}

function WizardTest({
  testing,
  result,
  onBack,
  onTest,
  onNext,
}: {
  testing: boolean;
  result: { ok: boolean; latency_ms: number | null; error: string | null } | null;
  onBack: () => void;
  onTest: () => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-3">
      <p className="text-[13px] text-[var(--color-secondary)]">
        Vamos a hacer un ping mínimo al proveedor con tu key y modelo para
        confirmar que responde.
      </p>
      <div className="flex items-center gap-3">
        <Button onClick={onTest} loading={testing} variant="secondary">
          Probar conexión
        </Button>
        {result ? (
          <span className="inline-flex items-center gap-1 text-[13px]">
            {result.ok ? (
              <>
                <CheckCircle2
                  className="h-4 w-4 text-[var(--color-success-fg)]"
                  aria-hidden
                />
                <span className="text-[var(--color-success-fg)]">
                  Conexión OK
                  {result.latency_ms !== null
                    ? ` · ${result.latency_ms} ms`
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
                  {result.error ?? "Falló"}
                </span>
              </>
            )}
          </span>
        ) : null}
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onBack}>
          Atrás
        </Button>
        <Button onClick={onNext} disabled={!result?.ok}>
          Continuar
        </Button>
      </div>
    </div>
  );
}

function WizardSave({
  provider,
  model,
  apiKeyPreview,
  saving,
  error,
  onBack,
  onSave,
}: {
  provider: BYOProviderInfo;
  model: string;
  apiKeyPreview: string;
  saving: boolean;
  error: string | null;
  onBack: () => void;
  onSave: (e: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form onSubmit={onSave} className="space-y-3">
      <p className="text-[13px] text-[var(--color-secondary)]">
        Último paso: guardar la conexión. Al confirmar, cambiamos el modo del
        tenant a <strong>BYO</strong> usando estas credenciales.
      </p>
      <dl className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-1 text-[13px]">
        <dt className="text-[var(--color-tertiary)]">Proveedor</dt>
        <dd className="font-medium text-[var(--color-primary)]">
          {provider.label}
        </dd>
        <dt className="text-[var(--color-tertiary)]">Modelo</dt>
        <dd className="text-[var(--color-primary)]">{model || "—"}</dd>
        <dt className="text-[var(--color-tertiary)]">Key</dt>
        <dd className="font-mono text-[var(--color-primary)]">
          •••{apiKeyPreview}
        </dd>
      </dl>
      {error ? <Banner variant="danger">{error}</Banner> : null}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onBack}>
          Atrás
        </Button>
        <Button type="submit" loading={saving}>
          Guardar y activar
        </Button>
      </div>
    </form>
  );
}

function DeepLinks({
  info,
  compact,
}: {
  info: BYOProviderInfo;
  compact?: boolean;
}): ReactNode {
  return (
    <div
      className={cn(
        "flex flex-wrap gap-3 text-[12px]",
        compact ? "pt-1" : "rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3",
      )}
    >
      <a
        href={info.api_keys_url}
        target="_blank"
        rel="noreferrer noopener"
        className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
      >
        Generar API key
        <ExternalLink className="h-3 w-3" aria-hidden />
      </a>
      <a
        href={info.docs_url}
        target="_blank"
        rel="noreferrer noopener"
        className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
      >
        Documentación
        <ExternalLink className="h-3 w-3" aria-hidden />
      </a>
    </div>
  );
}
