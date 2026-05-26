/**
 * US-071 + US-096 — Plantilla XLSX descargable del Plan.
 *
 * Genera un XLSX en el browser con las columnas canónicas del export
 * (ENH-028, US-090, ENH-050/051) + 2 filas de ejemplo + hoja
 * "Instrucciones" con formatos válidos por columna. Roundtrip diseñado
 * para que el archivo descargado se pueda llenar y subir por el wizard
 * de import (US-070) sin necesidad de mapeo manual.
 *
 * US-096: agrega columnas Outline Level (auto fórmula), Criticidad,
 * Hito Relacionado, Predecessors, Successors. Conditional formatting
 * de Duración > 21 (regla buenas prácticas, US-090).
 */
import type { Workbook, Worksheet } from "exceljs";

const SHEET_PLAN = "Plan";
const SHEET_INSTRUCTIONS = "Instrucciones";

// ENH-134: orden de columnas canónico V1. Outline Level y Duración son
// auto-fórmula; Criticidad pasa a booleana (Sí/No) como Es hito; se agrega
// Área Responsable antes de Responsable.
const COLUMNS = [
  { header: "WBS", key: "wbs", width: 10 },                  // A
  { header: "Tarea", key: "name", width: 40 },               // B
  { header: "Outline Level", key: "outline", width: 12 },    // C (auto)
  { header: "Inicio", key: "start", width: 14 },             // D
  { header: "Fin", key: "end", width: 14 },                  // E
  { header: "Duración (días)", key: "duration", width: 16 }, // F (auto)
  { header: "Avance (%)", key: "progress", width: 12 },      // G
  { header: "Estado", key: "status", width: 16 },            // H
  { header: "Área Responsable", key: "area", width: 24 },    // I
  { header: "Responsable", key: "owner", width: 24 },        // J
  { header: "Criticidad", key: "criticality", width: 12 },   // K (Sí/No)
  { header: "Es hito", key: "milestone", width: 10 },        // L
  { header: "Hito Relacionado", key: "related_milestone", width: 18 }, // M
  { header: "Predecessors", key: "predecessors", width: 16 }, // N
  { header: "Successors", key: "successors", width: 16 },    // O (auto)
];

const VALID_STATUSES = ["not_started", "in_progress", "completed", "on_hold"];

// US-090 / BUG-050: limit operacional para Duración (días).
const MAX_DURATION_DAYS = 21;

// Última fila a la que aplicamos validations + fórmulas. 1000 es
// suficiente para proyectos reales y mantiene el archivo ligero.
const LAST_DATA_ROW = 1000;

function _styleHeader(ws: Worksheet) {
  const header = ws.getRow(1);
  // ENH-134: font negro.
  header.font = { bold: true, color: { argb: "FF000000" } };
  header.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: "FFE5E7EB" },
  };
  header.alignment = { vertical: "middle", horizontal: "left" };
  header.height = 22;
  ws.views = [{ state: "frozen", ySplit: 1 }];
}

function _addExampleRow(
  ws: Worksheet,
  data: Record<string, string | number | Date | boolean>,
) {
  const row = ws.addRow(data);
  // ENH-134: font negro (italic solo para indicar que son ejemplos).
  row.font = { color: { argb: "FF000000" }, italic: true };
  row.alignment = { vertical: "middle" };
  row.eachCell((cell) => {
    if (typeof cell.value === "string" && cell.value.startsWith("ej:")) {
      cell.value = cell.value.replace(/^ej:\s*/, "");
    }
  });
}

function _attachAutoFormulas(ws: Worksheet) {
  // US-096 CA2: Outline Level desde WBS.
  // =IF(A2="","",LEN(A2)-LEN(SUBSTITUTE(A2,".",""))+1)
  // US-096 CA3: Duración = Fin - Inicio + 1 (inclusivo).
  // =IF(AND(D2<>"",E2<>""),E2-D2+1,"")
  for (let r = 2; r <= LAST_DATA_ROW; r++) {
    ws.getCell(`C${r}`).value = {
      formula: `IF(A${r}="","",LEN(A${r})-LEN(SUBSTITUTE(A${r},".",""))+1)`,
    } as never;
    ws.getCell(`F${r}`).value = {
      formula: `IF(AND(D${r}<>"",E${r}<>""),E${r}-D${r}+1,"")`,
    } as never;
  }
}

