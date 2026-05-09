"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Download,
  FileText,
  Layout,
  Save,
  Sparkles,
  Undo2,
  Wand2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiBase } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";
import { tweakReportHTML } from "@/lib/api/ai";
import {
  createReportTemplate,
  getReportTemplate,
  listReportTemplates,
  type ReportTemplateMini,
} from "@/lib/api/report-templates";

/**
 * US-109 — panel de creación de reporte con tweaker IA.
 *
 * Flujo:
 * 1. Modo entrada (`?mode=new` o `?mode=template`):
 *    - "new": carga el HTML default del proyecto vía
 *      POST /projects/{id}/reports/render-default-html (CA2).
 *    - "template": modal selector de plantillas guardadas (ENH-085 →
 *      CA7); al elegir, el HTML de la plantilla es el punto de partida.
 * 2. Panel izquierdo: textarea "instrucciones" + botón Aplicar →
 *    `POST /api/v1/ai/reports/tweak-html` (CA3).
 * 3. iframe con `srcdoc` muestra el HTML actual.
 * 4. Historial in-memory de hasta 10 versiones (CA6); botón Deshacer.
 * 5. Header: Guardar reporte / Guardar como plantilla (CA8 — la
 *    creación de Report la hace ENH-085 follow-up; aquí guardamos en
 *    `report_templates` con name + html).
 */

const MAX_HISTORY = 10;

