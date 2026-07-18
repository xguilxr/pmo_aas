"use client";

// US-191 — modal de evaluación periódica de salud: 5 dimensiones +
// salud global (la "sexta", el cuadro grande) con Fecha de Evaluación.
// Cada guardado queda en la historia; abajo se muestra la evolución.
// Reusado desde la tarjeta de Salud del proyecto y desde el portafolio
// (health-matrix / lista de proyectos, US-192).

import { useCallback, useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createHealthEvaluation,
  listHealthEvaluations,
  type HealthEvaluation,
  type ProjectHealth,
} from "@/lib/api/projects";
import { cn } from "@/lib/cn";

const DIMENSIONS: { key: DimKey; label: string }[] = [
  { key: "schedule", label: "Cronograma" },
  { key: "budget", label: "Presupuesto" },
  { key: "risks", label: "Riesgos / Issues" },
  { key: "decisions", label: "Decisiones" },
  { key: "resources", label: "Recursos" },
];

type DimKey = "schedule" | "budget" | "risks" | "decisions" | "resources";

const RAG_LABEL: Record<ProjectHealth, string> = {
  green: "Verde",
  yellow: "Amarillo",
  red: "Rojo",
};

function localToday(): string {
  const d = new Date();
  const off = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - off).toISOString().slice(0, 10);
}

export function RagDot({
  color,
  className,
}: {
  color: ProjectHealth | null | undefined;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full",
        color === "green" && "bg-emerald-500",
        color === "yellow" && "bg-amber-400",
        color === "red" && "bg-red-500",
        !color && "bg-[var(--border-default)]",
        className,
      )}
      title={color ? RAG_LABEL[color] : "Sin evaluar"}
      aria-label={color ? RAG_LABEL[color] : "Sin evaluar"}
    />
  );
}

function RagSelect({
  value,
  onChange,
  allowEmpty = true,
  ariaLabel,
}: {
  value: ProjectHealth | "";
  onChange: (v: ProjectHealth | "") => void;
  allowEmpty?: boolean;
  ariaLabel: string;
}) {
  return (
    <span className="flex items-center gap-2">
      <RagDot color={value || null} />
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value as ProjectHealth | "")}
        aria-label={ariaLabel}
        className="flex-1"
      >
        {allowEmpty ? <option value="">— sin evaluar —</option> : null}
        <option value="green">🟢 Verde</option>
        <option value="yellow">🟡 Amarillo</option>
        <option value="red">🔴 Rojo</option>
      </Select>
    </span>
  );
}

export function HealthEvaluationModal({
  projectId,
  projectName,
  open,
  onClose,
  onSaved,
}: {
  projectId: string;
  projectName?: string;
  open: boolean;
  onClose: () => void;
  /** Se llama tras guardar (para refrescar tarjeta/matriz). */
  onSaved?: () => void;
}) {
  const [evaluatedAt, setEvaluatedAt] = useState<string>(localToday);
  const [dims, setDims] = useState<Record<DimKey, ProjectHealth | "">>({
    schedule: "",
    budget: "",
    risks: "",
    decisions: "",
    resources: "",
  });
  const [overall, setOverall] = useState<ProjectHealth | "">("");
  const [note, setNote] = useState("");
  const [history, setHistory] = useState<HealthEvaluation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(() => {
    listHealthEvaluations(projectId)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [projectId]);

  useEffect(() => {
    if (!open) return;
    setEvaluatedAt(localToday());
    setDims({ schedule: "", budget: "", risks: "", decisions: "", resources: "" });
    setOverall("");
    setNote("");
    setError(null);
    loadHistory();
  }, [open, loadHistory]);

  async function save() {
    if (!overall) {
      setError("La salud global (la sexta evaluación) es obligatoria.");
      return;
    }
    if (overall !== "green" && note.trim().length < 5) {
      setError("Amarillo o rojo requieren una nota (mínimo 5 caracteres).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createHealthEvaluation(projectId, {
        evaluated_at: evaluatedAt || null,
        schedule: dims.schedule || null,
        budget: dims.budget || null,
        risks: dims.risks || null,
        decisions: dims.decisions || null,
        resources: dims.resources || null,
        overall,
        note: note.trim() || null,
      });
      loadHistory();
      onSaved?.();
      onClose();
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "No se pudo guardar la evaluación",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => !busy && onClose()}
      title={
        projectName
          ? `Evaluar salud — ${projectName}`
          : "Evaluar salud del período"
      }
      description="Las 5 dimensiones + la salud del proyecto como un todo. Cada guardado queda en la historia."
      size="lg"
    >
      <div className="space-y-3">
        {error ? <Banner variant="danger">{error}</Banner> : null}

        <label className="block max-w-[200px]">
          <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
            Fecha de evaluación
          </span>
          <Input
            type="date"
            value={evaluatedAt}
            onChange={(e) => setEvaluatedAt(e.target.value)}
          />
        </label>

        <div className="grid gap-2 sm:grid-cols-2">
          {DIMENSIONS.map((d) => (
            <label key={d.key} className="block">
              <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
                {d.label}
              </span>
              <RagSelect
                value={dims[d.key]}
                onChange={(v) => setDims((m) => ({ ...m, [d.key]: v }))}
                ariaLabel={`Evaluación de ${d.label}`}
              />
            </label>
          ))}
          <label className="block rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-subtle)] p-2">
            <span className="mb-1 block text-[12px] font-semibold text-[var(--text-primary)]">
              Salud del proyecto (global) *
            </span>
            <RagSelect
              value={overall}
              onChange={(v) => setOverall(v)}
              allowEmpty
              ariaLabel="Salud global del proyecto"
            />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
            Nota del período{" "}
            {overall && overall !== "green" ? "(obligatoria)" : "(opcional)"}
          </span>
          <Textarea
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Qué sustenta esta evaluación…"
          />
        </label>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button onClick={save} loading={busy}>
            Guardar evaluación
          </Button>
        </div>

        {/* Historia: evolución de las 5+1 en el tiempo. */}
        {history.length > 0 ? (
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
              Evaluaciones anteriores
            </div>
            <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-default)]">
              <table className="min-w-full text-xs">
                <thead className="bg-[var(--color-subtle)] text-left text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
                  <tr>
                    <th className="px-2 py-1.5">Fecha</th>
                    {DIMENSIONS.map((d) => (
                      <th key={d.key} className="px-2 py-1.5 text-center" title={d.label}>
                        {d.label.slice(0, 4)}.
                      </th>
                    ))}
                    <th className="px-2 py-1.5 text-center">Global</th>
                    <th className="px-2 py-1.5">Nota</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id} className="border-t border-[var(--border-subtle)]">
                      <td className="px-2 py-1.5 whitespace-nowrap text-[var(--color-secondary)]">
                        {h.evaluated_at}
                      </td>
                      {DIMENSIONS.map((d) => (
                        <td key={d.key} className="px-2 py-1.5 text-center">
                          <RagDot color={h[d.key]} />
                        </td>
                      ))}
                      <td className="px-2 py-1.5 text-center">
                        <RagDot color={h.overall} className="h-3 w-3" />
                      </td>
                      <td
                        className="max-w-[220px] truncate px-2 py-1.5 text-[var(--color-tertiary)]"
                        title={h.note ?? ""}
                      >
                        {h.note ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
