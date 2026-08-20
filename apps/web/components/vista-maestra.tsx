"use client";

/**
 * US-207 — La vista maestra del portafolio (control tower).
 *
 * El artboard «Portafolio — Vista maestra» de los mockups aprobados: una tabla
 * de ancho completo con una fila por proyecto y dieciséis columnas, header y
 * primera columna fijos, columnas configurables y export a XLSX.
 *
 * ## Por qué una tabla y no otro tablero
 *
 * El tablero ejecutivo (US-206) contesta «cómo va la cartera». Esta contesta
 * «¿qué pasa con ESTE proyecto?» para veintitrés proyectos a la vez, que es la
 * pregunta de la reunión de seguimiento. Para eso no sirve un gráfico: sirve
 * poder recorrer con el dedo una fila hasta la columna que interesa.
 *
 * De ahí las tres decisiones que la hacen usable y que un `<table>` normal no
 * tiene:
 *
 * - **Header y primera columna fijos.** Con dieciséis columnas se hace scroll
 *   horizontal siempre, y sin la columna del nombre pegada uno pierde de qué
 *   fila estaba leyendo. Es el fallo que convierte una tabla ancha en inútil.
 * - **Columnas configurables.** Nadie mira las dieciséis. El PMO de riesgos
 *   quiere seis; el de presupuesto, otras seis. La selección se recuerda porque
 *   volver a esconder diez columnas en cada visita es el motivo por el que la
 *   gente deja de usar la vista.
 * - **XLSX de lo que se ve.** El comité pide el archivo. Exportar las
 *   dieciséis cuando en pantalla hay seis entrega algo distinto de lo que se
 *   acordó mirar.
 *
 * ## Las tres columnas que faltan
 *
 * «Próximo hito», «Reporte» y «Completitud» no están: no existen como dato.
 * Son US-211 y US-210. Se declaran en `COLUMNAS_PENDIENTES` y la barra de
 * configuración las nombra como lo que son —pendientes—, en vez de callarlas:
 * quien conoce el mockup va a buscarlas, y no encontrarlas sin explicación se
 * lee como que se perdieron.
 */
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Columns3, Download } from "lucide-react";

import { colorSalud } from "@/components/dashboard-charts";
import { InlineSelectCell } from "@/components/inline-select-cell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SortableTh } from "@/components/ui/sortable-th";
import { cn } from "@/lib/cn";
import { formatearImporte } from "@/lib/moneda";
import type { PlanVsActualRow } from "@/lib/api/dashboard";
import {
  HEALTH_LABEL,
  PHASE_BADGE_TONE,
  PHASE_LABEL,
  PHASE_ORDER,
  TYPE_LABEL,
  etiquetaSalud,
  type ProjectHealth,
  type ProjectPhase,
} from "@/lib/api/projects";
import { useSortableRows, type SortableCtrl } from "@/lib/hooks/use-sortable-rows";

const CLAVE_COLUMNAS = "pmoaas:vista-maestra:columnas";

/** Las tres columnas del mockup que todavía no tienen dato detrás. */
export const COLUMNAS_PENDIENTES: { etiqueta: string; us: string }[] = [
  { etiqueta: "Próximo hito", us: "US-211" },
  { etiqueta: "Reporte", us: "US-211" },
  { etiqueta: "Completitud", us: "US-210" },
];

type Columna = {
  clave: string;
  etiqueta: string;
  /** Alineación de la celda y del header. Los números van a la derecha. */
  align?: "left" | "right" | "center";
  /** Para ordenar. Sin él la columna no es ordenable (las editables). */
  orden?: (r: PlanVsActualRow) => unknown;
  celda: (r: PlanVsActualRow, ctx: Contexto) => ReactNode;
  /** Texto plano para el XLSX. Una celda con JSX no se puede escribir. */
  texto: (r: PlanVsActualRow) => string | number;
  ancho?: number;
  /** `false` para las que no se pueden esconder: sin el nombre no hay tabla. */
  ocultable?: boolean;
};

