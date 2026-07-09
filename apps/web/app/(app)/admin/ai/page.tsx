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
  FileText,
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
import { Textarea } from "@/components/ui/textarea";
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

const MAX_INSTRUCTIONS_LEN = 2000;

const MODE_DESCRIPTION: Record<TenantAIMode, string> = {
  disabled:
    "Desactiva todas las funciones de IA. Los botones de 'Generar con IA' se ocultan. Default para tenants nuevos.",
  platform:
    "Usa la IA que hostea la plataforma (Groq · llama-3.3-70b-versatile). Por ahora sólo minutas; el contenido del tenant nunca se comparte con otros tenants.",
  byo: "Conecta OpenAI, Claude, Gemini, Perplexity, Microsoft Copilot M365 (Azure OpenAI) o cualquier endpoint OpenAI-compatible. El costo corre por tu cuenta.",
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
      // BUG-060: si el backend rechaza el switch a `byo` por falta de
      // config previa, en vez de dejar al usuario en una pantalla de
      // error cerramos el modal y le sugerimos abrir el wizard de
      // conexión. El error técnico queda como notice descartable.
      const msg = err instanceof ApiError ? err.message : "Error al guardar";
      const needsWizard =
        next === "byo" &&
        err instanceof ApiError &&
        /byo requerido/i.test(err.message);
      if (needsWizard) {
        setConfirmOpen(false);
        setPendingMode(data.mode);
        setNotice(
          "Para usar BYO necesitas conectar primero un proveedor. Abre el wizard desde la lista.",
        );
      } else {
        setError(msg);
      }
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

      <PermanentInstructionsSection
        mode={data.mode}
        value={data.instructions_md ?? ""}
        onSaved={(instructionsMd) =>
          setData((prev) => (prev ? { ...prev, instructions_md: instructionsMd } : prev))
        }
      />

      {pendingMode === "byo" ? (
        <BYOSection
          data={data}
          onOpenWizard={(p) => setWizardProvider(p)}
          onAfterRetest={() => void refresh()}
        />
      ) : null}

      <Modal
        open={confirmOpen}
        onClose={() => {
          // BUG-060: limpiar error previo al cerrar el modal de cambio
          // de modo. Antes el error de un intento fallido quedaba
          // visible aunque el usuario reculara y configurara BYO via
          // el wizard.
          setConfirmOpen(false);
          setError(null);
        }}
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

/* ======================= PermanentInstructionsSection ======================= */

function PermanentInstructionsSection({
  mode,
  value,
  onSaved,
}: {
  mode: TenantAIMode;
  value: string;
  onSaved: (instructionsMd: string | null) => void;
}) {
  const [text, setText] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    setText(value);
  }, [value]);

  const dirty = text.trim() !== (value ?? "").trim();

  async function save() {
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      const normalized = text.trim();
      const updated = await updateTenantAIProvider({
        mode,
        // ENH-189: normaliza vacío → "" (nunca se omite desde este form,
        // así el owner puede borrar las instrucciones guardando en blanco).
        instructions_md: normalized,
      });
      setText(updated.instructions_md ?? "");
      onSaved(updated.instructions_md ?? null);
      setOk("Instrucciones guardadas.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Error al guardar las instrucciones.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
        <h2 className="text-sm font-semibold text-[var(--color-primary)]">
          Instrucciones permanentes de IA
        </h2>
      </div>
      <p className="text-[12px] text-[var(--color-tertiary)]">
        Se aplican a toda generación de IA del tenant (minutas y reportes).
        Ej.: &quot;Redacta siempre en español formal; las fechas en formato
        DD/MMM.&quot;
      </p>
      <Textarea
        rows={5}
        maxLength={MAX_INSTRUCTIONS_LEN}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setOk(null);
        }}
        placeholder="Ej. Redacta siempre en español formal; las fechas en formato DD/MMM."
      />
      <p className="text-right text-[11px] text-[var(--color-tertiary)]">
        {text.length.toLocaleString("es-MX")} /{" "}
        {MAX_INSTRUCTIONS_LEN.toLocaleString("es-MX")}
      </p>
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {ok ? <Banner variant="success">{ok}</Banner> : null}
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          onClick={save}
          loading={saving}
          disabled={!dirty}
        >
          Guardar instrucciones
        </Button>
      </div>
    </section>
  );
}

