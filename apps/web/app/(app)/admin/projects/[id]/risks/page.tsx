"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { TriangleAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  RISK_STATUS_LABEL,
  createRisk,
  listRisks,
  type Risk,
  type RiskStatus,
} from "@/lib/api/modules";
import { cn } from "@/lib/cn";

const ALL_STATUSES: RiskStatus[] = [
  "identified",
  "analyzing",
  "mitigating",
  "materialized",
  "closed",
];

function severityTone(sev: number | null) {
  if (sev === null) return "neutral" as const;
  if (sev >= 13) return "danger" as const;
  if (sev >= 6) return "warning" as const;
  return "success" as const;
}

export default function RisksPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<RiskStatus[]>([]);
  const [onlySevere, setOnlySevere] = useState(false);

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "",
    description: "",
    probability: 3,
    impact: 3,
    mitigation_strategy: "",
    due_date: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await listRisks(id, {
        status: statusFilter.length ? statusFilter : undefined,
        severity_min: onlySevere ? 13 : undefined,
      });
      setRows(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los riesgos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, statusFilter, onlySevere]);

  async function submit() {
    setSubmitting(true);
    setFormError(null);
    try {
      await createRisk(id, {
        title: form.title,
        description: form.description || null,
        probability: form.probability,
        impact: form.impact,
        mitigation_strategy: form.mitigation_strategy || null,
        due_date: form.due_date || null,
      });
      setForm({
        title: "",
        description: "",
        probability: 3,
        impact: 3,
        mitigation_strategy: "",
        due_date: "",
      });
      setOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "No se pudo crear el riesgo");
    } finally {
      setSubmitting(false);
    }
  }

  const matrix = useMemo(() => {
    const grid: number[][] = Array.from({ length: 5 }, () => Array(5).fill(0));
    for (const r of rows) {
      if (r.probability && r.impact) grid[r.probability - 1][r.impact - 1]++;
    }
    return grid;
  }, [rows]);

  return (
    <div className="space-y-6">
      <ModuleShell<Risk>
        projectId={id}
        title="Riesgos"
        subtitle="Identifica, analiza y mitiga riesgos. La severidad es probabilidad × impacto."
        icon={<TriangleAlert className="h-5 w-5" aria-hidden />}
        records={rows}
        loading={loading}
        error={error}
        newModalOpen={open}
        setNewModalOpen={setOpen}
        newButtonLabel="Nuevo riesgo"
        newModalTitle="Registrar riesgo"
        newModalForm={() => (
          <div className="space-y-3">
            {formError ? (
              <p className="rounded-[var(--radius-md)] border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-3 py-2 text-[12px] text-[var(--color-danger-fg)]">
                {formError}
              </p>
            ) : null}
            <Field label="Título">
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Descripción">
              <Textarea
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Probabilidad (1-5)">
                <Select
                  value={String(form.probability)}
                  onChange={(e) => setForm({ ...form, probability: Number(e.target.value) })}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Impacto (1-5)">
                <Select
                  value={String(form.impact)}
                  onChange={(e) => setForm({ ...form, impact: Number(e.target.value) })}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="Estrategia de mitigación">
              <Textarea
                rows={3}
                value={form.mitigation_strategy}
                onChange={(e) => setForm({ ...form, mitigation_strategy: e.target.value })}
              />
            </Field>
            <Field label="Fecha compromiso">
              <Input
                type="date"
                value={form.due_date}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              />
            </Field>
          </div>
        )}
        newModalFooter={(close) => (
          <>
            <Button variant="secondary" onClick={close} disabled={submitting}>
              Cancelar
            </Button>
            <Button onClick={submit} loading={submitting} disabled={!form.title.trim()}>
              Crear
            </Button>
          </>
        )}
        filters={
          <>
            <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
              Estado
            </span>
            {ALL_STATUSES.map((s) => {
              const active = statusFilter.includes(s);
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() =>
                    setStatusFilter(
                      active ? statusFilter.filter((x) => x !== s) : [...statusFilter, s],
                    )
                  }
                  aria-pressed={active}
                  className={cn(
                    "inline-flex h-7 items-center rounded-full border px-2.5 text-[12px] font-medium transition-colors",
                    active
                      ? "border-[var(--text-primary)] bg-[var(--text-primary)] text-[var(--color-inverse)]"
                      : "border-[var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
                  )}
                >
                  {RISK_STATUS_LABEL[s]}
                </button>
              );
            })}
            <label className="ml-3 inline-flex items-center gap-2 text-[12px] text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={onlySevere}
                onChange={(e) => setOnlySevere(e.target.checked)}
              />
              Sólo severos (≥13)
            </label>
          </>
        }
        columns={[
          {
            key: "title",
            label: "Riesgo",
            render: (r) => (
              <div>
                <p className="font-medium">{r.title}</p>
                {r.category ? (
                  <p className="text-[11px] text-[var(--text-tertiary)]">{r.category}</p>
                ) : null}
              </div>
            ),
          },
          { key: "p", label: "P", render: (r) => <span className="tabular-nums">{r.probability ?? "—"}</span> },
          { key: "i", label: "I", render: (r) => <span className="tabular-nums">{r.impact ?? "—"}</span> },
          {
            key: "sev",
            label: "Severidad",
            render: (r) => (
              <Badge variant={severityTone(r.severity)}>{r.severity ?? "—"}</Badge>
            ),
          },
          {
            key: "status",
            label: "Estado",
            render: (r) => <Badge>{RISK_STATUS_LABEL[r.status]}</Badge>,
          },
          {
            key: "due",
            label: "Vence",
            render: (r) => r.due_date ?? "—",
          },
        ]}
      />

      <section className="mx-auto max-w-6xl rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
        <h2 className="mb-3 text-[14px] font-semibold text-[var(--text-primary)]">
          Matriz P × I
        </h2>
        <p className="mb-3 text-[12px] text-[var(--text-tertiary)]">
          Cada celda muestra el conteo de riesgos con esa combinación de probabilidad (fila) e impacto
          (columna).
        </p>
        <div className="overflow-x-auto">
          <table className="w-full max-w-xl border-collapse text-center text-[12px]">
            <thead>
              <tr>
                <th className="p-2 text-left text-[11px] uppercase text-[var(--text-tertiary)]">
                  P / I
                </th>
                {[1, 2, 3, 4, 5].map((i) => (
                  <th key={i} className="p-2 text-[11px] text-[var(--text-tertiary)]">
                    {i}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row, p) => (
                <tr key={p}>
                  <td className="p-2 text-left text-[11px] text-[var(--text-tertiary)]">{p + 1}</td>
                  {row.map((count, i) => {
                    const sev = (p + 1) * (i + 1);
                    const tone = severityTone(sev);
                    const bg =
                      tone === "danger"
                        ? "var(--color-danger-bg)"
                        : tone === "warning"
                          ? "var(--color-warning-bg)"
                          : "var(--color-success-bg)";
                    const border =
                      tone === "danger"
                        ? "var(--color-danger-border)"
                        : tone === "warning"
                          ? "var(--color-warning-border)"
                          : "var(--color-success-border)";
                    return (
                      <td
                        key={i}
                        className="h-12 w-12 border p-0 text-[var(--text-primary)]"
                        style={{ backgroundColor: bg, borderColor: border }}
                        title={`Severidad ${sev} · ${count} riesgo(s)`}
                      >
                        <span className="font-semibold tabular-nums">{count}</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
    </label>
  );
}
