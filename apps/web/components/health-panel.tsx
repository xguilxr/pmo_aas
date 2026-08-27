"use client";

/**
 * US-181 — Salud única híbrida: UI compartida.
 *
 * - HealthStatusCard: tarjeta del semáforo (color efectivo + fuente +
 *   mini-dots por dimensión) con acción "Declarar".
 * - HealthDeclareModal: declarar verde/amarillo/rojo (razón obligatoria
 *   en amarillo/rojo) o volver a la fuente automática.
 * - HealthWhyPanel: drill-down "por qué" — dimensiones con causas +
 *   tarjetas "Foco PM" (qué pasó / responsable / fecha / siguiente acción).
 */
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/textarea";
import {
  HEALTH_LABEL,
  type HealthDetail,
  type HealthDimension,
  type ProjectHealth,
  type ProjectHealthSource,
} from "@/lib/api/projects";
import { cn } from "@/lib/cn";

export function healthTone(color: ProjectHealth | null): string {
  if (color === "green") return "bg-[var(--color-success-fg)]";
  if (color === "yellow") return "bg-[var(--color-warning-fg)]";
  if (color === "red") return "bg-[var(--color-danger-fg)]";
  return "bg-[var(--border-subtle)]";
}

export function HealthStatusCard({
  value,
  source,
  reason,
  detail,
  onDeclare,
  onEvaluate,
}: {
  value: ProjectHealth;
  source: ProjectHealthSource;
  reason: string | null;
  detail: HealthDetail | null;
  onDeclare: () => void;
  /** US-191: abre la evaluación 5+1 con historial. */
  onEvaluate?: () => void;
}) {
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-3.5 shadow-[var(--relieve-isla)]">
      <p className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
        Salud
      </p>
      <div className="mt-2.5 flex items-center gap-2">
        <span className={cn("h-2.5 w-2.5 rounded-full", healthTone(value))} />
        <span className="text-[19px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
          {HEALTH_LABEL[value]}
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-[11.5px] leading-[1.5] text-[var(--text-tertiary)]" title={reason ?? undefined}>
        {source === "manual" ? "Declarada por PM" : "Automática"}
        {source === "manual" && reason ? ` · ${reason}` : ""}
      </p>
      {detail ? (
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          {detail.dimensions.map((d) => (
            <span
              key={d.key}
              title={`${d.label}: ${d.summary}`}
              className="inline-flex items-center gap-1 text-[10px] text-[var(--text-tertiary)]"
            >
              <span className={cn("h-2 w-2 rounded-full", healthTone(d.color))} />
              {d.label}
            </span>
          ))}
        </div>
      ) : null}
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        <Button size="sm" variant="secondary" onClick={onDeclare}>
          Declarar
        </Button>
        {/* US-191: evaluación 5+1 del período con historial. */}
        {onEvaluate ? (
          <Button size="sm" variant="secondary" onClick={onEvaluate}>
            Evaluar 5+1
          </Button>
        ) : null}
      </div>
    </article>
  );
}

