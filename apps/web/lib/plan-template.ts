/**
 * US-071 + US-096 + ENH-194 + US-193 — Workbook profesional del Plan.
 *
 * Un solo layout estilo MS Project (hoja "Plan") usado por la plantilla
 * vacía Y por el export "Descargar" con datos reales:
 *
 *   filas 1-2  Encabezado del proyecto (nombre, sponsor, PM, fechas,
 *              fecha de corte =TODAY()).
 *   filas 4-5  KPIs VIVOS (fórmulas): avance general, tareas,
 *              completadas, en curso, atrasadas, hitos.
 *   fila 7     Headers de la tabla (importables — el parser US-193
 *              busca la fila de headers automáticamente).
 *   filas 8+   Actividades. A la derecha (col Q+) el GANTT VIVO:
 *              barras de dos tonos por formato condicional (verde =
 *              avanzado según %, azul = pendiente), hitos morados y
 *              semana actual marcada. Se repinta al editar.
 *
 * Todo en Helvetica (US-193: primer cambio masivo de fuente; Excel en
 * Windows la sustituye por Arial automáticamente).
 *
 * Los estilos por fila (banda de padres, hito morado, chip de Estado)
 * son FORMATO CONDICIONAL, así funcionan igual en la plantilla vacía
 * conforme el usuario escribe.
 */
import type { Workbook, Worksheet } from "exceljs";

import { TASK_STATUS_LABEL } from "@/lib/api/tasks";

const SHEET_PLAN = "Plan";
const SHEET_INSTRUCTIONS = "Instrucciones";

// US-193: fuente única de todos los Excel del sistema.
export const XLSX_FONT = "Helvetica";

/**
 * ENH-202 — deja `XLSX_FONT` en todas las filas de la hoja.
 *
 * ExcelJS no expone una fuente por defecto del libro: lo que no lleva `font`
 * sale en Calibri. Poner la cabecera en Helvetica y dejar los datos en Calibri
 * es peor que no tocar nada, porque el archivo sale con dos tipografías.
 *
 * Se llama **después** de poblar la hoja, y conserva lo que cada celda ya
 * traía —negritas, colores— cambiando solo el nombre.
 */
export function aplicarFuente(ws: Worksheet): void {
  ws.eachRow({ includeEmpty: false }, (row) => {
    row.eachCell({ includeEmpty: false }, (cell) => {
      cell.font = { ...(cell.font ?? {}), name: XLSX_FONT };
    });
  });
}

// Paleta.
const DARK = "FF1F2937";
const GRAY = "FF6B7280";
const ACCENT = "FF2563EB";
const DONE = "FF059669";
const PURPLE = "FF7C3AED";
const BAND = "FFE5E7EB";
const TODAY_TINT = "FFFEE2E2";
const BORDER_C = "FFD1D5DB";

const HDR = 7; // fila de headers de la tabla
const FIRST = 8; // primera fila de datos
const TEMPLATE_ROWS = 300; // filas pre-formateadas en la plantilla
const GANTT_COL = 17; // Q (P = separador)
const MAX_DURATION_DAYS = 21;

export type TemplateProjectInfo = {
  name: string;
  objective?: string | null;
  scope?: string | null;
  sponsor?: string | null;
  pm?: string | null;
  startDate?: string | null; // ISO yyyy-mm-dd
  endDate?: string | null;
};

export type PlanExportRow = {
  wbs: string;
  name: string;
  outline: number | null;
  start: Date | null;
  end: Date | null;
  duration: number | null;
  /** Fracción 0..1 (la celda va con formato %). */
  progress: number;
  statusLabel: string;
  area: string;
  owner: string;
  critical: boolean;
  milestone: boolean;
  relatedMilestone: string;
  predecessors: string;
  successors: string;
};

