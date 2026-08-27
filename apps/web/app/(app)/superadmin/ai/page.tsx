"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getGroqUsage,
  getPlatformAIDefaults,
  listTenantsAIStatus,
  pingGroq,
  updatePlatformAIDefaults,
  type GroqUsageSummary,
  type PlatformAIDefaultsPatch,
  type PlatformAIDefaultsRead,
  type TenantAIStatusRow,
} from "@/lib/api/superadmin-ai";
import { getStoredUser } from "@/lib/auth-storage";

/**
 * Config de AI a nivel de plataforma (US-054, US-057, BUG-053).
 *
 * El superadmin configura Groq como IA base. Los tenants que necesitan
 * un proveedor propio lo configuran como BYO en /admin/ai.
 *
 * Orden de prioridad: tenant override (admin) > platform defaults (esta
 * página) > env var.
 */
export default function SuperadminAIPage() {
  const user = getStoredUser();
  const [data, setData] = useState<PlatformAIDefaultsRead | null>(null);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(data);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // US-057: Groq config
  const [groqKey, setGroqKey] = useState("");
  const [groqKeyDirty, setGroqKeyDirty] = useState(false);
  const [groqModel, setGroqModel] = useState("");
  const [groqPingResult, setGroqPingResult] = useState<
    | { ok: boolean; latency_ms: number | null; error: string | null }
    | null
  >(null);
  const [groqPinging, setGroqPinging] = useState(false);

  // US-057: panel de tenants + dashboard de uso.
  const [tenants, setTenants] = useState<TenantAIStatusRow[]>([]);
  const [usage, setUsage] = useState<GroqUsageSummary | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [d, t, u] = await Promise.all([
        getPlatformAIDefaults(),
        listTenantsAIStatus().catch(() => [] as TenantAIStatusRow[]),
        getGroqUsage(30).catch(() => null),
      ]);
      setData(d);
      setGroqModel(d.groq_model ?? "");
      setGroqKey("");
      setGroqKeyDirty(false);
      setTenants(t);
      setUsage(u);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la config");
    } finally {
      setLoading(false);
    }
  }

  async function runGroqPing() {
    setGroqPinging(true);
    setGroqPingResult(null);
    try {
      const r = await pingGroq();
      setGroqPingResult({
        ok: r.ok,
        latency_ms: r.latency_ms,
        error: r.error,
      });
    } catch (err) {
      setGroqPingResult({
        ok: false,
        latency_ms: null,
        error: err instanceof ApiError ? err.message : "Error al probar Groq",
      });
    } finally {
      setGroqPinging(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  if (user && !user.is_superadmin) {
    return (
      <div>
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
        groq_model: groqModel.trim() === "" ? null : groqModel.trim(),
      };
      if (groqKeyDirty) {
        body.groq_api_key = groqKey; // vacío = borrar
      }
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
    <div className="space-y-5">
      <header className="flex flex-col gap-1">
        <h1 className="flex items-center gap-2 text-[24px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          <Icono nombre="info" size={20} className="text-[var(--color-accent)]" />
          IA · Defaults de plataforma
        </h1>
        {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Se aplican a todos los tenants que no tengan override propio.
          Cambian sin redeploy; entran en vigor en el próximo task del worker.
        </p>
      </header>

      {loading || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          {error ? <Banner variant="danger">{error}</Banner> : null}
          {notice ? <Banner variant="success">{notice}</Banner> : null}

          <form
            onSubmit={save}
            className="space-y-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]"
          >
            <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
              IA base de la plataforma (Groq)
            </h2>
            <p className="text-[12px] text-[var(--text-tertiary)]">
              Los tenants que elijan modo "platform" usan esta config.
            </p>

            {/* US-057: Groq como IA base de la plataforma */}
            <div className="mt-2 space-y-3 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-4">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
                  IA base (Groq) — modo "platform" de los tenants
                </h3>
                {data.groq_configured ? (
                  <Badge variant="success">Configurado</Badge>
                ) : (
                  <Badge variant="warning">Sin configurar</Badge>
                )}
              </div>
              <Field
                label="GROQ_API_KEY"
                hint={
                  data.groq_api_key_mask
                    ? `Actual: ${data.groq_api_key_mask}. Dejar vacío = conservar.`
                    : "Pegar la API key generada en console.groq.com."
                }
              >
                <PasswordInput
                  value={groqKey}
                  onChange={(e) => {
                    setGroqKey(e.target.value);
                    setGroqKeyDirty(true);
                  }}
                  placeholder={
                    data.groq_api_key_mask
                      ? "••••••••"
                      : "gsk_..."
                  }
                  autoComplete="off"
                />
              </Field>
              <Field
                label="Modelo Groq"
                hint="Por defecto: llama-3.3-70b-versatile (free tier). 3.1 fue deprecado por Groq."
              >
                <Input
                  value={groqModel}
                  onChange={(e) => setGroqModel(e.target.value)}
                  placeholder="llama-3.3-70b-versatile"
                />
              </Field>
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={runGroqPing}
                  loading={groqPinging}
                >
                  Probar conexión
                </Button>
                {groqPingResult ? (
                  <span className="inline-flex items-center gap-1.5 text-[13px]">
                    {groqPingResult.ok ? (
                      <>
                        <Icono
                          nombre="circle-check"
                          size={15}
                          className="text-[var(--color-success-fg)]"
                        />
                        <span className="text-[var(--color-success-fg)]">
                          OK
                          {groqPingResult.latency_ms !== null
                            ? ` · ${groqPingResult.latency_ms} ms`
                            : ""}
                        </span>
                      </>
                    ) : (
                      <>
                        <Icono
                          nombre="circle-x"
                          size={15}
                          className="text-[var(--color-danger-fg)]"
                        />
                        <span className="text-[var(--color-danger-fg)]">
                          {groqPingResult.error ?? "Falló"}
                        </span>
                      </>
                    )}
                  </span>
                ) : null}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <Button type="submit" loading={saving}>
                Guardar defaults
              </Button>
            </div>
          </form>

          {/* US-057: panel de status por tenant */}
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
            <h2 className="mb-3 text-[13px] font-semibold text-[var(--text-primary)]">
              Tenants · Estado de IA
            </h2>
            {tenants.length === 0 ? (
              <p className="text-[13px] text-[var(--text-tertiary)]">
                No hay tenants registrados.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-[13px]">
                  <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)] shadow-[var(--linea-surco)]">
                    <tr>
                      <th className="h-8.5 px-3 font-medium">Tenant</th>
                      <th className="h-8.5 px-3 font-medium">Modo</th>
                      <th className="h-8.5 px-3 font-medium">Proveedor</th>
                      <th className="h-8.5 px-3 font-medium">Modelo</th>
                      <th className="h-8.5 px-3 font-medium">API key</th>
                      <th className="h-8.5 px-3 font-medium">Último test</th>
                      <th className="h-8.5 px-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tenants.map((t) => (
                      <tr
                        key={t.tenant_id}
                        className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]"
                      >
                        <td className="px-3 py-2">
                          <div className="overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)]">
                            {t.tenant_name}
                          </div>
                          <div className="text-[11px] tracking-[0.01em] text-[var(--text-tertiary)]">
                            {t.tenant_slug}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          {t.mode === "disabled" ? (
                            <Badge variant="neutral">Sin IA</Badge>
                          ) : t.mode === "platform" ? (
                            <Badge variant="info">Plataforma</Badge>
                          ) : (
                            <Badge variant="success">BYO</Badge>
                          )}
                        </td>
                        <td className="px-3 py-2 text-[var(--text-secondary)]">
                          {t.byo_provider ?? (t.mode === "platform" ? "groq" : "—")}
                        </td>
                        <td className="px-3 py-2 text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                          {t.byo_model ?? (t.mode === "platform" ? data.groq_model ?? "—" : "—")}
                        </td>
                        <td className="px-3 py-2 text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                          {t.byo_api_key_mask ?? "—"}
                        </td>
                        <td className="px-3 py-2 font-mono text-[11px] text-[var(--text-tertiary)]">
                          {t.last_test_at
                            ? new Date(t.last_test_at).toLocaleString("es-MX")
                            : "—"}
                        </td>
                        <td className="px-3 py-2">
                          {t.last_test_status === "ok" ? (
                            <Badge variant="success">
                              <Icono nombre="circle-check" size={12} />
                              OK
                            </Badge>
                          ) : t.last_test_status === "fail" ? (
                            <Badge variant="danger" title={t.last_test_error ?? undefined}>
                              <Icono nombre="circle-x" size={12} />
                              FAIL
                            </Badge>
                          ) : (
                            <span className="text-[var(--text-faint)]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* US-057: dashboard de uso Groq */}
          {usage ? (
            <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
              <h2 className="mb-3 text-[13px] font-semibold text-[var(--text-primary)]">
                Uso de Groq (últimos {usage.days} días)
              </h2>
              <div className="grid gap-3 sm:grid-cols-4">
                <UsageStat
                  label="Requests hoy"
                  value={usage.today_requests}
                  limit={usage.limit_requests_per_day}
                />
                <UsageStat
                  label="Tokens hoy"
                  value={usage.today_tokens}
                  limit={usage.limit_tokens_per_day}
                />
                <UsageStat
                  label={`Requests ${usage.days}d`}
                  value={usage.total_requests}
                />
                <UsageStat
                  label={`Tokens ${usage.days}d`}
                  value={usage.total_tokens}
                />
              </div>

              {usage.total_failed > 0 ? (
                <div className="mt-3 inline-flex items-center gap-1.5 text-[12px] text-[var(--color-warning-fg)]">
                  <Icono nombre="triangle-alert" size={14} />
                  {usage.total_failed} jobs fallidos en la ventana (revisa
                  rate limits y status de Groq).
                </div>
              ) : null}

              {usage.by_day.length > 0 ? (
                <div className="mt-4">
                  <h3 className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                    Requests por día
                  </h3>
                  <MiniBarChart
                    buckets={usage.by_day.map((b) => ({
                      label: b.date.slice(5),
                      value: b.requests,
                    }))}
                  />
                </div>
              ) : null}

              {usage.top_tenants.length > 0 ? (
                <div className="mt-4 overflow-x-auto">
                  <h3 className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                    Top tenants
                  </h3>
                  <table className="w-full text-[13px]">
                    <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)] shadow-[var(--linea-surco)]">
                      <tr>
                        <th className="h-8.5 px-3 font-medium">Tenant</th>
                        <th className="h-8.5 px-3 pr-3.5 text-right font-medium">Requests</th>
                        <th className="h-8.5 px-3 pr-3.5 text-right font-medium">Tokens in</th>
                        <th className="h-8.5 px-3 pr-3.5 text-right font-medium">Tokens out</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usage.top_tenants.map((r) => (
                        <tr
                          key={r.tenant_id}
                          className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]"
                        >
                          <td className="overflow-hidden text-ellipsis whitespace-nowrap px-3 py-2 text-[var(--text-secondary)]">
                            {r.tenant_name}
                          </td>
                          <td className="px-3 py-2 pr-3.5 text-right font-mono tabular-nums text-[var(--text-secondary)]">
                            {r.requests}
                          </td>
                          <td className="px-3 py-2 pr-3.5 text-right font-mono tabular-nums text-[var(--text-secondary)]">
                            {r.tokens_in}
                          </td>
                          <td className="px-3 py-2 pr-3.5 text-right font-mono tabular-nums text-[var(--text-secondary)]">
                            {r.tokens_out}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </section>
          ) : null}

          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)] text-[13px] text-[var(--text-secondary)]">
            <h2 className="mb-2 text-[13px] font-semibold text-[var(--text-primary)]">
              Estado de secrets (env)
            </h2>
            <p className="mb-3 text-[12px] text-[var(--text-tertiary)]">
              Fallback de sólo-lectura. La fuente de verdad de Groq es la
              config editable arriba (cifrada con Fernet). Los secrets de
              Gemini/Anthropic ya no son editables desde esta UI — viven
              en env y sólo se muestran aquí para diagnóstico.
            </p>
            <dl className="grid grid-cols-[200px_1fr] gap-x-4 gap-y-1.5 font-mono text-[12px]">
              <dt className="text-[var(--text-tertiary)]">GROQ_API_KEY (env fallback)</dt>
              <dd>{data.env.groq_configured ? "configurado" : "vacío"}</dd>
              <dt className="text-[var(--text-tertiary)]">GEMINI_API_KEY (legacy)</dt>
              <dd>{data.env.gemini_configured ? "configurado" : "vacío"}</dd>
              <dt className="text-[var(--text-tertiary)]">ANTHROPIC_API_KEY (legacy)</dt>
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

function UsageStat({
  label,
  value,
  limit,
}: {
  label: string;
  value: number;
  limit?: number;
}) {
  const pct = limit ? Math.min(100, (value / limit) * 100) : 0;
  const danger = limit && pct >= 90;
  const warn = limit && pct >= 70 && !danger;
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3">
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
        {label}
      </div>
      <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-[var(--text-primary)]">
        {value.toLocaleString()}
      </div>
      {limit ? (
        <>
          <div className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
            {Math.round(pct)}% de {limit.toLocaleString()}
          </div>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--border-subtle)] shadow-[var(--hundido)]">
            <div
              className={
                danger
                  ? "h-full bg-[var(--color-danger-fg)]"
                  : warn
                    ? "h-full bg-[var(--color-warning-fg)]"
                    : "h-full bg-[var(--color-accent)]"
              }
              style={{ width: `${pct}%` }}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

function MiniBarChart({
  buckets,
}: {
  buckets: Array<{ label: string; value: number }>;
}) {
  const max = Math.max(1, ...buckets.map((b) => b.value));
  return (
    <div className="flex items-end gap-1 overflow-x-auto">
      {buckets.map((b, i) => {
        const h = Math.max(4, (b.value / max) * 60);
        return (
          <div
            key={`${b.label}-${i}`}
            className="flex flex-col items-center gap-1"
            title={`${b.label}: ${b.value}`}
          >
            <div
              className="w-4 rounded-sm bg-[var(--color-accent)]"
              style={{ height: `${h}px` }}
            />
            <span className="text-[9px] text-[var(--color-tertiary)]">
              {b.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
