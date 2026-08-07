import { apiBase, apiFetch } from "@/lib/api";

// US-152 — cliente de los endpoints de analytics para dashboards N1/N2.

export type ScopeType = "tenant" | "organization" | "program" | "project";

export type ScopeParams = {
  scope?: ScopeType;
  id?: string;
};

export type TrendPoint = {
  snapshot_date: string;
  [metric: string]: number | string;
};

export type TrendsResponse = {
  scope: ScopeType;
  scope_id: string;
  metric: string | null;
  series: TrendPoint[];
};

export type RiskMatrixCell = {
  probability: number;
  impact: number;
  count: number;
};

export type RiskMatrixResponse = {
  cells: RiskMatrixCell[];
  total: number;
};

export type HeatmapRow = {
  org_id: string;
  org_name: string;
  green: number;
  yellow: number;
  red: number;
  total: number;
};

export type HeatmapResponse = { rows: HeatmapRow[] };

export type TreemapProject = {
  id: string;
  name: string;
  folio: string;
  value: number;
  health: string | null;
};
export type TreemapProgram = { id: string; name: string; children: TreemapProject[] };
export type TreemapOrg = { id: string; name: string; children: TreemapProgram[] };
export type TreemapResponse = { tree: TreemapOrg[] };

// US-181: matriz Proyecto × Dimensión de salud (salud única híbrida).
export type HealthMatrixRow = {
  project_id: string;
  folio: string;
  name: string;
  organization_id: string;
  organization_name: string | null;
  health_status: "green" | "yellow" | "red";
  health_source: "auto" | "manual";
  priority: number | null;
  dims: Record<string, "green" | "yellow" | "red" | null>;
};
export type HealthMatrixResponse = { rows: HealthMatrixRow[] };

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function getTrends(
  params: ScopeParams & { metric?: string; weeks?: number } = {},
): Promise<TrendsResponse> {
  return apiFetch<TrendsResponse>(`/api/v1/dashboard/trends${qs(params)}`);
}

export function getRiskMatrix(params: ScopeParams = {}): Promise<RiskMatrixResponse> {
  return apiFetch<RiskMatrixResponse>(`/api/v1/dashboard/risk-matrix${qs(params)}`);
}

export function getHeatmap(): Promise<HeatmapResponse> {
  return apiFetch<HeatmapResponse>(`/api/v1/dashboard/heatmap`);
}

export function getHealthMatrix(): Promise<HealthMatrixResponse> {
  return apiFetch<HealthMatrixResponse>(`/api/v1/dashboard/health-matrix`);
}

// US-192 — evaluaciones recientes de todos los proyectos visibles
// (insumo del reporte de salud del portafolio).
export type PortfolioHealthEvaluation = {
  project_id: string;
  evaluated_at: string;
  schedule: string | null;
  budget: string | null;
  risks: string | null;
  decisions: string | null;
  resources: string | null;
  overall: string;
  note: string | null;
};

export function getPortfolioHealthEvaluations(): Promise<{
  rows: PortfolioHealthEvaluation[];
}> {
  return apiFetch<{ rows: PortfolioHealthEvaluation[] }>(
    `/api/v1/dashboard/health-evaluations`,
  );
}

export function getTreemap(params: ScopeParams = {}): Promise<TreemapResponse> {
  return apiFetch<TreemapResponse>(`/api/v1/dashboard/treemap${qs(params)}`);
}

export function captureSnapshots(): Promise<{ date: string; rows: number }> {
  return apiFetch<{ date: string; rows: number }>(
    `/api/v1/dashboard/snapshots/capture`,
    { method: "POST" },
  );
}

// US-160 — reportes de status N1/N2 (PDF, fuera del builder). Descarga binaria.
async function _downloadPdf(path: string, filename: string): Promise<void> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/pdf",
    },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`No se pudo generar el reporte (${res.status}): ${txt.slice(0, 200)}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const _stamp = () => new Date().toISOString().slice(0, 10);

export function downloadPortfolioStatusReport(): Promise<void> {
  return _downloadPdf(`/api/v1/dashboard/reports/portfolio`, `status-portafolio-${_stamp()}.pdf`);
}

export function downloadOrgStatusReport(orgId: string): Promise<void> {
  return _downloadPdf(`/api/v1/organizations/${orgId}/reports/status`, `status-org-${_stamp()}.pdf`);
}

export function downloadProgramStatusReport(programId: string): Promise<void> {
  return _downloadPdf(`/api/v1/programs/${programId}/reports/status`, `status-programa-${_stamp()}.pdf`);
}

// US-187 — organigrama con utilización (XLSX) por scope. A diferencia de
// `_downloadPdf` (nombre fijo generado en el cliente), estos endpoints GET
// ya devuelven el filename listo vía `Content-Disposition` (US-186), así
// que lo parseamos en vez de inventarlo.
function _filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      // cae al filename simple
    }
  }
  const plainMatch = /filename="?([^";]+)"?/i.exec(header);
  return plainMatch?.[1] ?? fallback;
}

const XLSX_ACCEPT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

async function _downloadXlsx(path: string, fallbackFilename: string): Promise<void> {
  const res = await fetch(`${apiBase()}${path}`, {
    headers: {
      Accept: XLSX_ACCEPT,
    },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`No se pudo generar el organigrama (${res.status}): ${txt.slice(0, 200)}`);
  }
  const blob = await res.blob();
  const filename = _filenameFromDisposition(res.headers.get("Content-Disposition"), fallbackFilename);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadOrganizationOrganigrama(orgId: string): Promise<void> {
  return _downloadXlsx(
    `/api/v1/organizations/${orgId}/organigrama/export`,
    `organigrama-org-${_stamp()}.xlsx`,
  );
}

export function downloadProgramOrganigrama(programId: string): Promise<void> {
  return _downloadXlsx(
    `/api/v1/programs/${programId}/organigrama/export`,
    `organigrama-programa-${_stamp()}.xlsx`,
  );
}

export function downloadGlobalOrganigrama(): Promise<void> {
  return _downloadXlsx(
    `/api/v1/capacity/organigrama/export`,
    `organigrama-global-${_stamp()}.xlsx`,
  );
}
