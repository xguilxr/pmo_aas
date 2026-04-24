/**
 * US-071 — Plantilla vacía descargable del Plan.
 *
 * Genera un XLSX en el browser con las 9 columnas canónicas del export
 * (ENH-028) + 2 filas de ejemplo + hoja "Instrucciones" con formatos
 * válidos por columna. Roundtrip diseñado para que el archivo
 * descargado se pueda llenar y subir por el wizard de import (US-070)
 * sin necesidad de mapeo manual.
 */
import type { Workbook, Worksheet } from "exceljs";

const SHEET_PLAN = "Plan";
const SHEET_INSTRUCTIONS = "Instrucciones";

const COLUMNS = [
  { header: "WBS", key: "wbs", width: 10 },
  { header: "Tarea", key: "name", width: 40 },
  { header: "Inicio", key: "start", width: 14 },
  { header: "Fin", key: "end", width: 14 },
  { header: "Duración (días)", key: "duration", width: 16 },
  { header: "Avance (%)", key: "progress", width: 12 },
  { header: "Es hito", key: "milestone", width: 10 },
  { header: "Estado", key: "status", width: 16 },
  { header: "Responsable", key: "owner", width: 24 },
];

const VALID_STATUSES = ["not_started", "in_progress", "completed", "on_hold"];

function _styleHeader(ws: Worksheet) {
  const header = ws.getRow(1);
  header.font = { bold: true, color: { argb: "FF1F2937" } };
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
  row.font = { color: { argb: "FF6B7280" }, italic: true };
  row.alignment = { vertical: "middle" };
  row.eachCell((cell) => {
    if (typeof cell.value === "string" && cell.value.startsWith("ej:")) {
      cell.value = cell.value.replace(/^ej:\s*/, "");
    }
  });
}

function _attachDataValidation(ws: Worksheet, lastRow = 1000) {
  // Avance (%): entero 0-100 (col 6).
  for (let r = 2; r <= lastRow; r++) {
    ws.getCell(`F${r}`).dataValidation = {
      type: "whole",
      operator: "between",
      formulae: [0, 100],
      allowBlank: true,
      errorStyle: "warning",
      error: "Avance debe estar entre 0 y 100.",
    };
    ws.getCell(`G${r}`).dataValidation = {
      type: "list",
      formulae: ['"Sí,No,Yes,No"'],
      allowBlank: true,
    };
    ws.getCell(`H${r}`).dataValidation = {
      type: "list",
      formulae: [`"${VALID_STATUSES.join(",")}"`],
      allowBlank: true,
      errorStyle: "warning",
      error: `Estado debe ser uno de: ${VALID_STATUSES.join(", ")}.`,
    };
  }
}

function _addInstructionsSheet(wb: Workbook) {
  const ws = wb.addWorksheet(SHEET_INSTRUCTIONS);
  ws.columns = [
    { header: "Columna", key: "col", width: 18 },
    { header: "Tipo", key: "type", width: 14 },
    { header: "Formato / Valores válidos", key: "format", width: 50 },
    { header: "Notas", key: "notes", width: 50 },
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
      type: "Número",
      format: "Entero ≥ 0",
      notes: "Si es 0 y Es hito = Sí, se trata como hito.",
    },
    {
      col: "Avance (%)",
      type: "Entero",
      format: "0 a 100",
      notes:
        "Acepta también 0.0–1.0 (decimal) o '45%' al importar; aquí se valida como entero.",
    },
    {
      col: "Es hito",
      type: "Lista",
      format: "Sí / No (también Yes/No)",
      notes: "Marca la tarea como milestone (diamante en Gantt).",
    },
    {
      col: "Estado",
      type: "Lista",
      format: VALID_STATUSES.join(" | "),
      notes: "Default: not_started.",
    },
    {
      col: "Responsable",
      type: "Email o nombre",
      format: "ej: juan.perez@empresa.com",
      notes:
        "Al importar se hace fuzzy-match contra usuarios del tenant; si no hay match, queda como texto libre.",
    },
  ];
  for (const r of rows) {
    ws.addRow(r);
  }
  ws.getRow(1).height = 22;

  // Notas finales (US-071).
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

  // 2 filas de ejemplo en gris itálico.
  const today = new Date();
  const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
  const closingDay = new Date(today.getTime() + 9 * 24 * 60 * 60 * 1000);

  _addExampleRow(ws, {
    wbs: "1.1",
    name: "Kickoff del proyecto",
    start: today,
    end: tomorrow,
    duration: 2,
    progress: 0,
    milestone: "No",
    status: "not_started",
    owner: "responsable@empresa.com",
  });
  _addExampleRow(ws, {
    wbs: "1.2",
    name: "Cierre de fase 1",
    start: closingDay,
    end: closingDay,
    duration: 0,
    progress: 0,
    milestone: "Sí",
    status: "not_started",
    owner: "",
  });

  _attachDataValidation(ws);
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
