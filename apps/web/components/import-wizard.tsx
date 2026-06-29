"use client";

import { AlertTriangle, FileSpreadsheet, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import {
  type ImportPreviewResult,
  type ImportSource,
  type SystemField,
  SYSTEM_FIELDS,
  SYSTEM_FIELD_LABELS,
  importConfirm,
  importPreview,
  suggestImportMapping,
} from "@/lib/api/tasks";

/**
 * US-070 — Wizard de mapeo de columnas para import de plan.
 *
 * 4 pasos lógicos:
 *  1. Upload — selección de archivo (.xlsx/.csv/.mpp/.xml).
 *  2. Sheet — solo si Excel con >1 hoja; skip auto en CSV/MPP/XML.
 *  3. Preview + mapping — tabla de las primeras filas + dropdown
 *     por columna que asigna a `SystemField`. Solo XLSX/CSV;
 *     MPP/XML muestran preview informativo sin mapping (sus
 *     parsers ya emiten shape normalizado).
 *  4. Confirm — estrategia merge|replace + summary + botón final.
 */

type Step = "upload" | "sheet" | "preview" | "done";

const ACCEPT = ".xlsx,.csv,.mpp,.xml,.mpx,.mspdi";
const NEEDS_MAPPING: ImportSource[] = ["xlsx", "csv"];

type ImportWizardProps = {
  open: boolean;
  onClose: () => void;
  projectId: string;
  onImported: (count: number) => void;
};

export function ImportWizard({
  open,
  onClose,
  projectId,
  onImported,
}: ImportWizardProps) {
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null);
  const [sheet, setSheet] = useState<string | null>(null);
  // mapping[colIndex] = systemField — invierte la forma del backend
  // (`{field: colIndex}`) para hacer el render por-columna más natural.
  const [mapping, setMapping] = useState<Record<number, SystemField | "">>({});
  const [strategy, setStrategy] = useState<"merge" | "replace">("merge");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // ENH-053: confidence por columna. Se llena con la sugerencia AI/heurística;
  // confidence < 0.7 muestra warning de "match débil" en la UI.
  const [confidence, setConfidence] = useState<Record<number, number>>({});
  const [aiUsed, setAiUsed] = useState(false);

  function reset() {
    setStep("upload");
    setFile(null);
    setPreview(null);
    setSheet(null);
    setMapping({});
    setConfidence({});
    setAiUsed(false);
    setStrategy("merge");
    setBusy(false);
    setError(null);
  }

  useEffect(() => {
    if (!open) reset();
  }, [open]);

  async function runPreview(f: File, selectedSheet: string | null) {
    setBusy(true);
    setError(null);
    try {
      const result = await importPreview(projectId, f, selectedSheet);
      setPreview(result);
      setSheet(result.sheet_used);
      // Pre-llenar mapping con auto-detect.
      const initial: Record<number, SystemField | ""> = {};
      for (const [field, idx] of Object.entries(result.columns_detected)) {
        if (typeof idx === "number") initial[idx] = field as SystemField;
      }
      setMapping(initial);
      // ENH-053: pedir sugerencia (heurística + IA si tenant tiene IA)
      // para las columnas que no fueron detectadas por el parser. Si
      // falla, no rompe el flujo — el wizard sigue manual.
      const headerRow = (result.sample_rows[0] || []).map((v) =>
        v == null ? "" : String(v),
      );
      const headers = headerRow.filter(Boolean);
      if (headers.length > 0 && NEEDS_MAPPING.includes(result.source)) {
        try {
          const sug = await suggestImportMapping(projectId, headers);
          setAiUsed(sug.ai_used);
          const conf: Record<number, number> = {};
          headerRow.forEach((h, idx) => {
            if (!h) return;
            const item = sug.suggestions[h];
            if (!item) return;
            conf[idx] = item.confidence;
            // Si el parser ya detectó una columna, no la pisamos. Para
            // columnas sin detect, completamos con la sugerencia.
            if (item.field && initial[idx] === undefined) {
              initial[idx] = item.field;
            }
          });
          setMapping({ ...initial });
          setConfidence(conf);
        } catch {
          /* la heurística siempre debe funcionar offline; si el endpoint
             cae lo dejamos al usuario. */
        }
      }
      // Si Excel con >1 hojas y todavía no se eligió, abrir sheet
      // selector. Si no, ir directo a preview.
      if (result.sheets.length > 1 && !selectedSheet) {
        setStep("sheet");
      } else {
        setStep("preview");
      }
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "No se pudo procesar el archivo",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(f: File) {
    setFile(f);
    await runPreview(f, null);
  }

  async function chooseSheet(name: string) {
    if (!file) return;
    setSheet(name);
    await runPreview(file, name);
  }

  async function confirm() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      const needsMapping = NEEDS_MAPPING.includes(preview.source);
      let mappingPayload: Partial<Record<SystemField, number>> | null = null;
      if (needsMapping) {
        // Convertir mapping[colIndex]=field → {field: colIndex}.
        const inverted: Partial<Record<SystemField, number>> = {};
        for (const [colIdxStr, field] of Object.entries(mapping)) {
          if (!field) continue;
          inverted[field as SystemField] = Number(colIdxStr);
        }
        if (inverted.name === undefined) {
          setError(
            "El mapping debe incluir la columna 'Nombre' antes de confirmar.",
          );
          setBusy(false);
          return;
        }
        if (strategy === "replace") {
          const ok = window.confirm(
            "Estrategia REPLACE: se eliminarán todas las tareas actuales del proyecto antes de importar. ¿Continuar?",
          );
          if (!ok) {
            setBusy(false);
            return;
          }
        }
        mappingPayload = inverted;
      } else if (strategy === "replace") {
        const ok = window.confirm(
          "Estrategia REPLACE: se eliminarán todas las tareas actuales del proyecto antes de importar. ¿Continuar?",
        );
        if (!ok) {
          setBusy(false);
          return;
        }
      }
      const result = await importConfirm(projectId, preview.job_id, {
        mapping: mappingPayload,
        strategy,
      });
      onImported(result.imported);
      setStep("done");
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "No se pudo confirmar el import",
      );
    } finally {
      setBusy(false);
    }
  }

  const headerLabels = preview?.sample_rows[0] ?? [];
  const sampleData = preview?.sample_rows.slice(1) ?? [];
  const usedFields = useMemo(
    () => new Set(Object.values(mapping).filter(Boolean) as SystemField[]),
    [mapping],
  );
  const missingName = preview && !usedFields.has("name");
  const needsMapping = preview ? NEEDS_MAPPING.includes(preview.source) : true;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={titleFor(step, preview?.source)}
      description={descriptionFor(step, preview)}
      size="lg"
      footer={footerFor({
        step,
        busy,
        canConfirm: !!preview && (!needsMapping || !missingName),
        onClose,
        onBack: () => {
          if (step === "preview" && preview && preview.sheets.length > 1) {
            setStep("sheet");
          } else if (step === "preview" || step === "sheet") {
            setStep("upload");
            setPreview(null);
            setFile(null);
          }
        },
        onConfirm: confirm,
      })}
    >
      {error ? <Banner variant="danger">{error}</Banner> : null}

      {step === "upload" ? (
        <UploadStep onFile={handleFile} busy={busy} />
      ) : null}

      {step === "sheet" && preview ? (
        <SheetStep
          sheets={preview.sheets}
          current={sheet}
          onPick={chooseSheet}
          busy={busy}
        />
      ) : null}

      {step === "preview" && preview ? (
        <PreviewStep
          preview={preview}
          headerLabels={headerLabels}
          sampleData={sampleData}
          mapping={mapping}
          onChangeMapping={(idx, field) =>
            setMapping((m) => ({ ...m, [idx]: field }))
          }
          missingName={Boolean(missingName)}
          needsMapping={needsMapping}
          strategy={strategy}
          onChangeStrategy={setStrategy}
          confidence={confidence}
          aiUsed={aiUsed}
        />
      ) : null}

      {step === "done" ? (
        <div className="space-y-2 text-center">
          <p className="text-sm font-semibold text-[var(--color-success-fg)]">
            ✓ Import completado
          </p>
          <p className="text-sm text-[var(--color-secondary)]">
            Cerrá esta ventana para ver las tareas en la lista.
          </p>
        </div>
      ) : null}
    </Modal>
  );
}