export function HealthDeclareModal({
  open,
  current,
  source,
  reason: initialReason,
  pending,
  onClose,
  onDeclare,
  onBackToAuto,
}: {
  open: boolean;
  current: ProjectHealth;
  source: ProjectHealthSource;
  reason: string | null;
  pending: boolean;
  onClose: () => void;
  onDeclare: (status: ProjectHealth, reason: string) => void;
  onBackToAuto: () => void;
}) {
  const [status, setStatus] = useState<ProjectHealth>(current);
  const [reason, setReason] = useState(initialReason ?? "");
  const needsReason = status !== "green";
  const valid = !needsReason || reason.trim().length >= 5;
  const HEALTHS: ProjectHealth[] = ["green", "yellow", "red"];

  return (
    <Modal open={open} onClose={onClose} title="Declarar salud del proyecto">
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">
          La declaración manual manda sobre el cálculo automático hasta que
          regreses la salud a modo automático.
        </p>
        <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-1">
          {HEALTHS.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setStatus(h)}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-medium transition-colors",
                status === h
                  ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
              )}
            >
              <span className={cn("h-2.5 w-2.5 rounded-full", healthTone(h))} />
              {HEALTH_LABEL[h]}
            </button>
          ))}
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
            Razón {needsReason ? "(obligatoria)" : "(opcional)"}
          </label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Qué está pasando y qué se está haciendo al respecto…"
          />
          {needsReason && !valid ? (
            <p className="mt-1 text-xs text-[var(--color-danger-fg)]">
              Mínimo 5 caracteres para declarar amarillo/rojo.
            </p>
          ) : null}
        </div>
        <div className="flex items-center justify-between gap-2">
          {source === "manual" ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={pending}
              onClick={onBackToAuto}
              className="gap-1.5"
            >
              <Icono nombre="rotate-ccw" size={14} />
              Volver a automática
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={onClose} disabled={pending}>
              Cancelar
            </Button>
            <Button
              size="sm"
              disabled={pending || !valid}
              onClick={() => onDeclare(status, reason.trim())}
            >
              Declarar
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

const MATRIX_DIMS: { key: string; label: string }[] = [
  { key: "schedule", label: "Cronograma" },
  { key: "budget", label: "Presupuesto" },
  { key: "risks", label: "Riesgos" },
  { key: "decisions", label: "Decisiones" },
  { key: "resources", label: "Recursos" },
];

/** US-181 — heatmap ejecutivo Proyecto × Dimensión (dashboard N1). */
export function HealthDimensionMatrix({
  rows,
  onRowClick,
  onEvaluate,
}: {
  rows: {
    project_id: string;
    folio: string;
    name: string;
    organization_name: string | null;
    health_status: ProjectHealth;
    health_source: "auto" | "manual";
    dims: Record<string, ProjectHealth | null>;
  }[];
  onRowClick?: (projectId: string) => void;
  /** US-192: evaluar salud 5+1 sin abrir el proyecto. */
  onEvaluate?: (projectId: string, name: string) => void;
}) {
  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
        Sin proyectos activos visibles.
      </p>
    );
  }
  // Amarillos/rojos primero — el heatmap existe para encontrar el fuego.
  const rank = { red: 0, yellow: 1, green: 2 } as const;
  const sorted = [...rows].sort(
    (a, b) => rank[a.health_status] - rank[b.health_status] || a.name.localeCompare(b.name),
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-xs">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
            <th className="py-1.5 pr-2 font-medium">Proyecto</th>
            <th className="px-2 py-1.5 text-center font-medium">Salud</th>
            {MATRIX_DIMS.map((d) => (
              <th key={d.key} className="px-2 py-1.5 text-center font-medium">
                {d.label}
              </th>
            ))}
            {onEvaluate ? <th className="px-2 py-1.5" aria-label="Evaluar" /> : null}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.project_id}
              onClick={onRowClick ? () => onRowClick(r.project_id) : undefined}
              className={cn(
                "border-t border-[var(--border-subtle)]",
                onRowClick && "cursor-pointer hover:bg-[var(--color-subtle)]",
              )}
            >
              <td className="max-w-[260px] py-1.5 pr-2">
                <span className="block truncate font-medium text-[var(--text-primary)]" title={r.name}>
                  {r.name}
                </span>
                <span className="text-[10px] text-[var(--text-tertiary)]">
                  {r.folio}
                  {r.organization_name ? ` · ${r.organization_name}` : ""}
                </span>
              </td>
              <td className="px-2 py-1.5 text-center">
                <span
                  title={r.health_source === "manual" ? "Declarada por el PM" : "Automática"}
                  className={cn(
                    "inline-block h-3 w-3 rounded-full",
                    healthTone(r.health_status),
                    r.health_source === "manual" &&
                      "ring-1 ring-[var(--text-tertiary)] ring-offset-1 ring-offset-[var(--color-surface)]",
                  )}
                />
              </td>
              {MATRIX_DIMS.map((d) => (
                <td key={d.key} className="px-2 py-1.5 text-center">
                  <span
                    title={`${d.label}: ${r.dims[d.key] ?? "N/A"}`}
                    className={cn("inline-block h-2.5 w-2.5 rounded-full", healthTone(r.dims[d.key] ?? null))}
                  />
                </td>
              ))}
              {onEvaluate ? (
                <td className="px-2 py-1.5 text-right">
                  {/* US-192: editar la salud 5+1 sin abrir el proyecto. */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onEvaluate(r.project_id, r.name);
                    }}
                    className="rounded-[var(--radius-sm)] border border-[var(--border-default)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]"
                  >
                    Evaluar
                  </button>
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[10px] text-[var(--text-tertiary)]">
        Anillo = salud declarada por el PM · gris = sin datos (N/A)
      </p>
    </div>
  );
}

function DimensionRow({ dim }: { dim: HealthDimension }) {
  return (
    <div className="flex items-start gap-2.5 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-3">
      <span className={cn("mt-1 h-2.5 w-2.5 shrink-0 rounded-full", healthTone(dim.color))} />
      <div className="min-w-0">
        <p className="text-xs font-semibold text-[var(--text-primary)]">
          {dim.label}
          {dim.color === null ? (
            <span className="ml-1.5 font-normal text-[var(--text-tertiary)]">N/A</span>
          ) : null}
        </p>
        <p className="text-xs text-[var(--text-secondary)]">{dim.summary}</p>
      </div>
    </div>
  );
}

export function HealthWhyPanel({ detail }: { detail: HealthDetail }) {
  const hasFocus = detail.focus.length > 0;
  return (
    <section
      aria-label="Por qué esta salud"
      className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-3.5 shadow-[var(--relieve-isla)]"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">
          ¿Por qué? — salud por dimensión
        </h2>
        {detail.health_source === "manual" && detail.computed !== detail.health_status ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
            PM declara {HEALTH_LABEL[detail.health_status]} · cálculo dice{" "}
            {HEALTH_LABEL[detail.computed]}
            <span className={cn("h-2 w-2 rounded-full", healthTone(detail.computed))} />
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {detail.dimensions.map((d) => (
          <DimensionRow key={d.key} dim={d} />
        ))}
      </div>

      {hasFocus ? (
        <div className="mt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
            Foco PM
          </h3>
          <div className="mt-2 grid gap-2 lg:grid-cols-2">
            {detail.focus.map((f, i) => (
              <div
                key={`${f.type}-${i}`}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3"
              >
                <div className="flex items-center gap-2">
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", healthTone(f.color))} />
                  <p className="truncate text-xs font-semibold text-[var(--text-primary)]" title={f.what}>
                    {f.what}
                  </p>
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                  <div>
                    <dt className="text-[var(--text-tertiary)]">Dimensión</dt>
                    <dd className="text-[var(--text-secondary)]">{f.dimension_label}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-tertiary)]">Responsable</dt>
                    <dd className="text-[var(--text-secondary)]">{f.owner ?? "Sin asignar"}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-tertiary)]">Fecha compromiso</dt>
                    <dd className="text-[var(--text-secondary)]">
                      {f.due_date ?? "—"}
                      {typeof f.days === "number" && f.days > 0 ? ` · ${f.days}d` : ""}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-tertiary)]">Siguiente acción</dt>
                    <dd className="text-[var(--text-secondary)]">{f.suggested_action}</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-3 text-xs text-[var(--text-tertiary)]">
          Sin causas activas — el proyecto no tiene señales de alerta.
        </p>
      )}
    </section>
  );
}
