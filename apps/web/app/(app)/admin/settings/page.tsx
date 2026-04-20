"use client";

import { useEffect, useState } from "react";
import { Cog, Palette } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getSettings,
  updateSettings,
  type TenantSettings,
} from "@/lib/api/admin-panel";

const LOCALES = [
  { value: "es-MX", label: "Español (MX)" },
  { value: "en-US", label: "English (US)" },
];
const CURRENCIES = ["MXN", "USD", "EUR"];
const DATE_FORMATS = [
  { value: "DD/MM/YYYY", label: "DD/MM/YYYY" },
  { value: "MM/DD/YYYY", label: "MM/DD/YYYY" },
  { value: "YYYY-MM-DD", label: "YYYY-MM-DD" },
];
const TIMEZONES = [
  "America/Mexico_City",
  "America/Monterrey",
  "America/New_York",
  "America/Los_Angeles",
  "Europe/Madrid",
  "UTC",
];
const AI_MODES: Array<{ value: NonNullable<TenantSettings["ai_mode"]>; label: string }> = [
  { value: "ollama", label: "Ollama (local)" },
  { value: "claude", label: "Claude" },
  { value: "disabled", label: "Desactivado" },
];

export default function SettingsPage() {
  const [initial, setInitial] = useState<TenantSettings | null>(null);
  const [form, setForm] = useState<TenantSettings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((r) => {
        setInitial(r.settings);
        setForm(r.settings);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar la configuración");
      })
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      const r = await updateSettings(form);
      setInitial(r.settings);
      setForm(r.settings);
      setNotice("Configuración actualizada");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  const dirty = JSON.stringify(initial ?? {}) !== JSON.stringify(form);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="flex items-center gap-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--text-secondary)]">
          <Cog className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Configuración del tenant
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Preferencias globales de la organización: idioma, moneda, timezone, color corporativo
            y proveedor de IA.
          </p>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="space-y-5 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Idioma default">
            <Select
              value={form.locale ?? ""}
              onChange={(e) => setForm({ ...form, locale: e.target.value || undefined })}
            >
              <option value="">Sin definir</option>
              {LOCALES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Moneda default">
            <Select
              value={form.currency ?? ""}
              onChange={(e) => setForm({ ...form, currency: e.target.value || undefined })}
            >
              <option value="">Sin definir</option>
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Formato de fecha">
            <Select
              value={form.date_format ?? ""}
              onChange={(e) => setForm({ ...form, date_format: e.target.value || undefined })}
            >
              <option value="">Sin definir</option>
              {DATE_FORMATS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Timezone">
            <Select
              value={form.timezone ?? ""}
              onChange={(e) => setForm({ ...form, timezone: e.target.value || undefined })}
            >
              <option value="">Sin definir</option>
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Modo IA">
            <Select
              value={form.ai_mode ?? ""}
              onChange={(e) =>
                setForm({ ...form, ai_mode: (e.target.value as TenantSettings["ai_mode"]) || undefined })
              }
            >
              <option value="">Sin definir</option>
              {AI_MODES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Logo URL">
            <Input
              type="url"
              placeholder="https://…/logo.png"
              value={form.logo_url ?? ""}
              onChange={(e) => setForm({ ...form, logo_url: e.target.value || undefined })}
            />
          </Field>
        </div>

        <Field label="Color corporativo">
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={form.primary_color ?? "#1f2937"}
              onChange={(e) => setForm({ ...form, primary_color: e.target.value })}
              className="h-10 w-16 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)]"
              aria-label="Color primario"
            />
            <Input
              value={form.primary_color ?? ""}
              onChange={(e) => setForm({ ...form, primary_color: e.target.value || undefined })}
              placeholder="#1f2937"
            />
            <span className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 text-[12px] text-[var(--text-secondary)]">
              <Palette className="h-3.5 w-3.5" aria-hidden />
              Se aplica a PDFs exportados
            </span>
          </div>
        </Field>

        <div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
          <Button
            variant="secondary"
            onClick={() => (initial ? setForm(initial) : null)}
            disabled={!dirty || saving}
          >
            Descartar cambios
          </Button>
          <Button onClick={save} loading={saving} disabled={!dirty}>
            Guardar configuración
          </Button>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[12px] font-medium text-[var(--text-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