function Inner() {
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const queryMode = search.get("mode") as "new" | "template" | null;

  // CA1: si no hay mode, mostramos el panel con 2 botones para que el
  // PM elija punto de partida. Una vez elegido, mode pasa a "new" o
  // "template" y arranca el flujo correspondiente.
  const [mode, setMode] = useState<"new" | "template" | null>(queryMode);
  const [html, setHtml] = useState<string>("");
  const [history, setHistory] = useState<string[]>([]);
  const [loading, setLoading] = useState(queryMode === "new");
  const [error, setError] = useState<string | null>(null);

  const [instruction, setInstruction] = useState("");
  const [tweaking, setTweaking] = useState(false);
  const [modelUsed, setModelUsed] = useState<string | null>(null);

  // Modales
  const [pickTemplate, setPickTemplate] = useState(queryMode === "template");
  const [templates, setTemplates] = useState<ReportTemplateMini[]>([]);
  const [tplLoading, setTplLoading] = useState(false);

  const [saveTemplate, setSaveTemplate] = useState(false);
  const [tplName, setTplName] = useState("");
  const [tplDescription, setTplDescription] = useState("");
  const [savingTpl, setSavingTpl] = useState(false);

  async function startNewMode() {
    setMode("new");
    setLoading(true);
    setError(null);
    try {
      const token = getAccessToken();
      const res = await fetch(
        `${apiBase()}/api/v1/projects/${id}/reports/render-default-html`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: "include",
        },
      );
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const text = await res.text();
      setHtml(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el render default");
    } finally {
      setLoading(false);
    }
  }

  // CA2: si arrancamos con `?mode=new`, lanza el render default al montar.
  useEffect(() => {
    if (queryMode === "new" && !html && mode === "new") {
      void startNewMode();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryMode]);

  // CA7: lista de plantillas para el modal selector.
  useEffect(() => {
    if (!pickTemplate) return;
    setTplLoading(true);
    listReportTemplates()
      .then(setTemplates)
      .catch(() => {
        /* ignore */
      })
      .finally(() => setTplLoading(false));
  }, [pickTemplate]);

  async function pickTpl(tpl: ReportTemplateMini) {
    try {
      const full = await getReportTemplate(tpl.id);
      setHtml(full.html_content);
      setHistory([]);
      setMode("template");
      setPickTemplate(false);
      setLoading(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la plantilla");
    }
  }

  // CA3-CA5: enviar HTML actual + instrucción al LLM.
  async function applyTweak() {
    if (!html || tweaking) return;
    if (instruction.trim().length < 2) {
      setError("Escribe una instrucción para aplicar.");
      return;
    }
    setTweaking(true);
    setError(null);
    try {
      const res = await tweakReportHTML({
        current_html: html,
        instruction: instruction.trim(),
      });
      setHistory((h) => [html, ...h].slice(0, MAX_HISTORY));
      setHtml(res.html);
      setModelUsed(res.model ?? null);
      setInstruction("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falló el tweak IA");
    } finally {
      setTweaking(false);
    }
  }

  function downloadLocalHtml() {
    if (!html) return;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte-${id}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  // CA6: deshacer último tweak (pop del head del historial).
  function undoLast() {
    if (history.length === 0) return;
    const [prev, ...rest] = history;
    setHtml(prev);
    setHistory(rest);
  }

  // CA8: guardar como plantilla (ENH-085 — `report_templates`).
  async function commitSaveTemplate() {
    if (!tplName.trim() || !html) return;
    setSavingTpl(true);
    setError(null);
    try {
      await createReportTemplate({
        name: tplName.trim(),
        description: tplDescription.trim() || null,
        html_content: html,
        is_shared: true,
      });
      setSaveTemplate(false);
      setTplName("");
      setTplDescription("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo guardar la plantilla",
      );
    } finally {
      setSavingTpl(false);
    }
  }

  const blobUrl = useMemo(() => {
    if (!html) return null;
    const blob = new Blob([html], { type: "text/html" });
    return URL.createObjectURL(blob);
  }, [html]);

  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  return (
    <div className="space-y-3 p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href={`/pmo/projects/${id}/reports`}
            className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Volver a reportes
          </Link>
          <h1 className="mt-1 flex items-center gap-2 text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            <FileText className="h-5 w-5 text-[var(--color-accent)]" aria-hidden />
            Crear reporte
            {mode === "template" ? (
              <Badge variant="info">desde plantilla</Badge>
            ) : (
              <Badge>nuevo</Badge>
            )}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPickTemplate(true)}
            disabled={tweaking}
          >
            <Layout className="h-3.5 w-3.5" aria-hidden /> Cargar plantilla
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={undoLast}
            disabled={history.length === 0 || tweaking}
          >
            <Undo2 className="h-3.5 w-3.5" aria-hidden /> Deshacer ({history.length})
          </Button>
          {/* ENH-089 CA5: descarga HTML directo del state local. PDF/TXT
              quedan disponibles después de guardar como Reporte (vía
              `/reports/{id}/export?format=...`). */}
          <Button
            variant="ghost"
            size="sm"
            onClick={downloadLocalHtml}
            disabled={!html || tweaking}
          >
            <Download className="h-3.5 w-3.5" aria-hidden /> Descargar HTML
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setSaveTemplate(true)}
            disabled={!html || tweaking}
          >
            <Save className="h-3.5 w-3.5" aria-hidden /> Guardar como plantilla
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {modelUsed ? (
        <p className="text-[11px] text-[var(--text-tertiary)]">
          Último modelo usado: <Badge>{modelUsed}</Badge>
        </p>
      ) : null}

      {/* CA1: panel inicial con 2 modos cuando aún no se eligió. */}
      {mode === null ? (
        <section className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center shadow-[var(--shadow-sm)]">
          <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">
            ¿Cómo quieres empezar?
          </h2>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Elige punto de partida para el reporte. Después puedes
            modificarlo con instrucciones IA.
          </p>
          <div className="mt-5 flex flex-wrap items-stretch justify-center gap-3">
            <button
              type="button"
              onClick={startNewMode}
              className="flex w-72 flex-col items-center gap-2 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-5 text-left hover:border-[var(--color-accent)]"
            >
              <FileText className="h-7 w-7 text-[var(--color-accent)]" aria-hidden />
              <span className="text-[14px] font-semibold text-[var(--text-primary)]">
                Generar nuevo reporte
              </span>
              <span className="text-[12px] text-[var(--text-tertiary)]">
                Render default sobre data del proyecto, listo para tweak.
              </span>
            </button>
            <button
              type="button"
              onClick={() => setPickTemplate(true)}
              className="flex w-72 flex-col items-center gap-2 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-5 text-left hover:border-[var(--color-accent)]"
            >
              <Layout className="h-7 w-7 text-[var(--color-accent)]" aria-hidden />
              <span className="text-[14px] font-semibold text-[var(--text-primary)]">
                Generar con base en plantilla
              </span>
              <span className="text-[12px] text-[var(--text-tertiary)]">
                Carga una plantilla guardada como punto de partida.
              </span>
            </button>
          </div>
        </section>
      ) : null}

      <div
        className="grid gap-3 lg:grid-cols-[300px_1fr]"
        style={{ display: mode === null ? "none" : undefined }}
      >
        <aside className="space-y-2 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 p-3">
          <div className="flex items-center gap-2 text-[12px] font-semibold text-[var(--text-secondary)]">
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            Instrucciones IA
          </div>
          <Textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={8}
            placeholder='Ej: "agrega tabla de tareas críticas con responsable y fecha", "cambia el color del header a azul oscuro", "quita la sección de Cambios"'
            disabled={tweaking || !html}
          />
          <Button onClick={applyTweak} loading={tweaking} disabled={!html}>
            <Wand2 className="h-3.5 w-3.5" aria-hidden /> Aplicar
          </Button>
          <p className="text-[11px] text-[var(--text-tertiary)]">
            Cada submit envía el HTML actual + instrucción al LLM. El historial guarda
            las últimas {MAX_HISTORY} versiones.
          </p>
        </aside>

        <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-white shadow-[var(--shadow-sm)] overflow-hidden">
          {loading ? (
            <div className="space-y-3 p-6">
              <Skeleton className="h-8 w-1/2" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          ) : html ? (
            <iframe
              title="Vista del reporte"
              srcDoc={html}
              sandbox="allow-scripts"
              className="h-[80vh] w-full border-0"
            />
          ) : (
            <p className="p-6 text-[12px] italic text-[var(--text-tertiary)]">
              Sin contenido. Carga el render default o elige una plantilla.
            </p>
          )}
        </div>
      </div>

      {/* Modal selector de plantillas (CA7). */}
      <Modal
        open={pickTemplate}
        onClose={() => setPickTemplate(false)}
        title="Elegir plantilla"
        size="lg"
      >
        {tplLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : templates.length === 0 ? (
          <p className="text-[13px] italic text-[var(--text-tertiary)]">
            No hay plantillas guardadas. Crea una desde un reporte tweakeado y aparecerá aquí.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {templates.map((t) => (
              <li
                key={t.id}
                className="flex items-center justify-between gap-2 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                    {t.name}
                  </p>
                  {t.description ? (
                    <p className="truncate text-[11px] text-[var(--text-tertiary)]">
                      {t.description}
                    </p>
                  ) : null}
                </div>
                <Button size="sm" onClick={() => pickTpl(t)}>
                  Usar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Modal>

      {/* Modal Guardar como plantilla (ENH-085). */}
      <Modal
        open={saveTemplate}
        onClose={() => !savingTpl && setSaveTemplate(false)}
        title="Guardar como plantilla"
        footer={
          <>
            <Button variant="secondary" onClick={() => setSaveTemplate(false)} disabled={savingTpl}>
              Cancelar
            </Button>
            <Button
              onClick={commitSaveTemplate}
              loading={savingTpl}
              disabled={tplName.trim().length < 2}
            >
              <Save className="h-3.5 w-3.5" aria-hidden /> Guardar
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
              Nombre
            </span>
            <Input value={tplName} onChange={(e) => setTplName(e.target.value)} />
          </label>
          <label className="block">
            <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
              Descripción (opcional)
            </span>
            <Textarea
              rows={3}
              value={tplDescription}
              onChange={(e) => setTplDescription(e.target.value)}
            />
          </label>
        </div>
      </Modal>
    </div>
  );
}

export default function TweakReportPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 text-sm text-[var(--color-tertiary)]">Cargando…</div>
      }
    >
      <Inner />
    </Suspense>
  );
}