type Contexto = {
  /** Cambiar la salud declarada de un proyecto. */
  onSalud?: (projectId: string, salud: ProjectHealth) => void;
  /** Cambiar la prioridad. */
  onPrioridad?: (projectId: string, prioridad: number) => void;
  /** Abrir el desglose del cálculo de salud. */
  onDesglose?: (projectId: string, nombre: string) => void;
  /** `true` si la persona puede editar proyectos. */
  puedeEditar: boolean;
};

const FECHA = new Intl.DateTimeFormat("es-MX", {
  day: "2-digit",
  month: "short",
  year: "2-digit",
});

function fecha(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : FECHA.format(d);
}

/**
 * «hoy», «ayer», «hace 3 d» — el formato del mockup para «Últ. act.».
 *
 * Relativo y no absoluto a propósito: la pregunta de la columna es «¿esto está
 * fresco?», y `18 ago 26` obliga a calcular la respuesta. Más allá de un mes
 * el relativo deja de decir nada útil («hace 47 d») y se pone la fecha.
 */
function frescura(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const dias = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (dias <= 0) return "hoy";
  if (dias === 1) return "ayer";
  if (dias <= 30) return `hace ${dias} d`;
  return FECHA.format(d);
}

/** El par plan/real que el mockup escribe «72/63%». */
function par(plan: number, real: number): string {
  return `${Math.round(plan)}/${Math.round(real)}%`;
}

const PRIORIDADES = [1, 2, 3, 4, 5];