function titleFor(step: Step, source?: ImportSource): string {
  if (step === "upload") return "Importar plan — paso 1 de 3";
  if (step === "sheet") return "Importar plan — paso 2 de 3 · Hoja";
  if (step === "preview") {
    const total = source && NEEDS_MAPPING.includes(source) ? 3 : 2;
    return `Importar plan — paso ${total} de ${total} · Confirmar`;
  }
  return "Importar plan";
}

function descriptionFor(
  step: Step,
  preview: ImportPreviewResult | null,
): string | undefined {
  if (step === "upload") {
    return "Acepta .xlsx, .csv, .mpp y .xml de MS Project. Máximo 10 MB.";
  }
  if (step === "sheet") {
    return "Elegí qué hoja del libro contiene el plan a importar.";
  }
  if (step === "preview") {
    if (preview && !NEEDS_MAPPING.includes(preview.source)) {
      return "Este formato ya viene normalizado. Confirmá la estrategia y dale Importar.";
    }
    return "Asigná cada columna del archivo al campo del sistema. La columna 'Nombre' es obligatoria.";
  }
  return undefined;
}

type FooterArgs = {
  step: Step;
  busy: boolean;
  canConfirm: boolean;
  onClose: () => void;
  onBack: () => void;
  onConfirm: () => void;
};

