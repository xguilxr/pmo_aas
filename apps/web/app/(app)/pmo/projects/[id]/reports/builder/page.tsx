"use client";

/**
 * US-124 — Canvas drag-and-drop + preview en vivo (EP020 Report Builder).
 *
 * Layout: catálogo lateral filtrable + canvas central con drag-drop +
 * preview en vivo (debounced 500ms). El panel de parámetros y el
 * modal "guardar plantilla" llegan en US-125 y US-126.
 *
 * Persistencia local del canvas: localStorage (`report_draft_<pid>`).
 * Autosave cada 30 s.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Eye, ArrowLeft, FileDown, Loader2, Save, Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { CatalogSidebar } from "@/components/reports/builder/CatalogSidebar";
import { ChatPanel } from "@/components/reports/builder/ChatPanel";
import { SectionCanvas } from "@/components/reports/builder/SectionCanvas";
import { PreviewPane } from "@/components/reports/builder/PreviewPane";
import { SaveTemplateModal } from "@/components/reports/builder/SaveTemplateModal";
import { type SectionParams } from "@/components/reports/builder/SectionParamsPanel";
import { TemplatesGallery } from "@/components/reports/builder/TemplatesGallery";
import { listAreasByProject } from "@/lib/api/areas";
import {
  deleteBuilderTemplate,
  listSections,
  listBuilderTemplates,
  renderBuilderPdf,
  saveBuilderReport,
  updateBuilderTemplate,
  type ChatAction,
  type ReportBuilderTemplate,
  type ReportSection,
  type RenderRequest,
} from "@/lib/api/report-builder";
import { getStoredUser } from "@/lib/auth-storage";
import { confirmarDestructivo } from "@/lib/confirmar";

type DraftShape = {
  codes: string[];
  composition_mode: "A" | "B";
  cut_off_date: string | null;
  window_days: number;
  params: Record<string, Record<string, unknown>>;
  template_id?: string | null;
  updated_at: string;
};

const AUTOSAVE_MS = 30_000;

function draftKey(projectId: string) {
  return `report_draft_${projectId}`;
}

function loadDraft(projectId: string): DraftShape | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(draftKey(projectId));
    return raw ? (JSON.parse(raw) as DraftShape) : null;
  } catch {
    return null;
  }
}

function saveDraft(projectId: string, d: DraftShape) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(draftKey(projectId), JSON.stringify(d));
  } catch {
    /* quota / private mode → drop silently */
  }
}