function columnas(): Columna[] {
  const cols: Columna[] = [
    {
      clave: "name",
      etiqueta: "Proyecto",
      ocultable: false,
      ancho: 44,
      orden: (r) => r.name,
      texto: (r) => `${r.folio} · ${r.name}`,
      celda: (r) => (
        <Link
          href={`/pmo/projects/${r.project_id}`}
          className="block max-w-[280px] truncate font-medium text-[var(--color-primary)] hover:text-[var(--color-accent)]"
          title={`${r.folio} · ${r.name}`}
        >
          {r.name}
          <span className="ml-1.5 text-[11px] font-normal text-[var(--color-tertiary)]">
            {r.folio}
          </span>
        </Link>
      ),
    },
    {
      clave: "organization",
      etiqueta: "Organización",
      ancho: 24,
      orden: (r) => r.organization_name,
      texto: (r) => r.organization_name ?? "—",
      celda: (r) => (
        <span
          className="block max-w-[160px] truncate"
          title={r.organization_name ?? undefined}
        >
          {r.organization_name ?? "—"}
        </span>
      ),
    },
    {
      clave: "portfolio",
      etiqueta: "Portafolio",
      ancho: 24,
      orden: (r) => r.portfolio_name,
      texto: (r) => r.portfolio_name ?? "—",
      celda: (r) => (
        <span className="block max-w-[160px] truncate" title={r.portfolio_name ?? undefined}>
          {r.portfolio_name ?? "—"}
        </span>
      ),
    },
    {
      clave: "program",
      etiqueta: "Programa",
      ancho: 24,
      orden: (r) => r.program_name,
      texto: (r) => r.program_name ?? "—",
      celda: (r) => (
        <span className="block max-w-[160px] truncate" title={r.program_name ?? undefined}>
          {r.program_name ?? "—"}
        </span>
      ),
    },
    {
      clave: "type",
      etiqueta: "Tipo",
      ancho: 18,
      orden: (r) => r.type,
      texto: (r) => (r.type ? (TYPE_LABEL[r.type as keyof typeof TYPE_LABEL] ?? r.type) : "—"),
      celda: (r) => (
        <span className="whitespace-nowrap">
          {r.type ? (TYPE_LABEL[r.type as keyof typeof TYPE_LABEL] ?? r.type) : "—"}
        </span>
      ),
    },
    {
      clave: "phase",
      etiqueta: "Fase",
      ancho: 14,
      // Por el ciclo de vida y no alfabético: «Cancelado» primero no es por
      // donde empieza nada (US-202).
      orden: (r) => PHASE_ORDER.indexOf(r.phase as ProjectPhase),
      texto: (r) => PHASE_LABEL[r.phase as ProjectPhase] ?? r.phase,
      celda: (r) => (
        <Badge variant={PHASE_BADGE_TONE[r.phase as ProjectPhase] ?? "neutral"}>
          {PHASE_LABEL[r.phase as ProjectPhase] ?? r.phase}
        </Badge>
      ),
    },
    {
      clave: "priority",
      etiqueta: "Prio",
      align: "center",
      ancho: 8,
      orden: (r) => r.priority,
      texto: (r) => (r.priority ? `P${r.priority}` : "—"),
      celda: (r, ctx) =>
        ctx.puedeEditar && ctx.onPrioridad ? (
          <InlineSelectCell
            value={r.priority ? String(r.priority) : ""}
            options={PRIORIDADES.map((n) => ({ value: String(n), label: `P${n}` }))}
            onChange={(v) => v && ctx.onPrioridad?.(r.project_id, Number(v))}
            title="Prioridad"
            ariaLabel={`Prioridad de ${r.name}`}
          />
        ) : (
          <span>{r.priority ? `P${r.priority}` : "—"}</span>
        ),
    },
    {
      clave: "health",
      etiqueta: "Salud",
      align: "center",
      ancho: 12,
      orden: (r) => ({ red: 0, yellow: 1, green: 2 })[r.health ?? ""] ?? 9,
      texto: (r) =>
        `${etiquetaSalud(r.health)}${r.health_source === "manual" ? " (PM)" : ""}`,
      celda: (r, ctx) => (
        <span className="flex items-center justify-center gap-1.5">
          {ctx.puedeEditar && ctx.onSalud ? (
            <InlineSelectCell
              value={r.health ?? ""}
              options={(Object.keys(HEALTH_LABEL) as ProjectHealth[]).map((k) => ({
                value: k,
                label: HEALTH_LABEL[k],
              }))}
              onChange={(v) => v && ctx.onSalud?.(r.project_id, v as ProjectHealth)}
              title="Salud declarada"
              ariaLabel={`Salud de ${r.name}`}
            />
          ) : (
            <span style={{ color: colorSalud(r.health) }} className="font-medium">
              {etiquetaSalud(r.health)}
            </span>
          )}
          {/* El mockup: «click en salud abre el desglose del cálculo». Va como
              botón aparte del select porque son dos acciones distintas —ver por
              qué, y declarar otra cosa— y colapsarlas en un click haría que
              consultar el porqué cambiara el dato. */}
          {ctx.onDesglose ? (
            <button
              type="button"
              onClick={() => ctx.onDesglose?.(r.project_id, r.name)}
              className="rounded px-1 text-[11px] text-[var(--color-tertiary)] underline decoration-dotted hover:text-[var(--color-accent)]"
              title={`Por qué ${r.name} está en ${etiquetaSalud(r.health).toLowerCase()}`}
            >
              ?
            </button>
          ) : null}
        </span>
      ),
    },
    {
      clave: "progress",
      etiqueta: "Avance P/R",
      align: "right",
      ancho: 14,
      // Por la desviación y no por el avance: la pregunta de la columna es
      // «¿va atrasado?», y ordenar por el real pone arriba al que empieza.
      orden: (r) => r.progress_actual - r.progress_plan,
      texto: (r) => par(r.progress_plan, r.progress_actual),
      celda: (r) => {
        const delta = Math.round(r.progress_actual - r.progress_plan);
        return (
          <span className="whitespace-nowrap tabular-nums">
            {par(r.progress_plan, r.progress_actual)}
            {delta < 0 ? (
              <span className="ml-1 text-[11px] text-[var(--color-danger-fg)]">
                −{Math.abs(delta)}
              </span>
            ) : null}
          </span>
        );
      },
    },
    {
      clave: "budget",
      etiqueta: "Presup. P/R",
      align: "right",
      ancho: 22,
      orden: (r) => r.budget_plan,
      // BUG-092 — la moneda es la de la fila, que la API ya resolvió. Un
      // formato con la moneda del inquilino rotularía euros como pesos.
      texto: (r) =>
        `${formatearImporte(r.budget_plan, r.currency)} / ${formatearImporte(r.budget_actual, r.currency)}`,
      celda: (r) => (
        <span className="whitespace-nowrap tabular-nums">
          {formatearImporte(r.budget_plan, r.currency)}
          <span className="text-[var(--color-tertiary)]"> / </span>
          {formatearImporte(r.budget_actual, r.currency)}
        </span>
      ),
    },
    {
      clave: "end_date",
      etiqueta: "Fin",
      ancho: 12,
      orden: (r) => r.end_date,
      texto: (r) => fecha(r.end_date),
      celda: (r) => <span className="whitespace-nowrap">{fecha(r.end_date)}</span>,
    },
    {
      clave: "risks",
      etiqueta: "Riesgos",
      align: "right",
      ancho: 10,
      orden: (r) => r.open_risks,
      texto: (r) => r.open_risks,
      celda: (r) =>
        r.open_risks > 0 ? (
          <Link
            href={`/pmo/projects/${r.project_id}/raid`}
            className="tabular-nums hover:text-[var(--color-accent)]"
          >
            {r.open_risks}
          </Link>
        ) : (
          <span className="tabular-nums text-[var(--color-tertiary)]">0</span>
        ),
    },
    {
      clave: "issues",
      etiqueta: "Issues",
      align: "right",
      ancho: 10,
      orden: (r) => r.open_issues,
      texto: (r) => r.open_issues,
      celda: (r) =>
        r.open_issues > 0 ? (
          <Link
            href={`/pmo/projects/${r.project_id}/raid`}
            className="tabular-nums hover:text-[var(--color-accent)]"
          >
            {r.open_issues}
          </Link>
        ) : (
          <span className="tabular-nums text-[var(--color-tertiary)]">0</span>
        ),
    },
    {
      clave: "updated_at",
      etiqueta: "Últ. act.",
      ancho: 12,
      orden: (r) => r.updated_at,
      texto: (r) => frescura(r.updated_at),
      celda: (r) => (
        <span
          className="whitespace-nowrap text-[var(--color-tertiary)]"
          title={r.updated_at ?? undefined}
        >
          {frescura(r.updated_at)}
        </span>
      ),
    },
  ];
  return cols;
}