const STATUS_LABELS = {
  not_started: TASK_STATUS_LABEL["not_started"] ?? "No iniciada",
  in_progress: TASK_STATUS_LABEL["in_progress"] ?? "En progreso",
  completed: TASK_STATUS_LABEL["completed"] ?? "Completada",
  on_hold: TASK_STATUS_LABEL["on_hold"] ?? "En pausa",
};

/** Parsea "yyyy-mm-dd" a Date LOCAL (evita el shift UTC de new Date(iso)). */
export function localDateFromIso(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function colLetter(n: number): string {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

const thinBorder = {
  top: { style: "thin" as const, color: { argb: BORDER_C } },
  left: { style: "thin" as const, color: { argb: BORDER_C } },
  bottom: { style: "thin" as const, color: { argb: BORDER_C } },
  right: { style: "thin" as const, color: { argb: BORDER_C } },
};

function metaPair(ws: Worksheet, row: number, col: number, k: string, v: unknown) {
  const kc = ws.getCell(row, col);
  kc.value = k;
  kc.font = { name: XLSX_FONT, size: 9, bold: true, color: { argb: GRAY } };
  const vc = ws.getCell(row, col + 1);
  vc.value = v as never;
  vc.font = { name: XLSX_FONT, size: 9, color: { argb: DARK } };
  return vc;
}

/**
 * Construye el workbook profesional. `rows=null` → plantilla vacía
 * (validaciones + fórmulas auto + 2 filas de ejemplo + Instrucciones).
 */
export async function buildPlanWorkbook(
  info: TemplateProjectInfo,
  rows: PlanExportRow[] | null,
): Promise<Workbook> {
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  wb.creator = "PMO aaS";
  wb.created = new Date();

  const ws = wb.addWorksheet(SHEET_PLAN, {
    views: [
      { state: "frozen", xSplit: 2, ySplit: HDR, showGridLines: false },
    ],
  });

  const dataCount = rows ? Math.max(rows.length, 1) : TEMPLATE_ROWS;
  const lastRow = FIRST + dataCount - 1;
  const kpiLast = FIRST + Math.max(dataCount, TEMPLATE_ROWS) - 1;

  // ---------- Encabezado del proyecto ----------
  ws.mergeCells("A1:F1");
  const title = ws.getCell("A1");
  title.value = info.name;
  title.font = { name: XLSX_FONT, size: 18, bold: true, color: { argb: DARK } };
  ws.mergeCells("G1:J1");
  const brand = ws.getCell("G1");
  brand.value = "PLAN DE TRABAJO";
  brand.font = { name: XLSX_FONT, size: 10, bold: true, color: { argb: GRAY } };
  brand.alignment = { horizontal: "right" };

  metaPair(ws, 2, 1, "Sponsor", info.sponsor || "—");
  metaPair(ws, 2, 3, "PM", info.pm || "—");
  metaPair(ws, 2, 5, "Inicio", info.startDate || "—");
  metaPair(ws, 2, 7, "Fin", info.endDate || "—");
  const corte = metaPair(ws, 2, 9, "Corte", { formula: "TODAY()" } as never);
  corte.numFmt = "yyyy-mm-dd";

  // ---------- KPIs vivos ----------
  const kpis: [string, string][] = [
    [
      "AVANCE GENERAL",
      `IFERROR(ROUND(AVERAGEIF(C${FIRST}:C${kpiLast},1,G${FIRST}:G${kpiLast})*100,0),0)&"%"`,
    ],
    ["TAREAS", `COUNTIF(B${FIRST}:B${kpiLast},"<>")`],
    [
      "COMPLETADAS",
      `COUNTIF(H${FIRST}:H${kpiLast},"${STATUS_LABELS.completed}")`,
    ],
    [
      "EN CURSO",
      `COUNTIF(H${FIRST}:H${kpiLast},"${STATUS_LABELS.in_progress}")`,
    ],
    [
      "ATRASADAS",
      `COUNTIFS(E${FIRST}:E${kpiLast},"<"&TODAY(),G${FIRST}:G${kpiLast},"<1",B${FIRST}:B${kpiLast},"<>")`,
    ],
    [
      "HITOS",
      `COUNTIF(L${FIRST}:L${kpiLast},"Sí")&" ("&COUNTIFS(L${FIRST}:L${kpiLast},"Sí",H${FIRST}:H${kpiLast},"${STATUS_LABELS.completed}")&" ok)"`,
    ],
  ];
  kpis.forEach(([label, formula], i) => {
    const col = 1 + i * 2;
    ws.mergeCells(4, col, 4, col + 1);
    ws.mergeCells(5, col, 5, col + 1);
    const lc = ws.getCell(4, col);
    lc.value = label;
    lc.font = { name: XLSX_FONT, size: 8, bold: true, color: { argb: "FFFFFFFF" } };
    lc.fill = { type: "pattern", pattern: "solid", fgColor: { argb: DARK } };
    lc.alignment = { horizontal: "center" };
    const vc = ws.getCell(5, col);
    vc.value = { formula } as never;
    vc.font = { name: XLSX_FONT, size: 12, bold: true, color: { argb: DARK } };
    vc.alignment = { horizontal: "center" };
  });

  // ---------- Headers de la tabla ----------
  const headers = [
    "WBS", "Tarea", "Nivel", "Inicio", "Fin", "Días", "Avance", "Estado",
    "Área", "Responsable", "Criticidad", "Hito", "Hito Relacionado",
    "Predecesoras", "Sucesoras",
  ];
  headers.forEach((h, i) => {
    const c = ws.getCell(HDR, i + 1);
    c.value = h;
    c.font = { name: XLSX_FONT, size: 9, bold: true, color: { argb: "FFFFFFFF" } };
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: DARK } };
    c.alignment = { horizontal: "center", vertical: "middle" };
    c.border = thinBorder;
  });
  const widths = [9, 38, 6, 11, 11, 6, 8, 13, 13, 17, 10, 6, 15, 13, 13, 2];
  widths.forEach((w, i) => {
    ws.getColumn(i + 1).width = w;
  });

  // ---------- Timeline del Gantt ----------
  const starts = (rows ?? [])
    .map((r) => r.start)
    .filter((d): d is Date => d instanceof Date);
  const ends = (rows ?? [])
    .map((r) => r.end)
    .filter((d): d is Date => d instanceof Date);
  const anchorBase =
    starts.length > 0
      ? new Date(Math.min(...starts.map((d) => d.getTime())))
      : (localDateFromIso(info.startDate) ?? new Date());
  const monday = new Date(anchorBase);
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  const maxEnd =
    ends.length > 0
      ? new Date(Math.max(...ends.map((d) => d.getTime())))
      : null;
  const spanWeeks = maxEnd
    ? Math.ceil((maxEnd.getTime() - monday.getTime()) / (7 * 86_400_000)) + 2
    : 26;
  const weeks = Math.max(12, Math.min(spanWeeks, 104));

  for (let w = 0; w < weeks; w++) {
    const c = ws.getCell(HDR, GANTT_COL + w);
    const d = new Date(monday);
    d.setDate(d.getDate() + w * 7);
    c.value = d;
    c.numFmt = "dd/mm";
    c.font = { name: XLSX_FONT, size: 8, bold: true, color: { argb: "FFFFFFFF" } };
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: DARK } };
    c.alignment = { horizontal: "center" };
    ws.getColumn(GANTT_COL + w).width = 4.4;
  }

  // ---------- Filas de datos ----------
  for (let r = FIRST; r <= lastRow; r++) {
    const row = rows ? rows[r - FIRST] : null;
    for (let c = 1; c <= 15; c++) {
      const cell = ws.getCell(r, c);
      cell.border = thinBorder;
      cell.font = { name: XLSX_FONT, size: 9, color: { argb: DARK } };
    }
    for (let w = 0; w < weeks; w++) {
      ws.getCell(r, GANTT_COL + w).border = thinBorder;
    }
    ws.getCell(r, 1).numFmt = "@"; // BUG-088: WBS como texto
    ws.getCell(r, 4).numFmt = "yyyy-mm-dd";
    ws.getCell(r, 5).numFmt = "yyyy-mm-dd";
    ws.getCell(r, 7).numFmt = "0%";
    ws.getCell(r, 3).alignment = { horizontal: "center" };
    ws.getCell(r, 6).alignment = { horizontal: "center" };
    ws.getCell(r, 7).alignment = { horizontal: "center" };
    ws.getCell(r, 8).alignment = { horizontal: "center" };
    ws.getCell(r, 11).alignment = { horizontal: "center" };
    ws.getCell(r, 12).alignment = { horizontal: "center" };

    if (row) {
      ws.getCell(r, 1).value = row.wbs;
      ws.getCell(r, 2).value = row.name;
      ws.getCell(r, 3).value = row.outline ?? "";
      ws.getCell(r, 4).value = row.start ?? "";
      ws.getCell(r, 5).value = row.end ?? "";
      ws.getCell(r, 6).value = row.duration ?? "";
      ws.getCell(r, 7).value = row.progress;
      ws.getCell(r, 8).value = row.statusLabel;
      ws.getCell(r, 9).value = row.area;
      ws.getCell(r, 10).value = row.owner;
      ws.getCell(r, 11).value = row.critical ? "Sí" : "No";
      ws.getCell(r, 12).value = row.milestone ? "Sí" : "No";
      ws.getCell(r, 13).value = row.relatedMilestone;
      ws.getCell(r, 14).value = row.predecessors;
      ws.getCell(r, 15).value = row.successors;
    } else {
      // Plantilla: Nivel y Días auto-calculados (US-096).
      ws.getCell(r, 3).value = {
        formula: `IF(A${r}="","",LEN(A${r})-LEN(SUBSTITUTE(A${r},".",""))+1)`,
      } as never;
      ws.getCell(r, 6).value = {
        formula: `IF(AND(D${r}<>"",E${r}<>""),E${r}-D${r}+1,"")`,
      } as never;
    }
  }

  // ---------- Formato condicional (aplica en plantilla Y export) ----------
  const tableRng = `A${FIRST}:O${lastRow}`;
  // Padres (Nivel 1): banda gris + bold.
  ws.addConditionalFormatting({
    ref: tableRng,
    rules: [
      {
        type: "expression",
        priority: 10,
        formulae: [`$C${FIRST}=1`],
        style: {
          font: { name: XLSX_FONT, bold: true },
          fill: { type: "pattern", pattern: "solid", bgColor: { argb: BAND } },
        },
      } as never,
      // Hitos: texto morado.
      {
        type: "expression",
        priority: 11,
        formulae: [`$L${FIRST}="Sí"`],
        style: { font: { name: XLSX_FONT, color: { argb: PURPLE }, bold: true } },
      } as never,
    ],
  });
  // Chips de Estado.
  const statusRng = `H${FIRST}:H${lastRow}`;
  const chip = (label: string, bg: string, fg: string, priority: number) =>
    ({
      type: "cellIs",
      operator: "equal",
      priority,
      formulae: [`"${label}"`],
      style: {
        font: { name: XLSX_FONT, bold: true, color: { argb: fg } },
        fill: { type: "pattern", pattern: "solid", bgColor: { argb: bg } },
      },
    }) as never;
  ws.addConditionalFormatting({
    ref: statusRng,
    rules: [
      chip(STATUS_LABELS.completed, "FFDCFCE7", "FF166534", 1),
      chip(STATUS_LABELS.in_progress, "FFDBEAFE", "FF1E40AF", 2),
      chip(STATUS_LABELS.on_hold, "FFFEF9C3", "FF854D0E", 3),
      chip(STATUS_LABELS.not_started, "FFF3F4F6", "FF374151", 4),
    ],
  });
  // Duración > 21 días (US-090/US-096).
  ws.addConditionalFormatting({
    ref: `F${FIRST}:F${lastRow}`,
    rules: [
      {
        type: "cellIs",
        operator: "greaterThan",
        priority: 5,
        formulae: [String(MAX_DURATION_DAYS)],
        style: {
          fill: { type: "pattern", pattern: "solid", bgColor: { argb: "FFFFF8C5" } },
          font: { name: XLSX_FONT, color: { argb: "FF92400E" }, bold: true },
        },
      } as never,
    ],
  });
  // Gantt vivo (dos tonos + hito + semana actual).
  const g0 = colLetter(GANTT_COL);
  const gantRng = `${g0}${FIRST}:${colLetter(GANTT_COL + weeks - 1)}${lastRow}`;
  const overlap = `AND($D${FIRST}<>"",$E${FIRST}<>"",${g0}$${HDR}<=$E${FIRST},${g0}$${HDR}+6>=$D${FIRST})`;
  ws.addConditionalFormatting({
    ref: gantRng,
    rules: [
      {
        type: "expression",
        priority: 1,
        formulae: [`AND($L${FIRST}="Sí",${overlap})`],
        style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: PURPLE } } },
      } as never,
      {
        type: "expression",
        priority: 2,
        formulae: [
          `AND(${overlap},${g0}$${HDR}<=$D${FIRST}+($E${FIRST}-$D${FIRST})*$G${FIRST})`,
        ],
        style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: DONE } } },
      } as never,
      {
        type: "expression",
        priority: 3,
        formulae: [overlap],
        style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: ACCENT } } },
      } as never,
      {
        type: "expression",
        priority: 4,
        formulae: [`AND(${g0}$${HDR}<=TODAY(),TODAY()<${g0}$${HDR}+7)`],
        style: { fill: { type: "pattern", pattern: "solid", bgColor: { argb: TODAY_TINT } } },
      } as never,
    ],
  });

  // ---------- Plantilla: validaciones + ejemplos + Instrucciones ----------
  if (!rows) {
    const statusList = Object.values(STATUS_LABELS).join(",");
    for (let r = FIRST; r <= lastRow; r++) {
      ws.getCell(r, 7).dataValidation = {
        type: "decimal",
        operator: "between",
        formulae: [0, 1],
        allowBlank: true,
        errorStyle: "warning",
        error: "Avance en % (0% a 100%). Escribí 45 y Excel lo toma como 45%.",
      };
      ws.getCell(r, 8).dataValidation = {
        type: "list",
        formulae: [`"${statusList}"`],
        allowBlank: true,
        errorStyle: "warning",
      };
      ws.getCell(r, 11).dataValidation = {
        type: "list",
        formulae: ['"Sí,No"'],
        allowBlank: true,
      };
      ws.getCell(r, 12).dataValidation = {
        type: "list",
        formulae: ['"Sí,No"'],
        allowBlank: true,
      };
    }
    const today = new Date();
    const in3 = new Date(today.getTime() + 3 * 86_400_000);
    const in10 = new Date(today.getTime() + 10 * 86_400_000);
    const example: [string, string, Date, Date, number, string][] = [
      ["1", "Preparación", today, in10, 0, STATUS_LABELS.not_started],
      ["1.1", "Kickoff del proyecto", today, in3, 0, STATUS_LABELS.not_started],
    ];
    example.forEach(([wbs, name, st, en, prog, status], i) => {
      const r = FIRST + i;
      ws.getCell(r, 1).value = wbs;
      const nc = ws.getCell(r, 2);
      nc.value = name;
      nc.font = { name: XLSX_FONT, size: 9, italic: true, color: { argb: DARK } };
      ws.getCell(r, 4).value = st;
      ws.getCell(r, 5).value = en;
      ws.getCell(r, 7).value = prog;
      ws.getCell(r, 8).value = status;
    });
    addInstructionsSheet(wb);
  }

  return wb;
}

