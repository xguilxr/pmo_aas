"use client";

import { useEffect, useState } from "react";
import { Palette } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getSettings,
  updateSettings,
  type ProgressCalculationMethod,
  type TaskLoadThresholds,
  type TenantSettings,
} from "@/lib/api/admin-panel";

// ENH-098: progress calculation method options (Report Builder / EP020).
const PROGRESS_CALC_METHODS: { value: ProgressCalculationMethod; label: string }[] = [
  { value: "by_task_count", label: "Por conteo de tareas" },
  { value: "by_duration", label: "Por duración" },
  { value: "by_effort", label: "Por esfuerzo" },
];

// ENH-099: defaults shown when the tenant has no thresholds configured.
const DEFAULT_TASK_LOAD_THRESHOLDS: TaskLoadThresholds = {
  green_max: 5,
  amber_max: 10,
};

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

export function TenantSettingsForm() {
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
    return <Skeleton className="h-80 w-full" />;
  }

  return (
    <div className="space-y-5">
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

        {/* ENH-098 — Cálculo de avance (Report Builder / EP020) */}
        <div className="border-t border-[var(--border-subtle)] pt-4">
          <h3 className="mb-2 text-[13px] font-semibold text-[var(--text-primary)]">
            Cálculo de avance
          </h3>
          <p className="mb-3 text-[12px] text-[var(--text-tertiary)]">
            Método usado para calcular el % de avance de los proyectos en los
            reportes generados por el Report Builder.
          </p>
          <Field label="Método de cálculo">
            <Select
              value={form.progress_calculation_method ?? "by_task_count"}
              onChange={(e) =>
                setForm({
                  ...form,
                  progress_calculation_method:
                    (e.target.value as ProgressCalculationMethod) ||
                    undefined,
                })
              }
            >
              {PROGRESS_CALC_METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        {/* ENH-099 — Umbrales de carga de tareas (Report Builder / EP020) */}
        <div className="border-t border-[var(--border-subtle)] pt-4">
          <h3 className="mb-2 text-[13px] font-semibold text-[var(--text-primary)]">
            Umbrales de carga de tareas
          </h3>
          <p className="mb-3 text-[12px] text-[var(--text-tertiary)]">
            Define los cortes para colorear la carga de tareas por recurso en
            los reportes: hasta <em>verde</em>, hasta <em>ámbar</em>, y por
            encima se marca en rojo. Ambos valores deben ser positivos y
            <span className="whitespace-nowrap"> verde &lt; ámbar</span>.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Verde hasta">
              <Input
                type="number"
                min={1}
                step={1}
                value={
                  form.task_load_thresholds?.green_max ??
                  DEFAULT_TASK_LOAD_THRESHOLDS.green_max
                }
                onChange={(e) => {
                  const next = Number(e.target.value);
                  const current =
                    form.task_load_thresholds ?? DEFAULT_TASK_LOAD_THRESHOLDS;
                  setForm({
                    ...form,
                    task_load_thresholds: {
                      green_max: Number.isFinite(next) ? next : current.green_max,
                      amber_max: current.amber_max,
                    },
                  });
                }}
              />
            </Field>
            <Field label="Ámbar hasta">
              <Input
                type="number"
                min={1}
                step={1}
                value={
                  form.task_load_thresholds?.amber_max ??
                  DEFAULT_TASK_LOAD_THRESHOLDS.amber_max
                }
                onChange={(e) => {
                  const next = Number(e.target.value);
                  const current =
                    form.task_load_thresholds ?? DEFAULT_TASK_LOAD_THRESHOLDS;
                  setForm({
                    ...form,
                    task_load_thresholds: {
                      green_max: current.green_max,
                      amber_max: Number.isFinite(next) ? next : current.amber_max,
                    },
                  });
                }}
              />
            </Field>
          </div>
        </div>

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