/**
 * Las que arrancan visibles.
 *
 * «Organización» no está: con una organización elegida en el header sería una
 * columna con el mismo valor en las veintitrés filas. La página la enciende
 * cuando el header agrega, que es cuando distingue algo.
 */
const VISIBLES_POR_DEFECTO = new Set([
  "name",
  "portfolio",
  "program",
  "phase",
  "priority",
  "health",
  "progress",
  "budget",
  "end_date",
  "risks",
  "issues",
]);

export function VistaMaestra({
  filas,
  cargando,
  puedeEditar,
  siempreVisibles,
  onSalud,
  onPrioridad,
  onDesglose,
}: {
  filas: PlanVsActualRow[];
  cargando?: boolean;
  /** `true` si la persona puede editar proyectos: habilita la edición inline. */
  puedeEditar: boolean;
  /**
   * Columnas que el contexto obliga a mostrar — hoy «Organización» cuando el
   * header agrega. Se suman a lo guardado en vez de reemplazarlo: quien escondió
   * cinco columnas no las quiere de vuelta por cambiar de organización. Y se
   * pueden apagar a mano: es una preferencia de arranque, no un candado.
   */
  siempreVisibles?: readonly string[];
  onSalud?: (projectId: string, salud: ProjectHealth) => void;
  onPrioridad?: (projectId: string, prioridad: number) => void;
  onDesglose?: (projectId: string, nombre: string) => void;
}) {
  const todas = useMemo(() => columnas(), []);
  const [visibles, setVisibles] = useState<Set<string>>(
    () => new Set([...VISIBLES_POR_DEFECTO, ...(siempreVisibles ?? [])]),
  );
  const [configAbierta, setConfigAbierta] = useState(false);
  const [exportando, setExportando] = useState(false);
  const { sortedRows, ctrl } = useSortableRows<PlanVsActualRow>(filas);

  // La selección se recuerda: volver a esconder cinco columnas en cada visita
  // es el motivo por el que alguien deja de usar la vista.
  useEffect(() => {
    try {
      const crudo = window.localStorage.getItem(CLAVE_COLUMNAS);
      if (!crudo) return;
      const guardadas = JSON.parse(crudo);
      if (!Array.isArray(guardadas)) return;
      // Se filtra contra las columnas que existen hoy: una guardada que se
      // renombró dejaría un hueco, y una que ya no existe, una casilla
      // fantasma en el configurador.
      const claves = new Set(todas.map((c) => c.clave));
      const validas = guardadas.filter((k): k is string => claves.has(String(k)));
      setVisibles(
        new Set([
          ...validas,
          // La no ocultable entra siempre, aunque la guardada no la tenga.
          ...todas.filter((c) => c.ocultable === false).map((c) => c.clave),
          ...(siempreVisibles ?? []),
        ]),
      );
    } catch {
      // Modo privado o JSON corrupto: se arranca con el default.
    }
    // `siempreVisibles` a propósito **fuera** de las dependencias: si entrara,
    // apagar «Organización» a mano dispararía este efecto y la volvería a
    // encender. Solo tiene que aplicar al leer lo guardado, una vez.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [todas]);

  const alternar = useCallback(
    (clave: string) => {
      setVisibles((prev) => {
        const siguiente = new Set(prev);
        if (siguiente.has(clave)) siguiente.delete(clave);
        else siguiente.add(clave);
        try {
          window.localStorage.setItem(
            CLAVE_COLUMNAS,
            JSON.stringify([...siguiente]),
          );
        } catch {
          // Que no se pueda recordar no impide que se pueda elegir.
        }
        return siguiente;
      });
    },
    [],
  );

  const mostradas = useMemo(
    () => todas.filter((c) => visibles.has(c.clave)),
    [todas, visibles],
  );

  const contexto: Contexto = { onSalud, onPrioridad, onDesglose, puedeEditar };

  async function exportar() {
    if (exportando) return;
    setExportando(true);
    try {
      const ExcelJS = (await import("exceljs")).default;
      const { aplicarFuente, XLSX_FONT } = await import("@/lib/plan-template");
      const wb = new ExcelJS.Workbook();
      wb.creator = "PMO aaS";
      const ws = wb.addWorksheet("Vista maestra");
      // Solo las columnas visibles: exportar dieciséis cuando en pantalla hay
      // seis entrega algo distinto de lo que se acordó mirar.
      ws.columns = mostradas.map((c) => ({
        header: c.etiqueta,
        key: c.clave,
        width: c.ancho,
      }));
      ws.getRow(1).font = { name: XLSX_FONT, bold: true };
      for (const fila of sortedRows) {
        const registro: Record<string, string | number> = {};
        for (const c of mostradas) registro[c.clave] = c.texto(fila);
        ws.addRow(registro);
      }
      // ENH-202 — sin el barrido las filas de datos salen en Calibri y el
      // archivo lleva dos tipografías.
      aplicarFuente(ws);
      const buf = await wb.xlsx.writeBuffer();
      const url = URL.createObjectURL(
        new Blob([buf], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "vista-maestra-portafolio.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setExportando(false);
    }
  }

  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-default)] p-3">
        <p className="text-sm text-[var(--color-tertiary)]">
          {cargando
            ? "Cargando proyectos…"
            : `${filas.length} ${filas.length === 1 ? "proyecto" : "proyectos"}`}
          {ctrl.sortKey ? " · ordenado por " : ""}
          {ctrl.sortKey
            ? (todas.find((c) => c.clave === ctrl.sortKey)?.etiqueta ?? "").toLowerCase()
            : ""}
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setConfigAbierta((v) => !v)}
            aria-expanded={configAbierta}
          >
            <Columns3 className="mr-1 h-3.5 w-3.5" aria-hidden />
            Columnas ({mostradas.length}/{todas.length})
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={exportar}
            disabled={exportando || filas.length === 0}
          >
            <Download className="mr-1 h-3.5 w-3.5" aria-hidden />
            {exportando ? "Generando…" : "XLSX"}
          </Button>
        </div>
      </header>

      {configAbierta ? (
        <div className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] p-3">
          <fieldset>
            <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
              Columnas visibles
            </legend>
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {todas.map((c) => (
                <label
                  key={c.clave}
                  className={cn(
                    "flex items-center gap-1.5 text-[13px]",
                    c.ocultable === false && "text-[var(--color-tertiary)]",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={visibles.has(c.clave)}
                    disabled={c.ocultable === false}
                    onChange={() => alternar(c.clave)}
                  />
                  {c.etiqueta}
                </label>
              ))}
            </div>
          </fieldset>
          {/* Las del mockup que no existen todavía, nombradas. Callarlas hace
              que quien conoce el mockup las busque y crea que se perdieron. */}
          <p className="mt-2.5 text-[11px] text-[var(--color-tertiary)]">
            Pendientes de los mockups:{" "}
            {COLUMNAS_PENDIENTES.map((c) => `${c.etiqueta} (${c.us})`).join(" · ")}
            . Necesitan datos que todavía no existen.
          </p>
        </div>
      ) : null}

      {/* El scroll horizontal vive aquí y no en la página: la tabla es lo ancho,
          y un `overflow` en el contenedor de la pantalla arrastraría el header
          y los filtros con ella. */}
      <div className="relative max-h-[70vh] overflow-auto">
        <table className="w-full min-w-max border-separate border-spacing-0 text-[13px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--color-tertiary)]">
              {mostradas.map((c, i) => {
                // La primera columna se queda pegada a la izquierda **y** arriba:
                // es la intersección de los dos ejes fijos, así que necesita el
                // z-index más alto o el header la tapa al hacer scroll.
                const fijaX = i === 0;
                const clases = cn(
                  "sticky top-0 border-b border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2",
                  fijaX && "left-0 z-20",
                  !fijaX && "z-10",
                  c.align === "right" && "text-right",
                  c.align === "center" && "text-center",
                );
                return c.orden ? (
                  <SortableTh
                    key={c.clave}
                    sortKey={c.clave}
                    getter={c.orden}
                    ctrl={ctrl as SortableCtrl<PlanVsActualRow>}
                    align={c.align}
                    className={clases}
                  >
                    {c.etiqueta}
                  </SortableTh>
                ) : (
                  <th key={c.clave} className={cn(clases, "font-medium")}>
                    {c.etiqueta}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {cargando ? (
              [0, 1, 2, 3, 4].map((i) => (
                <tr key={i}>
                  {mostradas.map((c) => (
                    <td key={c.clave} className="px-3 py-2">
                      <span
                        aria-hidden
                        className="block h-4 animate-pulse rounded bg-[var(--color-muted)]"
                      />
                    </td>
                  ))}
                </tr>
              ))
            ) : sortedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={mostradas.length}
                  className="px-3 py-10 text-center text-sm text-[var(--color-tertiary)]"
                >
                  Ningún proyecto casa con estos filtros. Prueba a limpiarlos, o
                  crea el primero desde «Nuevo proyecto».
                </td>
              </tr>
            ) : (
              sortedRows.map((r) => (
                <tr key={r.project_id} className="group hover:bg-[var(--color-subtle)]">
                  {mostradas.map((c, i) => (
                    <td
                      key={c.clave}
                      className={cn(
                        "border-b border-[var(--border-subtle)] px-3 py-2",
                        // La celda fija necesita fondo propio: sin él se ve el
                        // texto de las columnas de debajo pasando por detrás.
                        i === 0 &&
                          "sticky left-0 z-10 bg-[var(--color-surface)] group-hover:bg-[var(--color-subtle)]",
                        c.align === "right" && "text-right",
                        c.align === "center" && "text-center",
                      )}
                    >
                      {c.celda(r, contexto)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