function addInstructionsSheet(wb: Workbook) {
  const ws = wb.addWorksheet(SHEET_INSTRUCTIONS);
  ws.columns = [
    { header: "Columna", key: "col", width: 18 },
    { header: "Tipo", key: "type", width: 14 },
    { header: "Formato / Valores válidos", key: "format", width: 50 },
    { header: "Notas", key: "notes", width: 62 },
  ];
  const header = ws.getRow(1);
  header.font = { name: XLSX_FONT, bold: true };
  header.fill = { type: "pattern", pattern: "solid", fgColor: { argb: BAND } };
  const rows: Array<Record<string, string>> = [
    { col: "Encabezado (filas 1-5)", type: "Auto", format: "Info del proyecto + KPIs con fórmulas", notes: "No lo edites: el avance general, tareas, atrasadas e hitos se calculan solos. La tabla empieza en la fila 7." },
    { col: "WBS", type: "Texto", format: "Ej: 1, 1.1, 1.30.2", notes: "La columna viene en formato Texto — no lo cambies a número o Excel pierde los ceros (1.30 → 1.3)." },
    { col: "Tarea", type: "Texto", format: "Texto libre", notes: "Obligatorio. Filas sin tarea se ignoran al importar." },
    { col: "Nivel / Días", type: "Auto", format: "Fórmulas", notes: "Se calculan desde WBS y fechas. No editar." },
    { col: "Inicio / Fin", type: "Fecha", format: "YYYY-MM-DD", notes: "Con fechas la barra del Gantt (derecha) se pinta sola." },
    { col: "Avance", type: "%", format: "0% a 100%", notes: "Escribí 45 y Excel lo toma como 45%. La parte verde del Gantt avanza con este valor." },
    { col: "Estado", type: "Lista", format: Object.values(STATUS_LABELS).join(" | "), notes: "En español — el sistema lo importa igual. Colorea la celda solo." },
    { col: "Área / Responsable", type: "Texto", format: "Nombre del área / persona", notes: "Al importar se hace match contra áreas y pool de recursos." },
    { col: "Criticidad / Hito", type: "Lista", format: "Sí / No", notes: "Hito = rombo morado en el Gantt." },
    { col: "Hito Relacionado", type: "Texto", format: "WBS de un hito (ej. 1.5)", notes: "Se resuelve por WBS al importar." },
    { col: "Predecesoras", type: "CSV de WBS", format: "ej: 1.1, 1.2", notes: "Crean dependencias reales al importar." },
    { col: "Gantt (col Q →)", type: "Auto", format: "Formato condicional", notes: "Verde = avanzado, azul = pendiente, morado = hito, columna rosada = semana actual. No editar: se pinta solo." },
  ];
  for (const r of rows) {
    const added = ws.addRow(r);
    added.font = { name: XLSX_FONT, size: 9 };
    added.alignment = { vertical: "top", wrapText: true };
  }
}

/** Plantilla vacía (info del proyecto/charter + hoja Instrucciones). */
export async function buildEmptyTemplate(
  project: TemplateProjectInfo | string,
): Promise<Blob> {
  const info: TemplateProjectInfo =
    typeof project === "string" ? { name: project } : project;
  const wb = await buildPlanWorkbook(info, null);
  const buffer = await wb.xlsx.writeBuffer();
  return new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

/** Helper de UI: descarga la plantilla con un nombre canónico. */
export async function downloadEmptyTemplate(
  project: TemplateProjectInfo | string,
) {
  const projectName = typeof project === "string" ? project : project.name;
  const slug = (projectName || "proyecto")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  const blob = await buildEmptyTemplate(project);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `PLAN-PLANTILLA-${slug || "proyecto"}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
