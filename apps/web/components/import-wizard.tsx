"use client";

import { AlertTriangle, FileSpreadsheet, Sparkles, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import {
  type ImportPreviewResult,
  type ImportSource,
  type ImportWarning,
  type ParsedPreviewTask,
  type SystemField,
  SYSTEM_FIELDS,
  SYSTEM_FIELD_LABELS,
  TASK_STATUS_LABEL,
  importAiStructure,
  importConfirm,
  importPreview,
  importRepreview,
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
  // ENH-192: interpretación en vivo — tareas parseadas, warnings y count
  // se refrescan vía /repreview cuando el usuario re-mapea columnas.
  const [parsedPreview, setParsedPreview] = useState<ParsedPreviewTask[]>([]);
  const [liveWarnings, setLiveWarnings] = useState<ImportWarning[]>([]);
  const [liveTaskCount, setLiveTaskCount] = useState(0);
  // US-188 nivel 3: la vista previa actual es una propuesta de la IA;
  // el confirm la persiste tal cual (ignora el mapeo de columnas).
  const [aiStructure, setAiStructure] = useState(false);
  // US-189: resumen del import para el paso final en lenguaje llano.
  const [doneSummary, setDoneSummary] = useState<{
    imported: number;
    aiStatuses: number;
    aiResources: number;
  } | null>(null);
  const repreviewSeq = useRef(0);
  const mappingTouched = useRef(false);

  function reset() {
    setStep("upload");
    setFile(null);
    setPreview(null);
    setSheet(null);
    setMapping({});
    setConfidence({});
    setAiUsed(false);
    setParsedPreview([]);
    setLiveWarnings([]);
    setLiveTaskCount(0);
    setAiStructure(false);
    setDoneSummary(null);
    mappingTouched.current = false;
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
      // ENH-192: estado inicial de la interpretación en vivo.
      setParsedPreview(result.parsed_preview ?? []);
      setLiveWarnings(result.warnings ?? []);
      setLiveTaskCount(result.task_count);
      setAiStructure(false);
      mappingTouched.current = false;
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
          // US-188 nivel 1: mandar filas de muestra para que la IA
          // mapee por contenido, no solo por nombre de header.
          const sug = await suggestImportMapping(
            projectId,
            headers,
            result.sample_rows.slice(1, 6),
          );
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

  // US-188 nivel 3: pedir a la IA que interprete el archivo completo.
  async function aiInterpret() {
    if (!preview || busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await importAiStructure(projectId, preview.job_id);
      setParsedPreview(r.parsed_preview);
      setLiveWarnings(r.warnings);
      setLiveTaskCount(r.task_count);
      setAiStructure(true);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "La IA no pudo interpretar el archivo",
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      // US-188: con propuesta IA activa el mapeo de columnas no aplica —
      // se persiste exactamente lo que muestra la vista previa.
      if (aiStructure) {
        if (strategy === "replace") {
          const ok = window.confirm(
            "Estrategia REPLACE: se eliminarán todas las tareas actuales del proyecto antes de importar. ¿Continuar?",
          );
          if (!ok) {
            setBusy(false);
            return;
          }
        }
        const result = await importConfirm(projectId, preview.job_id, {
          mapping: null,
          strategy,
          use_ai_structure: true,
        });
        setDoneSummary({
          imported: result.imported,
          aiStatuses: result.ai_normalized?.statuses ?? 0,
          aiResources: result.ai_normalized?.resources ?? 0,
        });
        onImported(result.imported);
        setStep("done");
        return;
      }
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
      setDoneSummary({
        imported: result.imported,
        aiStatuses: result.ai_normalized?.statuses ?? 0,
        aiResources: result.ai_normalized?.resources ?? 0,
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

  // ENH-192: al re-mapear columnas, re-interpretar el archivo (debounce
  // 400ms) para refrescar la tabla interpretada + warnings en vivo.
  useEffect(() => {
    if (!preview || step !== "preview" || !NEEDS_MAPPING.includes(preview.source)) {
      return;
    }
    // US-188: con propuesta IA activa el mapeo no aplica.
    if (aiStructure) return;
    if (!mappingTouched.current) return;
    const inverted: Partial<Record<SystemField, number>> = {};
    for (const [colIdxStr, field] of Object.entries(mapping)) {
      if (!field) continue;
      inverted[field as SystemField] = Number(colIdxStr);
    }
    const seq = ++repreviewSeq.current;
    const timer = window.setTimeout(async () => {
      try {
        const r = await importRepreview(
          projectId,
          preview.job_id,
          Object.keys(inverted).length > 0 ? inverted : null,
        );
        if (seq !== repreviewSeq.current) return; // respuesta vieja
        setParsedPreview(r.parsed_preview);
        setLiveWarnings(r.warnings);
        setLiveTaskCount(r.task_count);
      } catch {
        /* interpretación en vivo es best-effort; el confirm re-valida. */
      }
    }, 400);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapping, preview, projectId, step, aiStructure]);

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
        canConfirm: !!preview && (aiStructure || !needsMapping || !missingName),
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
          onChangeMapping={(idx, field) => {
            mappingTouched.current = true;
            setMapping((m) => ({ ...m, [idx]: field }));
          }}
          missingName={Boolean(missingName)}
          needsMapping={needsMapping}
          strategy={strategy}
          onChangeStrategy={setStrategy}
          confidence={confidence}
          aiUsed={aiUsed}
          parsedPreview={parsedPreview}
          warnings={liveWarnings}
          taskCount={liveTaskCount}
          aiStructure={aiStructure}
          onAiInterpret={aiInterpret}
          busy={busy}
        />
      ) : null}

      {step === "done" ? (
        <div className="space-y-2 text-center">
          <p className="text-sm font-semibold text-[var(--color-success-fg)]">
            ✓ Listo — se importaron {doneSummary?.imported ?? 0} tareas
          </p>
          {/* US-188 nivel 2: transparencia de lo que normalizó la IA. */}
          {doneSummary && (doneSummary.aiStatuses > 0 || doneSummary.aiResources > 0) ? (
            <p className="text-xs text-[var(--color-tertiary)]">
              ✨ La IA normalizó {doneSummary.aiStatuses} estado(s) y
              asignó {doneSummary.aiResources} responsable(s).
            </p>
          ) : null}
          <p className="text-sm text-[var(--color-secondary)]">
            Cerrá esta ventana para ver tu plan actualizado.
          </p>
        </div>
      ) : null}
    </Modal>
  );
}

// US-189: títulos y descripciones en lenguaje llano (sin jerga PM).
function titleFor(step: Step, _source?: ImportSource): string {
  if (step === "upload") return "Importar plan — subí tu archivo";
  if (step === "sheet") return "Importar plan — elegí la hoja";
  if (step === "preview") return "Importar plan — revisá y confirmá";
  return "Importar plan";
}

function descriptionFor(
  step: Step,
  preview: ImportPreviewResult | null,
): string | undefined {
  if (step === "upload") {
    return "Subí el archivo con tu plan de trabajo. Máximo 10 MB.";
  }
  if (step === "sheet") {
    return "El Excel tiene varias hojas — elegí la que contiene el plan.";
  }
  if (step === "preview") {
    if (preview && !NEEDS_MAPPING.includes(preview.source)) {
      return "Este formato ya viene listo. Revisá el resumen y dale Importar.";
    }
    return "Así quedará tu plan. Si algo no cuadra, ajustá las columnas o dejá que la IA interprete el archivo.";
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
  // US-189: drag & drop además del click — y copy en lenguaje llano
  // para gente que no es PM.
  const [dragging, setDragging] = useState(false);
  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (busy) return;
        const f = e.dataTransfer.files?.[0];
        if (f) void onFile(f);
      }}
      className={
        "flex flex-col items-center gap-2 rounded-[var(--radius-xl)] border-2 border-dashed py-10 text-center cursor-pointer hover:border-[var(--color-accent)] hover:bg-[var(--color-surface)]" +
        (dragging
          ? " border-[var(--color-accent)] bg-[var(--color-surface)]"
          : " border-[var(--border-default)] bg-[var(--color-subtle)]") +
        (busy ? " pointer-events-none opacity-60" : "")
      }
    >
      <Upload className="h-8 w-8 text-[var(--color-tertiary)]" aria-hidden />
      <span className="text-sm font-medium text-[var(--color-primary)]">
        {busy ? "Procesando…" : "Arrastrá tu archivo aquí o hacé click"}
      </span>
      <span className="text-xs text-[var(--color-tertiary)]">
        Sirve la plantilla del sistema o tu propio Excel — también .csv,
        .mpp y .xml de MS Project.
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
  parsedPreview = [],
  warnings = [],
  taskCount = 0,
  aiStructure = false,
  onAiInterpret,
  busy = false,
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
  parsedPreview?: ParsedPreviewTask[];
  warnings?: ImportWarning[];
  taskCount?: number;
  aiStructure?: boolean;
  onAiInterpret?: () => void;
  busy?: boolean;
}) {
  const usedFields = new Set(
    Object.values(mapping).filter(Boolean) as SystemField[],
  );
  return (
    <div className="space-y-3">
      {/* US-189: resumen en lenguaje llano — lo primero que se lee. */}
      <div
        className={
          "rounded-[var(--radius-md)] border px-3 py-2 text-sm font-medium " +
          (taskCount > 0
            ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
            : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300")
        }
      >
        {taskCount > 0 ? (
          <>
            Se importarán <strong>{taskCount}</strong> tareas
            {warnings.length > 0
              ? ` · ${warnings.length} aviso${warnings.length > 1 ? "s" : ""} para revisar`
              : " · todo se ve bien"}
          </>
        ) : (
          <>
            No reconocimos las columnas de tu archivo. Probá
            {" "}
            <strong>Interpretar archivo con IA</strong> o ajustá las
            columnas manualmente abajo.
          </>
        )}
      </div>

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
          {/* ENH-053: badge cuando la IA refinó el mapeo. */}
          {aiUsed && !aiStructure ? (
            <span className="ml-3 inline-flex items-center rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
              ✨ Mapeo asistido por IA
            </span>
          ) : null}
          {/* US-188 nivel 3: la vista previa es una propuesta de la IA. */}
          {aiStructure ? (
            <span className="ml-3 inline-flex items-center gap-1 rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
              <Sparkles className="h-3 w-3" aria-hidden />
              Plan interpretado por IA — revisá antes de importar
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-[var(--color-tertiary)]">
            Al importar
          </label>
          <Select
            value={strategy}
            onChange={(e) =>
              onChangeStrategy(e.target.value as "merge" | "replace")
            }
            aria-label="Estrategia de import"
          >
            {/* US-189: opciones en lenguaje llano. */}
            <option value="merge">Agregar y actualizar tareas</option>
            <option value="replace">Reemplazar todo el plan</option>
          </Select>
        </div>
      </div>

      {missingName && needsMapping && !aiStructure ? (
        <Banner variant="warning">
          <span className="inline-flex items-center gap-1.5">
            <AlertTriangle className="h-4 w-4" aria-hidden />
            Asigná una columna al campo <strong>Nombre</strong> antes de
            confirmar, o dejá que la IA interprete el archivo.
          </span>
        </Banner>
      ) : null}

      {/* US-188 nivel 3: interpretación completa con IA — útil cuando el
          archivo no tiene headers reconocibles o viene "sucio". */}
      {needsMapping && onAiInterpret && !aiStructure ? (
        <div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={onAiInterpret}
            disabled={busy}
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            {busy ? "Interpretando…" : "Interpretar archivo con IA"}
          </Button>
        </div>
      ) : null}

      {/* BUG-088 + ENH-192: avisos no bloqueantes en vivo (WBS numérico,
          huérfanos, % dudoso, estados no reconocidos). */}
      {warnings.length > 0 ? (
        <Banner variant="warning">
          <ul className="space-y-1">
            {warnings.map((w) => (
              <li key={w.code} className="flex items-start gap-1.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                <span>{w.message}</span>
              </li>
            ))}
          </ul>
        </Banner>
      ) : null}

      {/* ENH-179: el mapeo se separa de la vista previa y se acomoda en una
          grilla de 2-3 columnas (antes era un dropdown alto por cada columna
          dentro del header de la tabla, que se estiraba a lo ancho y alto).
          Cada tarjeta muestra la columna, el campo destino y un valor de
          ejemplo para mapear con contexto. */}
      {/* US-189: el mapeo de columnas es detalle avanzado — colapsado
          cuando el auto-detect funcionó, abierto si falta lo esencial. */}
      {needsMapping && !aiStructure ? (
        <details open={missingName || taskCount === 0}>
          <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Ajustar columnas (avanzado)
          </summary>
          <div className="mt-1.5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
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
        </details>
      ) : null}

      {/* ENH-192 + ENH-199: vista previa INTERPRETADA con el look de la
          tabla del plan — jerarquía indentada por WBS, chips de estado
          con color, hitos ◆ — y scroll para ver varias líneas. */}
      {parsedPreview.length > 0 ? (
        <div>
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Así se verá en el sistema
            {taskCount > parsedPreview.length
              ? ` (primeras ${parsedPreview.length} de ${taskCount})`
              : ` (${parsedPreview.length} tareas)`}
          </div>
          <div className="max-h-[340px] overflow-auto rounded-[var(--radius-md)] border border-[var(--border-default)]">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 z-10 bg-[var(--color-subtle)]">
                <tr>
                  {[
                    "WBS",
                    "Tarea",
                    "Inicio",
                    "Fin",
                    "%",
                    "Estado",
                    "Área",
                    "Responsable",
                    "Pred.",
                  ].map((h) => (
                    <th
                      key={h}
                      className="border-b border-[var(--border-default)] px-2 py-1.5 text-left text-[11px] font-medium text-[var(--color-tertiary)]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parsedPreview.map((t) => {
                  const depth = t.wbs
                    ? Math.max(0, t.wbs.split(".").filter(Boolean).length - 1)
                    : 0;
                  return (
                    <tr
                      key={t.row_number}
                      className="border-t border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                    >
                      <td className="px-2 py-1.5 tabular-nums text-[var(--color-tertiary)]">
                        {t.wbs ?? "—"}
                      </td>
                      <td
                        className="max-w-[260px] truncate px-2 py-1.5 text-[var(--color-primary)]"
                        style={{ paddingLeft: `${8 + depth * 16}px` }}
                        title={t.name}
                      >
                        {t.is_milestone ? (
                          <span className="mr-1 text-purple-600">◆</span>
                        ) : null}
                        {t.name}
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-[var(--color-secondary)]">
                        {t.start_date ?? "—"}
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-[var(--color-secondary)]">
                        {t.end_date ?? "—"}
                      </td>
                      <td className="px-2 py-1.5 tabular-nums text-[var(--color-secondary)]">
                        {t.progress}%
                      </td>
                      <td className="px-2 py-1.5">
                        {/* ENH-199: chip de color como en el plan (ENH-188). */}
                        <span
                          className={
                            "inline-flex whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-semibold " +
                            (t.status === "completed"
                              ? "bg-emerald-100 text-emerald-700"
                              : t.status === "in_progress"
                                ? "bg-blue-100 text-blue-700"
                                : t.status === "on_hold"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-slate-100 text-slate-600")
                          }
                        >
                          {t.status
                            ? (TASK_STATUS_LABEL[t.status] ?? t.status)
                            : "No iniciada"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-[var(--color-secondary)]">
                        {t.area ?? "—"}
                      </td>
                      <td className="max-w-[140px] truncate px-2 py-1.5 text-[var(--color-secondary)]" title={t.resources ?? ""}>
                        {t.resources ?? "—"}
                      </td>
                      <td className="px-2 py-1.5 tabular-nums text-[var(--color-secondary)]">
                        {t.predecessors ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* Datos crudos del archivo — colapsados; útiles para re-mapear
          columnas con contexto. Si no hay interpretación (mapping sin
          'Nombre'), quedan como única vista. */}
      <details open={parsedPreview.length === 0}>
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
          Datos crudos del archivo
        </summary>
        <div className="mt-1.5 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-default)]">
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
      </details>

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