function _attachDataValidation(ws: Worksheet) {
  for (let r = 2; r <= LAST_DATA_ROW; r++) {
    // Avance (%) — col G.
    ws.getCell(`G${r}`).dataValidation = {
      type: "whole",
      operator: "between",
      formulae: [0, 100],
      allowBlank: true,
      errorStyle: "warning",
      error: "Avance debe estar entre 0 y 100.",
    };
    // Estado — col H.
    ws.getCell(`H${r}`).dataValidation = {
      type: "list",
      formulae: [`"${VALID_STATUSES.join(",")}"`],
      allowBlank: true,
      errorStyle: "warning",
      error: `Estado debe ser uno de: ${VALID_STATUSES.join(", ")}.`,
    };
    // ENH-134: Criticidad ahora booleana (Sí/No) — col K.
    ws.getCell(`K${r}`).dataValidation = {
      type: "list",
      formulae: ['"Sí,No,Yes,No"'],
      allowBlank: true,
    };
    // Es hito — col L.
    ws.getCell(`L${r}`).dataValidation = {
      type: "list",
      formulae: ['"Sí,No,Yes,No"'],
      allowBlank: true,
    };
  }
}

function _attachConditionalFormatting(ws: Worksheet) {
  // US-096 CA4: Duración > 21 → fondo amarillo en la celda de Duración.
  // ExcelJS API: addConditionalFormatting con type=cellIs.
  ws.addConditionalFormatting({
    ref: `F2:F${LAST_DATA_ROW}`,
    rules: [
      {
        type: "cellIs",
        operator: "greaterThan",
        priority: 1,
        formulae: [String(MAX_DURATION_DAYS)],
        style: {
          fill: {
            type: "pattern",
            pattern: "solid",
            bgColor: { argb: "FFFFF8C5" },
          },
          font: { color: { argb: "FF92400E" }, bold: true },
        },
      } as never,
    ],
  });
}

