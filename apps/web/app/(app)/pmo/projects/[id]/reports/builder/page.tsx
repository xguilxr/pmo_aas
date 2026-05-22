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
import { useParams } from "next/navigation";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { CatalogSidebar } from "@/components/reports/builder/CatalogSidebar";
import { SectionCanvas } from "@/components/reports/builder/SectionCanvas";
import { PreviewPane } from "@/components/reports/builder/PreviewPane";
import {
  listSections,
  listBuilderTemplates,
  type ReportBuilderTemplate,
  type ReportSection,
  type RenderRequest,
} from "@/lib/api/report-builder";

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

  const [catalog, setCatalog] = useState<ReportSection[]>([]);
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);

  const [codes, setCodes] = useState<string[]>([]);
  const [compositionMode, setCompositionMode] = useState<"A" | "B">("A");
  const [windowDays, setWindowDays] = useState<number>(14);
  const [cutOff, setCutOff] = useState<string>(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  // 1) Catálogo + plantillas seed
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [sec, tpls] = await Promise.all([
          listSections({ level: 4 }),
          listBuilderTemplates({ level: 3 }),
        ]);
        if (cancelled) return;
        setCatalog(sec);
        setTemplates(tpls);
      } finally {
        if (!cancelled) setLoadingCatalog(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // 2) Hidratar canvas desde draft local
  useEffect(() => {
    if (!projectId) return;
    const d = loadDraft(projectId);
    if (d) {
      setCodes(d.codes);
      setCompositionMode(d.composition_mode);
      setCutOff(d.cut_off_date ?? cutOff);
      setWindowDays(d.window_days);
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
        params: {},
        updated_at: new Date().toISOString(),
      });
    }, AUTOSAVE_MS);
    return () => clearInterval(id);
  }, [projectId, codes, compositionMode, cutOff, windowDays]);

  const renderRequest = useMemo<RenderRequest | null>(() => {
    if (codes.length === 0) return null;
    // El motor necesita una plantilla; para preview construimos una
    // "plantilla efímera" usando una seed L3-AVANCE como base y
    // overriding section_codes. Como el backend no acepta inline
    // template aún (futuro endpoint), por ahora usamos la seed más
    // cercana al modo del canvas.
    const seed = templates.find(
      (t) => t.composition_mode === compositionMode && t.is_seed
    );
    if (!seed) return null;
    return {
      template: seed.id,
      project_id: projectId,
      level: 3,
      cut_off_date: cutOff,
      window_days: windowDays,
      // Override en frontend: para preview puramente declarativo, el
      // motor v1.0 ignora codes extra; el render fiel del canvas
      // sustituirá la seed por una custom (US-126 al guardar).
    };
  }, [codes, compositionMode, cutOff, windowDays, projectId, templates]);

  const handleAdd = useCallback(
    (code: string) => {
      if (codes.includes(code)) return;
      setCodes([...codes, code]);
      setSelectedCode(code);
    },
    [codes]
  );

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
            className="flex items-center gap-1 text-sm text-zinc-600 hover:text-zinc-900"
          >
            <ArrowLeft className="h-4 w-4" /> Reportes
          </Link>
          <h1 className="text-lg font-semibold text-zinc-900">Report Builder</h1>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-zinc-600">
            Modo
            <Select
              value={compositionMode}
              onChange={(e) => setCompositionMode(e.target.value as "A" | "B")}
              className="ml-1 inline-block h-8 w-auto"
            >
              <option value="A">A · por sección</option>
              <option value="B">B · por área</option>
            </Select>
          </label>
          <label className="text-xs text-zinc-600">
            Corte
            <input
              type="date"
              value={cutOff}
              onChange={(e) => setCutOff(e.target.value)}
              className="ml-1 h-8 rounded border border-zinc-300 px-2 text-xs"
            />
          </label>
          <label className="text-xs text-zinc-600">
            Ventana
            <input
              type="number"
              min={1}
              max={365}
              value={windowDays}
              onChange={(e) => setWindowDays(Number(e.target.value) || 14)}
              className="ml-1 h-8 w-16 rounded border border-zinc-300 px-2 text-xs"
            />
          </label>
          <Button variant="secondary" size="sm" disabled title="Llega en US-130/US-126">
            <Download className="mr-1 h-3.5 w-3.5" /> Exportar
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
              <SectionCanvas
                codes={codes}
                catalog={catalog}
                selectedCode={selectedCode}
                onReorder={handleReorder}
                onSelect={setSelectedCode}
                onRemove={handleRemove}
              />
            </div>
            <div className="w-[480px] border-l border-zinc-200">
              <PreviewPane request={renderRequest} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
