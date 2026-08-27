"use client";

import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/api";
import {
  NOTIFICATION_TYPE_LABEL,
  getPreferences,
  updatePreferences,
  type NotificationPreferences,
} from "@/lib/api/notifications";

// Orden y tipos que exponemos al usuario. Coinciden con EMAIL_BY_DEFAULT
// en services/notifications.py del backend.
const TYPES = [
  "request_approved",
  "request_rejected",
  "request_needs_info",
  "pm_assigned",
  "aid_overdue",
  "risk_high",
  "change_pending",
  "minute_generated",
  "report_sent",
] as const;

type TypeChoice = "email_and_inapp" | "inapp_only";

export function NotificationPreferencesSection() {
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPreferences()
      .then((p) => {
        if (!cancelled) setPrefs(p);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Error al cargar preferencias");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function typeValue(t: string): TypeChoice {
    if (!prefs) return "email_and_inapp";
    return (prefs.by_type[t] as TypeChoice) ?? "email_and_inapp";
  }

  async function save(patch: Partial<NotificationPreferences>) {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePreferences(patch);
      setPrefs(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
      <header className="mb-4 flex items-center gap-2">
        <Icono nombre="bell" size={20} className="text-[var(--color-tertiary)]" />
        <h2 className="text-lg font-semibold text-[var(--color-primary)]">
          Notificaciones
        </h2>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading || !prefs ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 px-4 py-3">
            <div>
              <div className="text-sm font-medium text-[var(--color-primary)]">
                Enviar correos electrónicos
              </div>
              <p className="text-xs text-[var(--color-tertiary)]">
                Kill-switch global. Si lo apagas, solo recibes notificaciones
                in-app sin importar los overrides por tipo.
              </p>
            </div>
            <Switch
              checked={prefs.email_enabled}
              onChange={(v) => save({ email_enabled: v })}
              disabled={saving}
            />
          </div>

          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
              Por tipo de evento
            </div>
            <ul className="divide-y divide-[var(--border-subtle)] rounded-[var(--radius-md)] border border-[var(--border-subtle)]">
              {TYPES.map((t) => {
                const choice = typeValue(t);
                const sendsEmail = choice === "email_and_inapp";
                return (
                  <li
                    key={t}
                    className="flex items-center justify-between px-4 py-2.5 text-sm"
                  >
                    <span className="text-[var(--color-primary)]">
                      {NOTIFICATION_TYPE_LABEL[t] ?? t}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-[var(--color-tertiary)]">
                        {sendsEmail ? "Email + in-app" : "Solo in-app"}
                      </span>
                      <Switch
                        checked={sendsEmail}
                        onChange={(v) =>
                          save({
                            by_type: {
                              [t]: v ? "email_and_inapp" : "inapp_only",
                            },
                          })
                        }
                        disabled={saving || !prefs.email_enabled}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          {saved ? (
            <div className="inline-flex items-center gap-1 text-xs text-[var(--color-success-fg)]">
              <Icono nombre="check" size={14} /> Guardado
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