export default function ReportBuilderPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";
  // ENH-125: ?template_id=X carga una plantilla existente al entrar.
  const searchParams = useSearchParams();
  const initialTemplateId = searchParams?.get("template_id") ?? null;

  const [catalog, setCatalog] = useState<ReportSection[]>([]);
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);

  const [codes, setCodes] = useState<string[]>([]);
  const [compositionMode, setCompositionMode] = useState<"A" | "B">("A");
  const [windowDays, setWindowDays] = useState<number>(14);
  // US-148: ventana = value + unit (UI). Internamente sigue siendo
  // windowDays (int) — el motor de US-123 trabaja en días. La conversión
  // se hace al cambiar unit o value.
  const [windowValue, setWindowValue] = useState<number>(2);
  const [windowUnit, setWindowUnit] = useState<"days" | "weeks" | "months">("weeks");
  // BUG-063: el corte ya NO se configura en la plantilla — se fija
  // automáticamente a "hoy" al generar/preview. Mantenemos `cutOff`
  // como constante interna para el render request.
  const cutOff = useMemo(() => new Date().toISOString().slice(0, 10), []);
  // BUG-063: filtro de área a nivel reporte (barra superior).
  const [areaId, setAreaId] = useState<string>("");
  const [areas, setAreas] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  // US-125 — params por sección (map code → params).
  const [paramsByCode, setParamsByCode] = useState<Record<string, SectionParams>>({});
  // US-126 — modal "Guardar como plantilla" + plantilla cargada.
  const [saveOpen, setSaveOpen] = useState(false);
  const [loadedTemplateId, setLoadedTemplateId] = useState<string | null>(null);
  // ENH-139/140: estados de Visualizar y Guardar Reporte.
  const [visualizing, setVisualizing] = useState(false);
  const [savingReport, setSavingReport] = useState(false);
  const [currentUserId] = useState<string | null>(() => getStoredUser()?.id ?? null);
  // US-127 — chat IA.
  const [chatOpen, setChatOpen] = useState(false);

  async function refreshTemplates() {
    const tpls = await listBuilderTemplates({});
    setTemplates(tpls);
  }

  // 1) Catálogo + plantillas (seeds + propias + del proyecto)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [sec, tpls, projectAreas] = await Promise.all([
          listSections({ level: 4 }),
          listBuilderTemplates({}),
          listAreasByProject(projectId).catch(() => []),
        ]);
        if (cancelled) return;
        setCatalog(sec);
        setTemplates(tpls);
        setAreas(projectAreas.map((a) => ({ id: a.id, name: a.name })));
        // ENH-125: si vino ?template_id=X en la URL, cargar esa plantilla
        // directamente. Útil cuando el PM hace click en "Editar" desde
        // el listado de plantillas en /reports.
        if (initialTemplateId) {
          const found = tpls.find((t) => t.id === initialTemplateId);
          if (found) {
            loadTemplateIntoCanvas(found);
          }
        }
      } finally {
        if (!cancelled) setLoadingCatalog(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTemplateId]);

  // 2) Hidratar canvas desde draft local
  useEffect(() => {
    if (!projectId) return;
    const d = loadDraft(projectId);
    if (d) {
      setCodes(d.codes);
      setCompositionMode(d.composition_mode);
      // BUG-063: el corte ya no se restaura del draft — es siempre hoy.
      setWindowDays(d.window_days);
      if (d.params) setParamsByCode(d.params);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // 3) Autosave cada 30s
  useEffect(() => {
    if (!projectId) return;
    const id = setInterval(() => {
      saveDraft(projectId, {
        codes,
        composition_mode: compositionMode,
        cut_off_date: cutOff,
        window_days: windowDays,
        params: paramsByCode,
        updated_at: new Date().toISOString(),
      });
    }, AUTOSAVE_MS);
    return () => clearInterval(id);
  }, [projectId, codes, compositionMode, cutOff, windowDays, paramsByCode]);

  // ENH-125 — dirty flag: hay cambios sin guardar si el canvas no está
  // vacío Y no hay loadedTemplateId (i.e. plantilla efímera no persistida).
  // Para plantillas cargadas, no rastreamos diff fino (queda como mejora);
  // hoy asumimos que cargada = no dirty hasta que owner pida más.
  const isDirty = codes.length > 0 && !loadedTemplateId;

  useEffect(() => {
    function beforeUnload(e: BeforeUnloadEvent) {
      if (!isDirty) return;
      e.preventDefault();
      // Browsers ignoran custom strings y muestran su propio prompt.
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [isDirty]);

  const renderRequest = useMemo<RenderRequest | null>(() => {
    if (codes.length === 0) return null;
    // ENH-138: preview fiel del canvas. Enviamos los codes + modo inline;
    // el backend arma una plantilla efímera y renderiza data real.
    return {
      section_codes: codes,
      composition_mode: compositionMode,
      project_id: projectId,
      level: 3,
      cut_off_date: cutOff,
      window_days: windowDays,
      area_id: areaId || null,
      params: paramsByCode,
    };
  }, [codes, compositionMode, cutOff, windowDays, areaId, projectId, paramsByCode]);

  const handleAdd = useCallback(
    (code: string) => {
      if (codes.includes(code)) return;
      setCodes([...codes, code]);
      setSelectedCode(code);
    },
    [codes]
  );

  const loadTemplateIntoCanvas = useCallback(
    (tpl: ReportBuilderTemplate) => {
      setCodes(tpl.section_codes);
      setCompositionMode(tpl.composition_mode);
      const params = (tpl.default_parameters as Record<string, SectionParams>) ?? {};
      setParamsByCode(params);
      setLoadedTemplateId(tpl.is_seed ? null : tpl.id);
      setSelectedCode(null);
      // US-148: si la plantilla persistió ventana de tiempo en
      // `_template`, restaurarla en el header.
      const tmplMeta = (params as Record<string, unknown>)._template as
        | { window_days?: number; window_value?: number; window_unit?: string }
        | undefined;
      if (tmplMeta?.window_days && Number.isFinite(tmplMeta.window_days)) {
        setWindowDays(tmplMeta.window_days);
      }
      if (tmplMeta?.window_value && Number.isFinite(tmplMeta.window_value)) {
        setWindowValue(tmplMeta.window_value);
      }
      if (tmplMeta?.window_unit === "days" || tmplMeta?.window_unit === "weeks" || tmplMeta?.window_unit === "months") {
        setWindowUnit(tmplMeta.window_unit);
      }
    },
    []
  );

  async function togglePublish(tpl: ReportBuilderTemplate) {
    const newVisibility = tpl.visibility === "project" ? "private" : "project";
    await updateBuilderTemplate(tpl.id, {
      visibility: newVisibility,
      ...(newVisibility === "project" ? { project_id: projectId } : {}),
    });
    await refreshTemplates();
  }

  async function removeTemplate(tpl: ReportBuilderTemplate) {
    if (
      !confirmarDestructivo({
        objeto: `la plantilla «${tpl.name}»`,
        consecuencia: "Los informes ya generados con ella no se tocan; deja de poder usarse para nuevos.",
        reversibilidad: "definitiva",
      })
    )
      return;
    await deleteBuilderTemplate(tpl.id);
    if (loadedTemplateId === tpl.id) setLoadedTemplateId(null);
    await refreshTemplates();
  }

  // ENH-139: abre un PDF del preview real (canvas inline, sin persistir).
  async function handleVisualize() {
    if (!renderRequest) {
      window.alert("Agrega al menos una sección al canvas.");
      return;
    }
    setVisualizing(true);
    try {
      const blob = await renderBuilderPdf(renderRequest);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      // No revocamos de inmediato para que la pestaña pueda cargar el PDF.
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Error al visualizar");
    } finally {
      setVisualizing(false);
    }
  }

  // ENH-140: persiste un snapshot del reporte en el Historial del proyecto.
  async function handleSaveReport() {
    if (!renderRequest) {
      window.alert("Agrega al menos una sección al canvas.");
      return;
    }
    const name = window.prompt("Nombre del reporte:", "Reporte custom");
    if (name === null) return;
    setSavingReport(true);
    try {
      await saveBuilderReport({ ...renderRequest, name: name.trim() || "Reporte custom" });
      window.alert("Reporte guardado en el Historial del proyecto.");
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Error al guardar el reporte");
    } finally {
      setSavingReport(false);
    }
  }

  /** US-127 — aplica acciones devueltas por la IA al canvas y devuelve
   *  un undo handle que el ChatPanel guarda para que el PM revierta. */
  function applyChatActions(actions: ChatAction[]): () => void {
    const prevCodes = [...codes];
    const prevParams = { ...paramsByCode };
    let nextCodes = [...codes];
    let nextParams = { ...paramsByCode };
    for (const a of actions) {
      if (a.type === "add_section" && a.code && !nextCodes.includes(a.code)) {
        nextCodes = [...nextCodes, a.code];
      } else if (
        a.type === "remove_section" &&
        a.index !== null &&
        a.index !== undefined &&
        a.index >= 0 &&
        a.index < nextCodes.length
      ) {
        const removed = nextCodes[a.index];
        nextCodes = nextCodes.filter((_, i) => i !== a.index);
        if (removed) {
          const np = { ...nextParams };
          delete np[removed];
          nextParams = np;
        }
      } else if (
        a.type === "update_section_params" &&
        a.index !== null &&
        a.index !== undefined &&
        nextCodes[a.index]
      ) {
        const code = nextCodes[a.index];
        nextParams = {
          ...nextParams,
          [code]: { ...(nextParams[code] ?? {}), ...(a.params ?? {}) },
        };
      } else if (
        a.type === "reorder_section" &&
        a.index !== null &&
        a.index !== undefined &&
        a.to !== null &&
        a.to !== undefined &&
        a.index >= 0 &&
        a.to >= 0 &&
        a.index < nextCodes.length &&
        a.to < nextCodes.length
      ) {
        const moved = nextCodes[a.index];
        nextCodes = nextCodes.filter((_, i) => i !== a.index);
        nextCodes.splice(a.to, 0, moved);
      }
    }
    setCodes(nextCodes);
    setParamsByCode(nextParams);
    return () => {
      setCodes(prevCodes);
      setParamsByCode(prevParams);
    };
  }

  const handleReorder = useCallback((next: string[]) => setCodes(next), []);
  const handleRemove = useCallback(
    (code: string) => {
      setCodes(codes.filter((c) => c !== code));
      if (selectedCode === code) setSelectedCode(null);
    },
    [codes, selectedCode]
  );

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-2">
        <div className="flex items-center gap-3">
          <Link
            href={`/pmo/projects/${projectId}/reports`}
            onClick={(e) => {
              // ENH-125: confirma antes de salir si hay cambios sin guardar.
              if (isDirty && !window.confirm("Tienes cambios sin guardar. ¿Salir sin guardar la plantilla?")) {
                e.preventDefault();
              }
            }}
            className="flex items-center gap-1 text-sm text-zinc-600 hover:text-zinc-900"
          >
            <ArrowLeft className="h-4 w-4" /> Reportes
          </Link>
          <h1 className="text-lg font-semibold text-zinc-900">Report Builder</h1>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-zinc-600">
            Agrupación
            <Select
              value={compositionMode}
              onChange={(e) => setCompositionMode(e.target.value as "A" | "B")}
              className="ml-1 inline-block h-8 w-auto"
              title="Por sección: cada sección ordena sus items por área. Por área: agrupa todas las secciones bajo cada área."
            >
              <option value="A">Por sección</option>
              <option value="B">Por área</option>
            </Select>
          </label>
          <label className="text-xs text-zinc-600">
            Área
            <Select
              value={areaId}
              onChange={(e) => setAreaId(e.target.value)}
              className="ml-1 inline-block h-8 w-auto"
              title="Filtra el contenido del reporte a una sola área."
            >
              <option value="">Todas</option>
              {/* DIS-03: el proyecto puede no tener áreas asignadas todavía. */}
              {areas.length === 0 ? (
                <option value="" disabled>
                  (este proyecto aún no tiene áreas)
                </option>
              ) : null}
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </label>
          <label className="flex items-center gap-1 text-xs text-zinc-600">
            Ventana
            <input
              type="number"
              min={1}
              max={52}
              value={windowValue}
              onChange={(e) => {
                const v = Math.max(1, Number(e.target.value) || 2);
                setWindowValue(v);
                const mult = { days: 1, weeks: 7, months: 30 }[windowUnit];
                setWindowDays(v * mult);
              }}
              className="h-8 w-14 rounded border border-zinc-300 px-2 text-xs"
            />
            <Select
              value={windowUnit}
              onChange={(e) => {
                const unit = e.target.value as "days" | "weeks" | "months";
                setWindowUnit(unit);
                const mult = { days: 1, weeks: 7, months: 30 }[unit];
                setWindowDays(windowValue * mult);
              }}
              className="h-8 w-auto text-xs"
            >
              <option value="days">días</option>
              <option value="weeks">semanas</option>
              <option value="months">mes</option>
            </Select>
          </label>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setChatOpen(true)}
            title="Abrir chat IA"
          >
            <Sparkles className="mr-1 h-3.5 w-3.5 text-violet-500" /> IA
          </Button>
          {/* ENH-139/140: orden Visualizar · Guardar Reporte · Guardar Plantilla. */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleVisualize}
            disabled={codes.length === 0 || visualizing}
            loading={visualizing}
            title="Abrir un PDF del preview real"
          >
            <Eye className="mr-1 h-3.5 w-3.5" /> Visualizar
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSaveReport}
            disabled={codes.length === 0 || savingReport}
            loading={savingReport}
            title="Guardar el reporte en el Historial del proyecto"
          >
            <FileDown className="mr-1 h-3.5 w-3.5" /> Guardar Reporte
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSaveOpen(true)}
            disabled={codes.length === 0}
            title="Guardar la composición como plantilla reusable"
          >
            <Save className="mr-1 h-3.5 w-3.5" /> Guardar Plantilla
          </Button>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        {loadingCatalog ? (
          <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Cargando catálogo…
          </div>
        ) : (
          <>
            <CatalogSidebar
              sections={catalog}
              selectedCodes={codes}
              onAdd={handleAdd}
            />
            <div className="flex flex-1 flex-col border-r border-zinc-200">
              <TemplatesGallery
                templates={templates}
                currentUserId={currentUserId}
                projectId={projectId}
                onLoad={loadTemplateIntoCanvas}
                onTogglePublish={togglePublish}
                onDelete={removeTemplate}
              />
              {/* BUG-063: contenido editable por sección — cada item del
                  canvas despliega sus parámetros inline con el botón de
                  settings (similar al editor de minutas). */}
              <SectionCanvas
                codes={codes}
                catalog={catalog}
                selectedCode={selectedCode}
                paramsByCode={paramsByCode}
                onReorder={handleReorder}
                onSelect={setSelectedCode}
                onRemove={handleRemove}
                onParamsChange={(code, next) =>
                  setParamsByCode({ ...paramsByCode, [code]: next })
                }
              />
            </div>
            {/* BUG-063: columna derecha solo Preview, siempre visible y
                actualizándose en vivo (el propio PreviewPane trae su
                header + estado de render). */}
            <div className="flex w-[480px] flex-col border-l border-zinc-200">
              <PreviewPane request={renderRequest} />
            </div>
          </>
        )}
      </main>

      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        canvasCodes={codes}
        compositionMode={compositionMode}
        onApplyActions={applyChatActions}
      />

      <SaveTemplateModal
        open={saveOpen}
        onClose={() => setSaveOpen(false)}
        defaults={{
          level: 4,
          composition_mode: compositionMode,
          section_codes: codes,
          // US-148: persistir ventana de tiempo en `default_parameters._template`
          // (bucket reservado para metadata global de la plantilla — sin migración).
          default_parameters: {
            ...paramsByCode,
            _template: {
              window_days: windowDays,
              window_value: windowValue,
              window_unit: windowUnit,
            },
          },
          project_id: projectId,
        }}
        onSaved={async (id) => {
          setLoadedTemplateId(id);
          await refreshTemplates();
        }}
      />
    </div>
  );
}