/* ======================= BYOSection ======================= */

function BYOSection({
  data,
  onOpenWizard,
  onAfterRetest,
}: {
  data: TenantAIProviderRead;
  onOpenWizard: (p: BYOProviderInfo) => void;
  onAfterRetest: () => void;
}) {
  const activeKey = data.byo?.provider as BYOProvider | undefined;
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
            connected={activeKey === p.key && !!data.byo?.has_api_key}
            testStatus={activeKey === p.key ? data.byo?.last_test_status ?? null : null}
            disabled={false}
            onClick={() => onOpenWizard(p)}
          />
        ))}
      </div>

      {data.byo ? (
        <ActiveConnectionPanel data={data} onAfterRetest={onAfterRetest} />
      ) : null}
    </section>
  );
}

function ActiveConnectionPanel({
  data,
  onAfterRetest,
}: {
  data: TenantAIProviderRead;
  onAfterRetest: () => void;
}) {
  const [retesting, setRetesting] = useState(false);
  const [retestError, setRetestError] = useState<string | null>(null);
  const [retestOk, setRetestOk] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const byo = data.byo!;
  const failed = byo.last_test_status === "fail";

  async function retest() {
    setRetesting(true);
    setRetestError(null);
    setRetestOk(null);
    try {
      const r = await testTenantAIProvider({});
      if (r.ok) {
        setRetestOk(
          r.latency_ms != null ? `Conexión OK · ${r.latency_ms} ms` : "Conexión OK",
        );
      } else {
        setRetestError(r.error ?? "Falló la prueba.");
      }
      onAfterRetest();
    } catch (err) {
      setRetestError(err instanceof ApiError ? err.message : "Error al probar.");
    } finally {
      setRetesting(false);
    }
  }

  if (editing) {
    return (
      <ActiveConnectionEditForm
        byo={byo}
        onCancel={() => setEditing(false)}
        onSaved={() => {
          setEditing(false);
          onAfterRetest();
        }}
      />
    );
  }

  return (
    <div className="mt-3 space-y-2">
      {failed ? (
        <Banner variant="danger">
          <strong>Última prueba falló:</strong>{" "}
          {byo.last_test_error ?? "sin detalle"}
        </Banner>
      ) : null}
      {retestError ? <Banner variant="danger">{retestError}</Banner> : null}
      {retestOk ? <Banner variant="success">{retestOk}</Banner> : null}

      <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3 text-[12px]">
        <div className="font-medium text-[var(--color-primary)]">
          Conexión activa
        </div>
        <div className="mt-1 text-[var(--color-secondary)]">
          Proveedor: <strong>{byo.provider}</strong> · Modelo:{" "}
          <strong>{byo.model ?? "—"}</strong>
          {byo.base_url ? (
            <>
              {" "}· Base URL:{" "}
              <span className="font-mono break-all">{byo.base_url}</span>
            </>
          ) : null}
          {byo.deployment_name ? (
            <>
              {" "}· Deployment:{" "}
              <span className="font-mono">{byo.deployment_name}</span>
            </>
          ) : null}
          {byo.api_version ? (
            <>
              {" "}· API version:{" "}
              <span className="font-mono">{byo.api_version}</span>
            </>
          ) : null}
          {" "}· Key:{" "}
          <span className="font-mono">{byo.api_key_mask ?? "sin key"}</span>
        </div>
        {(byo.rate_limit_rpm != null || byo.daily_token_limit != null) ? (
          <div className="mt-1 text-[var(--color-tertiary)]">
            Límites:{" "}
            {byo.rate_limit_rpm != null
              ? `${byo.rate_limit_rpm} RPM`
              : "RPM —"}{" "}
            ·{" "}
            {byo.daily_token_limit != null
              ? `${byo.daily_token_limit.toLocaleString()} tokens/día`
              : "tokens/día —"}
          </div>
        ) : null}
        {byo.last_test_status ? (
          <div className="mt-1 text-[var(--color-tertiary)]">
            Último test:{" "}
            {byo.last_test_status === "ok" ? "OK" : "FAIL"} ·{" "}
            {byo.last_test_at
              ? new Date(byo.last_test_at).toLocaleString()
              : "—"}
          </div>
        ) : (
          <div className="mt-1 text-[var(--color-tertiary)]">
            Sin probar todavía.
          </div>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            onClick={retest}
            loading={retesting}
          >
            Probar conexión
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setEditing(true)}
          >
            Editar
          </Button>
        </div>
      </div>
    </div>
  );
}

function ActiveConnectionEditForm({
  byo,
  onCancel,
  onSaved,
}: {
  byo: NonNullable<TenantAIProviderRead["byo"]>;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const isAzure = byo.provider === "azure";
  const isCustom = byo.provider === "custom";
  const [model, setModel] = useState(byo.model ?? "");
  const [baseUrl, setBaseUrl] = useState(byo.base_url ?? "");
  const [deploymentName, setDeploymentName] = useState(byo.deployment_name ?? "");
  const [apiVersion, setApiVersion] = useState(byo.api_version ?? "");
  const [rateLimitRpm, setRateLimitRpm] = useState(
    byo.rate_limit_rpm != null ? String(byo.rate_limit_rpm) : "",
  );
  const [dailyTokenLimit, setDailyTokenLimit] = useState(
    byo.daily_token_limit != null ? String(byo.daily_token_limit) : "",
  );
  const [acknowledgeSecurity, setAcknowledgeSecurity] = useState(
    !!byo.acknowledge_security,
  );
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const rpmTrim = rateLimitRpm.trim();
    const tokTrim = dailyTokenLimit.trim();
    try {
      await updateTenantAIProvider({
        mode: "byo",
        byo: {
          provider: byo.provider as BYOProvider,
          api_key: apiKey.trim() ? apiKey : null,
          model: model.trim() || null,
          base_url: baseUrl.trim() || null,
          deployment_name: isAzure
            ? (deploymentName.trim() || null)
            : null,
          api_version: isAzure ? (apiVersion.trim() || null) : null,
          rate_limit_rpm: rpmTrim ? Number(rpmTrim) : null,
          daily_token_limit: tokTrim ? Number(tokTrim) : null,
          acknowledge_security: isCustom ? acknowledgeSecurity : null,
        },
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={save}
      className="mt-3 space-y-3 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3 text-[12px]"
    >
      <div className="font-medium text-[var(--color-primary)]">
        Editar conexión · {byo.provider}
      </div>
      <div>
        <label
          htmlFor="edit-model"
          className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
        >
          Modelo
        </label>
        <Input
          id="edit-model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="Ej. gpt-4o-mini"
        />
      </div>
      <div>
        <label
          htmlFor="edit-url"
          className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
        >
          {isAzure ? "Resource endpoint" : "Base URL"}
        </label>
        <Input
          id="edit-url"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api..."
        />
      </div>
      {isAzure ? (
        <>
          <div>
            <label
              htmlFor="edit-deployment"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Deployment name
            </label>
            <Input
              id="edit-deployment"
              value={deploymentName}
              onChange={(e) => setDeploymentName(e.target.value)}
            />
          </div>
          <div>
            <label
              htmlFor="edit-api-version"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              API version
            </label>
            <Input
              id="edit-api-version"
              value={apiVersion}
              onChange={(e) => setApiVersion(e.target.value)}
              placeholder="2024-02-15-preview"
            />
          </div>
        </>
      ) : null}
      <div>
        <label
          htmlFor="edit-key"
          className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
        >
          API key
        </label>
        <Input
          id="edit-key"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={byo.api_key_mask ?? "Pega una nueva key"}
          autoComplete="off"
        />
        <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
          Déjalo vacío para conservar la key actual.
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <label
            htmlFor="edit-rpm"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Rate limit (RPM)
          </label>
          <Input
            id="edit-rpm"
            type="number"
            min={1}
            value={rateLimitRpm}
            onChange={(e) => setRateLimitRpm(e.target.value)}
            placeholder="—"
          />
        </div>
        <div>
          <label
            htmlFor="edit-tokens"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Tope tokens diarios
          </label>
          <Input
            id="edit-tokens"
            type="number"
            min={100}
            value={dailyTokenLimit}
            onChange={(e) => setDailyTokenLimit(e.target.value)}
            placeholder="—"
          />
        </div>
      </div>
      {isCustom ? (
        <label className="flex items-start gap-2 text-[12px]">
          <input
            type="checkbox"
            checked={acknowledgeSecurity}
            onChange={(e) => setAcknowledgeSecurity(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            Confirmo que mi tenant es responsable de la seguridad y
            cumplimiento del proveedor custom.
          </span>
        </label>
      ) : null}
      {error ? <Banner variant="danger">{error}</Banner> : null}
      <p className="text-[11px] text-[var(--color-tertiary)]">
        Al guardar se prueba la conexión con los nuevos valores. Si falla,
        la config previa se conserva.
      </p>
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onCancel}
          disabled={saving}
        >
          Cancelar
        </Button>
        <Button type="submit" size="sm" loading={saving}>
          Guardar y probar
        </Button>
      </div>
    </form>
  );
}

function ProviderCard({
  info,
  connected,
  testStatus,
  disabled,
  onClick,
}: {
  info: BYOProviderInfo;
  connected: boolean;
  testStatus: "ok" | "fail" | null;
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
        {connected && testStatus === "fail" ? (
          <Badge variant="danger">Última prueba falló</Badge>
        ) : connected && testStatus === "ok" ? (
          <Badge variant="success">
            <Check className="mr-1 h-3 w-3" aria-hidden />
            Conectado
          </Badge>
        ) : connected ? (
          <Badge variant="warning">Sin probar</Badge>
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
  const [deploymentName, setDeploymentName] = useState("");
  const [apiVersion, setApiVersion] = useState(
    provider.requires_azure_fields ? "2024-02-15-preview" : "",
  );
  const [rateLimitRpm, setRateLimitRpm] = useState<string>("");
  const [dailyTokenLimit, setDailyTokenLimit] = useState<string>("");
  const [acknowledgeSecurity, setAcknowledgeSecurity] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<
    | { ok: boolean; latency_ms: number | null; error: string | null }
    | null
  >(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildPayload() {
    const base = {
      provider: provider.key,
      api_key: apiKey,
      model: model || null,
      base_url: baseUrl || null,
    } as const;
    const extra: Record<string, unknown> = {};
    if (provider.requires_azure_fields) {
      extra.deployment_name = deploymentName || null;
      extra.api_version = apiVersion || null;
    }
    const rpm = rateLimitRpm.trim();
    if (rpm) extra.rate_limit_rpm = Number(rpm);
    const dt = dailyTokenLimit.trim();
    if (dt) extra.daily_token_limit = Number(dt);
    if (provider.requires_security_ack) {
      extra.acknowledge_security = acknowledgeSecurity;
    }
    return { ...base, ...extra };
  }

  async function runTest() {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const r = await testTenantAIProvider({ byo: buildPayload() });
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
      await updateTenantAIProvider({ mode: "byo", byo: buildPayload() });
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
          deploymentName={deploymentName}
          setDeploymentName={setDeploymentName}
          apiVersion={apiVersion}
          setApiVersion={setApiVersion}
          rateLimitRpm={rateLimitRpm}
          setRateLimitRpm={setRateLimitRpm}
          dailyTokenLimit={dailyTokenLimit}
          setDailyTokenLimit={setDailyTokenLimit}
          acknowledgeSecurity={acknowledgeSecurity}
          setAcknowledgeSecurity={setAcknowledgeSecurity}
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
  deploymentName,
  setDeploymentName,
  apiVersion,
  setApiVersion,
  rateLimitRpm,
  setRateLimitRpm,
  dailyTokenLimit,
  setDailyTokenLimit,
  acknowledgeSecurity,
  setAcknowledgeSecurity,
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
  deploymentName: string;
  setDeploymentName: (s: string) => void;
  apiVersion: string;
  setApiVersion: (s: string) => void;
  rateLimitRpm: string;
  setRateLimitRpm: (s: string) => void;
  dailyTokenLimit: string;
  setDailyTokenLimit: (s: string) => void;
  acknowledgeSecurity: boolean;
  setAcknowledgeSecurity: (v: boolean) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const baseUrlReady = !info.requires_base_url || baseUrl.trim().length > 0;
  const azureReady =
    !info.requires_azure_fields || deploymentName.trim().length > 0;
  const ackReady = !info.requires_security_ack || acknowledgeSecurity;
  const canAdvance =
    apiKey.trim().length > 5 && baseUrlReady && azureReady && ackReady;
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
          {info.requires_azure_fields ? "Modelo (opcional · informativo)" : "Modelo"}
        </label>
        <Input
          id="wiz-model"
          list="wiz-model-suggestions"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder={
            info.requires_azure_fields ? "Ej. gpt-4o" : "Ej. gpt-4o-mini"
          }
        />
        <datalist id="wiz-model-suggestions">
          {info.suggested_models.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
        {info.requires_azure_fields ? (
          <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
            Azure usa el deployment server-side; el campo "modelo" es solo
            referencia para tu equipo.
          </p>
        ) : null}
      </div>
      {info.requires_base_url ? (
        <div>
          <label
            htmlFor="wiz-url"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            {info.requires_azure_fields
              ? "Resource endpoint"
              : "Base URL"}
          </label>
          <Input
            id="wiz-url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={info.base_url_hint ?? "https://api..."}
          />
          {info.requires_azure_fields ? (
            <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
              Lo encuentras en Azure Portal → tu recurso OpenAI →
              "Keys and Endpoint".
            </p>
          ) : null}
        </div>
      ) : null}
      {info.requires_azure_fields ? (
        <>
          <div>
            <label
              htmlFor="wiz-deployment"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Deployment name
            </label>
            <Input
              id="wiz-deployment"
              value={deploymentName}
              onChange={(e) => setDeploymentName(e.target.value)}
              placeholder="Ej. gpt-4o-prod"
            />
            <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
              Azure Portal → tu recurso → "Model deployments".
            </p>
          </div>
          <div>
            <label
              htmlFor="wiz-api-version"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              API version
            </label>
            <Input
              id="wiz-api-version"
              value={apiVersion}
              onChange={(e) => setApiVersion(e.target.value)}
              placeholder="2024-02-15-preview"
            />
          </div>
        </>
      ) : null}
      {info.requires_security_ack && info.security_warning ? (
        <Banner variant="warning">
          <p className="font-medium">Aviso de seguridad</p>
          <p className="mt-1 text-[12px]">{info.security_warning}</p>
          <label className="mt-2 flex items-start gap-2 text-[12px]">
            <input
              type="checkbox"
              checked={acknowledgeSecurity}
              onChange={(e) => setAcknowledgeSecurity(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              Confirmo que mi tenant es responsable de la seguridad y
              cumplimiento del proveedor elegido.
            </span>
          </label>
        </Banner>
      ) : null}
      <details className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3 text-[12px]">
        <summary className="cursor-pointer font-medium text-[var(--color-secondary)]">
          Límites de uso (opcional)
        </summary>
        <div className="mt-2 space-y-2">
          <div>
            <label
              htmlFor="wiz-rpm"
              className="mb-1 block text-[12px] text-[var(--color-secondary)]"
            >
              Rate limit (requests por minuto)
            </label>
            <Input
              id="wiz-rpm"
              type="number"
              min={1}
              value={rateLimitRpm}
              onChange={(e) => setRateLimitRpm(e.target.value)}
              placeholder="60"
            />
          </div>
          <div>
            <label
              htmlFor="wiz-tokens"
              className="mb-1 block text-[12px] text-[var(--color-secondary)]"
            >
              Tope de tokens diarios
            </label>
            <Input
              id="wiz-tokens"
              type="number"
              min={100}
              value={dailyTokenLimit}
              onChange={(e) => setDailyTokenLimit(e.target.value)}
              placeholder="500000"
            />
          </div>
          <p className="text-[11px] text-[var(--color-tertiary)]">
            Los límites se almacenan junto con la config para que el
            worker los respete (CA4 US-110). Déjalos vacíos para no
            aplicar tope.
          </p>
        </div>
      </details>
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
      {info.api_keys_url ? (
        <a
          href={info.api_keys_url}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
        >
          Generar API key
          <ExternalLink className="h-3 w-3" aria-hidden />
        </a>
      ) : null}
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
