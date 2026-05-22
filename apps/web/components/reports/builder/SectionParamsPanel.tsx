"use client";

import { useMemo } from "react";

import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ReportSection } from "@/lib/api/report-builder";

export type SectionParams = Record<string, unknown>;

type Props = {
  section: ReportSection | null;
  params: SectionParams;
  onChange: (next: SectionParams) => void;
};

/**
 * US-125 — Panel de parámetros transversales.
 *
 * El form se construye dinámicamente leyendo `section.parameters_schema`
 * (informal JSON Schema-like) y completándolo con los parámetros
 * transversales aplicables (área, ventana, top N, modo, orden, agrupación)
 * según el `applies_to` declarado en cada section.
 */
const TRANSVERSAL_FIELDS = [
  { key: "area_id", label: "Área", type: "text", placeholder: "Todas si vacío" },
  { key: "window_days", label: "Ventana (días)", type: "number", min: 1, max: 365 },
  { key: "top_n", label: "Top N", type: "number", min: 1, max: 100 },
  {
    key: "mode",
    label: "Modo",
    type: "select",
    options: [
      { value: "", label: "—" },
      { value: "summary", label: "Resumen" },
      { value: "detail", label: "Detalle" },
    ],
  },
  {
    key: "order_by",
    label: "Ordenamiento",
    type: "select",
    options: [
      { value: "", label: "—" },
      { value: "date_asc", label: "Fecha ↑" },
      { value: "date_desc", label: "Fecha ↓" },
      { value: "severity_desc", label: "Severidad ↓" },
      { value: "area", label: "Área" },
    ],
  },
  {
    key: "group_by",
    label: "Agrupación",
    type: "select",
    options: [
      { value: "", label: "—" },
      { value: "area", label: "Por área" },
      { value: "owner", label: "Por responsable" },
      { value: "type", label: "Por tipo" },
    ],
  },
] as const;

export function SectionParamsPanel({ section, params, onChange }: Props) {
  const schema = useMemo<Record<string, unknown>>(
    () => (section?.parameters_schema as Record<string, unknown>) ?? {},
    [section]
  );

  function update(key: string, value: unknown) {
    if (value === "" || value === undefined || value === null) {
      const next = { ...params };
      delete next[key];
      onChange(next);
      return;
    }
    onChange({ ...params, [key]: value });
  }

  function validate(key: string, raw: string, min?: number, max?: number): number | "" {
    if (raw === "") return "";
    const n = Number(raw);
    if (Number.isNaN(n)) return "";
    if (min !== undefined && n < min) return min;
    if (max !== undefined && n > max) return max;
    return n;
  }

  if (!section) {
    return (
      <div className="flex h-full flex-col bg-zinc-50 p-3 text-xs text-zinc-500">
        Selecciona una sección del canvas para configurar sus parámetros.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-zinc-50 p-3">
      <header className="mb-3">
        <h3 className="text-sm font-semibold text-zinc-800">
          {section.code} — {section.name}
        </h3>
        {section.description && (
          <p className="mt-1 text-xs text-zinc-500">{section.description}</p>
        )}
      </header>

      <div className="space-y-3 overflow-y-auto">
        <section>
          <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Parámetros transversales
          </h4>
          <div className="space-y-2">
            {TRANSVERSAL_FIELDS.map((f) => {
              if (f.type === "select") {
                return (
                  <label key={f.key} className="block text-xs text-zinc-600">
                    <span className="mb-0.5 block">{f.label}</span>
                    <Select
                      value={String(params[f.key] ?? "")}
                      onChange={(e) => update(f.key, e.target.value)}
                    >
                      {f.options.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </Select>
                  </label>
                );
              }
              if (f.type === "number") {
                return (
                  <label key={f.key} className="block text-xs text-zinc-600">
                    <span className="mb-0.5 block">{f.label}</span>
                    <Input
                      type="number"
                      min={f.min}
                      max={f.max}
                      value={String(params[f.key] ?? "")}
                      onChange={(e) =>
                        update(f.key, validate(f.key, e.target.value, f.min, f.max))
                      }
                    />
                  </label>
                );
              }
              return (
                <label key={f.key} className="block text-xs text-zinc-600">
                  <span className="mb-0.5 block">{f.label}</span>
                  <Input
                    type="text"
                    placeholder={"placeholder" in f ? f.placeholder : ""}
                    value={String(params[f.key] ?? "")}
                    onChange={(e) => update(f.key, e.target.value)}
                  />
                </label>
              );
            })}
          </div>
        </section>

        {Object.keys(schema).length > 0 && (
          <section>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Específicos
            </h4>
            <div className="space-y-2 text-xs text-zinc-500">
              {/* Schema dinámico: rendereo de fields según `parameters_schema`.
                  Para v1.0 v exponemos sólo el JSON crudo como hint visual. */}
              <pre className="overflow-x-auto rounded bg-white p-2 text-[10px]">
{JSON.stringify(schema, null, 2)}
              </pre>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
