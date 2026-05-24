"use client";

import { useEffect, useRef, useState } from "react";

import { renderBuilder, type RenderRequest } from "@/lib/api/report-builder";

type Props = {
  request: RenderRequest | null;
};

/** US-124 — preview en vivo con debounce ~500 ms. */
export function PreviewPane({ request }: Props) {
  const [html, setHtml] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!request) {
      setHtml("");
      return;
    }
    if (timer.current) clearTimeout(timer.current);
    setLoading(true);
    timer.current = setTimeout(async () => {
      try {
        const res = await renderBuilder(request, "json");
        // ENH-124: inyecta CSS al HTML del preview para visualizar cortes de
        // página A4 (aprox 1123px @ 96dpi). El estilo es solo para el
        // preview; el PDF real respeta sus propios @page/page-break.
        const pageBreakCss = `
<style id="builder-preview-page-marks">
  body { background: #f4f4f5; padding: 0; }
  /* Container que simula página A4 */
  body > * { background: white; }
  /* Marcador visual cada ~1123px (alto A4 a 96dpi) */
  body { background-image: repeating-linear-gradient(
    to bottom,
    transparent 0,
    transparent 1100px,
    #fcd34d 1100px,
    #fcd34d 1102px,
    transparent 1102px,
    transparent 1123px,
    #e4e4e7 1123px,
    #e4e4e7 1135px
  ); }
</style>
`.trim();
        const enriched = res.html.includes("</head>")
          ? res.html.replace("</head>", `${pageBreakCss}\n</head>`)
          : pageBreakCss + res.html;
        setHtml(enriched);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al renderizar preview");
      } finally {
        setLoading(false);
      }
    }, 500);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [JSON.stringify(request)]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-600">
        <span>Preview en vivo · líneas amarillas marcan cortes A4</span>
        {loading && <span className="text-zinc-400">Renderizando…</span>}
      </div>
      {error && (
        <div className="bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
      )}
      {request ? (
        <iframe
          title="Report Builder preview"
          className="h-full w-full flex-1 bg-white"
          srcDoc={html}
          sandbox=""
        />
      ) : (
        <div className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500">
          Agrega secciones para ver el preview.
        </div>
      )}
    </div>
  );
}