function footerFor({
  step,
  busy,
  canConfirm,
  onClose,
  onBack,
  onConfirm,
}: FooterArgs) {
  if (step === "upload") {
    return (
      <Button variant="secondary" onClick={onClose} disabled={busy}>
        Cancelar
      </Button>
    );
  }
  if (step === "sheet") {
    return (
      <>
        <Button variant="secondary" onClick={onBack} disabled={busy}>
          Atrás
        </Button>
      </>
    );
  }
  if (step === "preview") {
    return (
      <>
        <Button variant="secondary" onClick={onBack} disabled={busy}>
          Atrás
        </Button>
        <Button onClick={onConfirm} disabled={busy || !canConfirm}>
          {busy ? "Importando…" : "Importar"}
        </Button>
      </>
    );
  }
  return (
    <Button onClick={onClose}>Cerrar</Button>
  );
}

function UploadStep({
  onFile,
  busy,
}: {
  onFile: (f: File) => void | Promise<void>;
  busy: boolean;
}) {
  return (
    <label
      className={
        "flex flex-col items-center gap-2 rounded-[var(--radius-xl)] border-2 border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] py-10 text-center cursor-pointer hover:border-[var(--color-accent)] hover:bg-[var(--color-surface)]" +
        (busy ? " pointer-events-none opacity-60" : "")
      }
    >
      <Upload className="h-8 w-8 text-[var(--color-tertiary)]" aria-hidden />
      <span className="text-sm font-medium text-[var(--color-primary)]">
        {busy ? "Procesando…" : "Click para elegir archivo"}
      </span>
      <span className="text-xs text-[var(--color-tertiary)]">
        .xlsx · .csv · .mpp · .xml
      </span>
      <input
        type="file"
        accept={ACCEPT}
        className="sr-only"
        disabled={busy}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onFile(f);
          e.target.value = "";
        }}
      />
    </label>
  );
}