function _addInstructionsSheet(wb: Workbook) {
  const ws = wb.addWorksheet(SHEET_INSTRUCTIONS);
  ws.columns = [
    { header: "Columna", key: "col", width: 18 },
    { header: "Tipo", key: "type", width: 14 },
    { header: "Formato / Valores válidos", key: "format", width: 50 },
    { header: "Notas", key: "notes", width: 60 },
  ];
  _styleHeader(ws);
  const rows: Array<Record<string, string>> = [
    {
      col: "WBS",
      type: "Texto",
      format: "Ej: 1, 1.1, 1.1.1",
      notes: "Identificador jerárquico. Opcional pero recomendado.",
    },
    {
      col: "Tarea",
      type: "Texto",
      format: "Texto libre",
      notes: "Obligatorio. Filas con tarea vacía se ignoran al importar.",
    },
    {
      col: "Outline Level",
      type: "Auto",
      format: "Fórmula =LEN(WBS)-LEN(SUB(WBS,'.',''))+1",
      notes: "US-096: se calcula automáticamente desde WBS. No editar.",
    },
    {
      col: "Inicio",
      type: "Fecha",
      format: "YYYY-MM-DD (ISO 8601)",
      notes: "Excel también acepta el tipo de celda Date.",
    },
    {
      col: "Fin",
      type: "Fecha",
      format: "YYYY-MM-DD",
      notes: "Si está vacío y hay duración, se calcula al importar.",
    },
    {
      col: "Duración (días)",
      type: "Auto",
      format: "Fórmula =Fin-Inicio+1",
      notes:
        `US-096: se calcula desde fechas. Conditional formatting amarillo si > ${MAX_DURATION_DAYS} días (fuera de buenas prácticas, US-090).`,
    },
    {
      col: "Avance (%)",
      type: "Entero",
      format: "0 a 100",
      notes:
        "Acepta también 0.0–1.0 (decimal) o '45%' al importar; aquí se valida como entero.",
    },
    {
      col: "Estado",
      type: "Lista",
      format: VALID_STATUSES.join(" | "),
      notes: "Default: not_started.",
    },
    {
      col: "Área Responsable",
      type: "Texto",
      format: "Nombre del área (ej: PMO, Infraestructura)",
      notes:
        "ENH-134. Al importar se hace match contra las áreas del proyecto; si no hay match, se ignora.",
    },
    {
      col: "Responsable",
      type: "Email o nombre",
      format: "ej: juan.perez@empresa.com",
      notes:
        "Al importar se hace fuzzy-match contra usuarios del tenant; si no hay match, queda como texto libre.",
    },
    {
      col: "Criticidad",
      type: "Lista",
      format: "Sí / No (también Yes/No)",
      notes: "ENH-134. Booleana: marca la tarea como crítica.",
    },
    {
      col: "Es hito",
      type: "Lista",
      format: "Sí / No (también Yes/No)",
      notes: "Marca la tarea como milestone (diamante en Gantt).",
    },
    {
      col: "Hito Relacionado",
      type: "Texto",
      format: "WBS de un hito existente (ej: 1.5)",
      notes:
        "ENH-050. Liga la tarea a un hito del mismo proyecto. Resolución por WBS al importar.",
    },
    {
      col: "Predecessors",
      type: "CSV de WBS",
      format: "ej: 1.1, 1.2",
      notes:
        "US-090. Lista de WBS separados por coma. Cada WBS debe existir en el plan.",
    },
    {
      col: "Successors",
      type: "Auto",
      format: "Calculado",
      notes:
        "US-090: se reconstruye desde Predecessors al importar. No editar.",
    },
  ];
  for (const r of rows) {
    ws.addRow(r);
  }
  ws.getRow(1).height = 22;

  ws.addRow({});
  const note = ws.addRow({
    col: "Nota",
    type: "—",
    format: "Llena las filas a partir de la fila 2 de la hoja 'Plan'.",
    notes:
      "Las 2 filas de ejemplo se sobreescriben al subir. El wizard de importación detecta las columnas automáticamente.",
  });
  note.font = { italic: true, color: { argb: "FF6B7280" } };
}

/**
 * Construye el XLSX en memoria y devuelve un Blob listo para descargar.
 */
export async function buildEmptyTemplate(projectName: string): Promise<Blob> {
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  wb.creator = "PMO aaS";
  wb.created = new Date();
  wb.title = `Plantilla de plan — ${projectName}`;

  const ws = wb.addWorksheet(SHEET_PLAN);
  ws.columns = COLUMNS;
  _styleHeader(ws);

  const today = new Date();
  const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
  const closingDay = new Date(today.getTime() + 9 * 24 * 60 * 60 * 1000);

  // Las celdas de Outline + Duración llevan fórmula; los ejemplos
  // dejan esas columnas vacías para que la fórmula se vea funcionando.
  _addExampleRow(ws, {
    wbs: "1.1",
    name: "Kickoff del proyecto",
    start: today,
    end: tomorrow,
    progress: 0,
    status: "not_started",
    area: "PMO",
    owner: "responsable@empresa.com",
    criticality: "No",
    milestone: "No",
    related_milestone: "",
    predecessors: "",
    successors: "",
  });
  _addExampleRow(ws, {
    wbs: "1.2",
    name: "Cierre de fase 1",
    start: closingDay,
    end: closingDay,
    progress: 0,
    status: "not_started",
    area: "PMO",
    owner: "",
    criticality: "Sí",
    milestone: "Sí",
    related_milestone: "",
    predecessors: "1.1",
    successors: "",
  });

  _attachAutoFormulas(ws);
  _attachDataValidation(ws);
  _attachConditionalFormatting(ws);
  _addInstructionsSheet(wb);

  const buffer = await wb.xlsx.writeBuffer();
  return new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

/**
 * Helper de UI: descarga la plantilla con un nombre canónico.
 */
export async function downloadEmptyTemplate(projectName: string) {
  const slug = (projectName || "proyecto")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  const blob = await buildEmptyTemplate(projectName);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `PLAN-PLANTILLA-${slug || "proyecto"}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
