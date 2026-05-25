"use client";

import { useMemo } from "react";

import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ReportSection } from "@/lib/api/report-builder";

export type SectionParams = Record<string, unknown>;

/**
 * US-125 + BUG-063 — Parámetros POR SECCIÓN (inline en el canvas).
 *
 * Los transversales del reporte completo (área, ventana, agrupación) se
 * configuran en la barra superior. Aquí quedan SOLO los parámetros
 * propios de cada sección:
 * - `top_n` y `order_by` para secciones con tabla.
 * - `mode` (resumen/detalle) para las que lo soporten.
 * - Toggles de campos visibles (`excluded_fields`) cuando la sección
 *   declara `data_shape.fields` — permite quitar columnas sin quitar la
 *   sección entera.
 */

const ORDER_OPTIONS = [
  { value: "", label: "Por defecto" },
  { value: "date_asc", label: "Fecha ↑" },
  { value: "date_desc", label: "Fecha ↓" },
  { value: "severity_desc", label: "Severidad ↓" },
  { value: "area", label: "Área" },
] as const;

const MODE_OPTIONS = [
  { value: "", label: "Por defecto" },
  { value: "summary", label: "Resumen" },
  { value: "detail", label: "Detalle" },
] as const;

type FormProps = {
  section: ReportSection | null;
  params: SectionParams;
  onChange: (next: SectionParams) => void;
};

function _fieldsOf(section: ReportSection | null): string[] {
  const shape = (section?.data_shape ?? {}) as Record<string, unknown>;
  const fields = shape.fields;
  return Array.isArray(fields) ? fields.filter((f): f is string => typeof f === "string") : [];
}

/** Form de parámetros de una sola sección (sin header — el canvas ya lo
 *  muestra). Usado inline en cada item del SectionCanvas. */
export function SectionParamsForm({ section, params, onChange }: FormProps) {
  const fields = useMemo(() => _fieldsOf(section), [section]);
  const excluded = useMemo(
    () => (Array.isArray(params.excluded_fields) ? (params.excluded_fields as string[]) : []),
    [params.excluded_fields],
  );
  // Una sección "de tabla" si su data_shape declara `rows`.
  const isTable = useMemo(() => {
    const shape = (section?.data_shape ?? {}) as Record<string, unknown>;
    return Array.isArray(shape.fields) && shape.fields.includes("rows");
  }, [section]);

  function update(key: string, value: unknown) {
    if (value === "" || value === undefined || value === null) {
      const next = { ...params };
      delete next[key];
      onChange(next);
      return;
    }
    onChange({ ...params, [key]: value });
  }

  function toggleField(field: string, include: boolean) {
    const set = new Set(excluded);
    if (include) set.delete(field);
    else set.add(field);
    const arr = [...set];
    if (arr.length === 0) {
      const next = { ...params };
      delete next.excluded_fields;
      onChange(next);
      return;
    }
    onChange({ ...params, excluded_fields: arr });
  }

  if (!section) {
    return <p className="text-xs text-zinc-500">Sección sin catalogar.</p>;
  }

  return (
    <div className="space-y-3">
      {isTable && (
        <div className="grid grid-cols-2 gap-2">
          <label className="block text-xs text-zinc-600">
            <span className="mb-0.5 block">Top N</span>
            <Input
              type="number"
              min={1}
              max={100}
              placeholder="Todos"
              value={String(params.top_n ?? "")}
              onChange={(e) => {
                const n = Number(e.target.value);
                update("top_n", e.target.value === "" || Number.isNaN(n) ? "" : Math.max(1, Math.min(100, n)));
              }}
            />
          </label>
          <label className="block text-xs text-zinc-600">
            <span className="mb-0.5 block">Ordenamiento</span>
            <Select
              value={String(params.order_by ?? "")}
              onChange={(e) => update("order_by", e.target.value)}
            >
              {ORDER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          </label>
        </div>
      )}

      <label className="block text-xs text-zinc-600">
        <span className="mb-0.5 block">Modo</span>
        <Select
          value={String(params.mode ?? "")}
          onChange={(e) => update("mode", e.target.value)}
        >
          {MODE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </label>

      {fields.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-zinc-600">
            Campos visibles
          </p>
          <div className="flex flex-wrap gap-1.5">
            {fields.map((f) => {
              const included = !excluded.includes(f);
              return (
                <label
                  key={f}
                  className={`inline-flex cursor-pointer items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${
                    included
                      ? "border-zinc-300 bg-white text-zinc-700"
                      : "border-zinc-200 bg-zinc-100 text-zinc-400 line-through"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="h-3 w-3"
                    checked={included}
                    onChange={(e) => toggleField(f, e.target.checked)}
                  />
                  {f}
                </label>
              );
            })}
          </div>
          <p className="mt-1 text-[10.5px] text-zinc-400">
            Desmarca un campo para quitarlo del reporte sin quitar la sección.
          </p>
        </div>
      )}
    </div>
  );
}