function SheetStep({
  sheets,
  current,
  onPick,
  busy,
}: {
  sheets: string[];
  current: string | null;
  onPick: (name: string) => void;
  busy: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm text-[var(--color-secondary)]">
        El archivo Excel tiene <strong>{sheets.length}</strong> hojas:
      </p>
      <ul className="grid gap-2">
        {sheets.map((name) => (
          <li key={name}>
            <button
              type="button"
              onClick={() => onPick(name)}
              disabled={busy}
              className={
                "flex w-full items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-left text-sm hover:bg-[var(--color-subtle)]" +
                (busy ? " pointer-events-none opacity-60" : "") +
                (current === name
                  ? " border-[var(--color-accent)] bg-[var(--color-subtle)]"
                  : "")
              }
            >
              <span className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
                {name}
              </span>
              {current === name ? <Badge variant="neutral">Actual</Badge> : null}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PreviewStep({
  preview,
  headerLabels,
  sampleData,
  mapping,
  onChangeMapping,
  missingName,
  needsMapping,
  strategy,
  onChangeStrategy,
  confidence = {},
  aiUsed = false,
}: {
  preview: ImportPreviewResult;
  headerLabels: (string | null)[];
  sampleData: (string | null)[][];
  mapping: Record<number, SystemField | "">;
  onChangeMapping: (idx: number, field: SystemField | "") => void;
  missingName: boolean;
  needsMapping: boolean;
  strategy: "merge" | "replace";
  onChangeStrategy: (s: "merge" | "replace") => void;
  confidence?: Record<number, number>;
  aiUsed?: boolean;
}) {
  const usedFields = new Set(
    Object.values(mapping).filter(Boolean) as SystemField[],
  );
  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-[1fr_auto] sm:items-center">
        <div className="text-xs text-[var(--color-tertiary)]">
          <span className="mr-3">
            Origen: <strong>{preview.source.toUpperCase()}</strong>
          </span>
          {preview.sheet_used ? (
            <span className="mr-3">
              Hoja: <strong>{preview.sheet_used}</strong>
            </span>
          ) : null}
          <span>
            Tareas detectadas: <strong>{preview.task_count}</strong>
          </span>
          {/* ENH-053: badge cuando la IA refinó el mapeo. */}
          {aiUsed ? (
            <span className="ml-3 inline-flex items-center rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
              ✨ Mapeo asistido por IA
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-[var(--color-tertiary)]">
            Estrategia
          </label>
          <Select
            value={strategy}
            onChange={(e) =>
              onChangeStrategy(e.target.value as "merge" | "replace")
            }
            aria-label="Estrategia de import"
          >
            <option value="merge">Merge por WBS</option>
            <option value="replace">Replace (reemplaza todo)</option>
          </Select>
        </div>
      </div>

      {missingName && needsMapping ? (
        <Banner variant="warning">
          <span className="inline-flex items-center gap-1.5">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            Asigná una columna al campo <strong>Nombre</strong> antes de confirmar.
          </span>
        </Banner>
      ) : null}

      {/* ENH-179: el mapeo se separa de la vista previa y se acomoda en una
          grilla de 2-3 columnas (antes era un dropdown alto por cada columna
          dentro del header de la tabla, que se estiraba a lo ancho y alto).
          Cada tarjeta muestra la columna, el campo destino y un valor de
          ejemplo para mapear con contexto. */}
      {needsMapping ? (
        <div>
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Mapeo de columnas
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {headerLabels.map((label, idx) => {
              const sample = sampleData.find((r) => r[idx] != null && r[idx] !== "")?.[idx];
              const lowConf =
                mapping[idx] &&
                (confidence[idx] ?? 0) < 0.7 &&
                (confidence[idx] ?? 0) > 0;
              return (
                <div
                  key={idx}
                  className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] px-2.5 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className="truncate text-[11px] font-medium text-[var(--color-secondary)]"
                      title={label ?? `Col ${idx + 1}`}
                    >
                      {label ?? `Col ${idx + 1}`}
                    </span>
                    {lowConf ? (
                      <span
                        className="shrink-0 text-[10px] text-amber-600"
                        title="La sugerencia tiene baja confianza — verifica el mapeo."
                      >
                        ⚠ baja confianza
                      </span>
                    ) : null}
                  </div>
                  <Select
                    className="mt-1 w-full text-[11px]"
                    value={mapping[idx] ?? ""}
                    onChange={(e) =>
                      onChangeMapping(idx, e.target.value as SystemField | "")
                    }
                    aria-label={`Mapeo de columna ${label ?? idx + 1}`}
                  >
                    <option value="">— ignorar —</option>
                    {SYSTEM_FIELDS.map((f) => (
                      <option
                        key={f}
                        value={f}
                        disabled={
                          mapping[idx] !== f && usedFields.has(f as SystemField)
                        }
                      >
                        {SYSTEM_FIELD_LABELS[f]}
                      </option>
                    ))}
                  </Select>
                  <div
                    className="mt-1 truncate text-[10px] text-[var(--color-tertiary)]"
                    title={sample != null ? String(sample) : ""}
                  >
                    {sample != null && sample !== "" ? `ej: ${sample}` : "sin datos"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Vista previa de datos: tabla compacta; el header muestra el campo
          destino asignado (si lo hay) en vez de repetir el dropdown. */}
      <div>
        {needsMapping ? (
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Vista previa
          </div>
        ) : null}
        <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-default)]">
          <table className="min-w-full text-xs">
            <thead className="bg-[var(--color-subtle)]">
              <tr>
                {headerLabels.map((label, idx) => (
                  <th
                    key={idx}
                    className="border-b border-[var(--border-default)] px-2 py-1.5 text-left align-top"
                  >
                    <div className="text-[11px] font-medium text-[var(--color-tertiary)]">
                      {label ?? `Col ${idx + 1}`}
                    </div>
                    {needsMapping && mapping[idx] ? (
                      <div className="mt-0.5 text-[10px] font-medium text-[var(--color-secondary)]">
                        → {SYSTEM_FIELD_LABELS[mapping[idx] as SystemField]}
                      </div>
                    ) : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sampleData.length === 0 ? (
                <tr>
                  <td
                    colSpan={Math.max(1, headerLabels.length)}
                    className="px-2 py-6 text-center text-[var(--color-tertiary)]"
                  >
                    Sin filas de muestra (archivo vacío después del header).
                  </td>
                </tr>
              ) : (
                sampleData.map((row, rIdx) => (
                  <tr key={rIdx} className="border-t border-[var(--border-subtle)]">
                    {headerLabels.map((_h, cIdx) => (
                      <td
                        key={cIdx}
                        className="px-2 py-1.5 text-[var(--color-secondary)]"
                      >
                        {row[cIdx] ?? <span className="text-[var(--color-tertiary)]">—</span>}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {preview.errors.length > 0 ? (
        <Banner variant="warning">
          <div className="text-xs">
            <strong>{preview.errors.length}</strong> filas con errores no
            críticos en el preview. Se omitirán al confirmar.
          </div>
        </Banner>
      ) : null}
    </div>
  );
}
