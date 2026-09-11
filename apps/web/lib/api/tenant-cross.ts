import { apiBase, apiFetch } from "@/lib/api";
import type {
  ChangeRequest,
  Issue,
  IssueStatus,
  IssueType,
  MeetingMinute,
  Risk,
  RiskStatus,
} from "./modules";

export type TenantCrossFilter = {
  organization_id?: string;
  /** US-201 — el nivel nuevo, entre organización y programa. */
  portfolio_id?: string;
  program_id?: string;
  project_id?: string;
};

/** ENH-019: filtros avanzados para RAID (cross-tenant). */
export type TenantRisksFilter = TenantCrossFilter & {
  status?: RiskStatus;
  severity_min?: number;
  owner_id?: string;
};

export type TenantIssuesFilter = TenantCrossFilter & {
  type?: IssueType;
  status?: IssueStatus;
  priority_min?: number;
  owner_id?: string;
};

// ENH-010: todos los endpoints cross-tenant incluyen los campos del
// proyecto (`project_folio`, `project_name`) junto al recurso, para
// que la UI muestre el proyecto legible en vez del UUID abreviado.
type WithProject<T> = T & {
  project_folio: string;
  project_name: string;
};

export type TenantRisk = WithProject<Risk>;
export type TenantIssue = WithProject<Issue>;
export type TenantChange = WithProject<ChangeRequest>;
export type TenantMinute = WithProject<MeetingMinute>;

function toQs(
  filter: Record<string, string | number | undefined | null>,
): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filter)) {
    if (v === undefined || v === null || v === "") continue;
    params.append(k, String(v));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function listTenantRisks(
  filter: TenantRisksFilter = {},
): Promise<TenantRisk[]> {
  return apiFetch<TenantRisk[]>(`/api/v1/tenant/risks${toQs(filter)}`);
}

export function listTenantIssues(
  filter: TenantIssuesFilter = {},
): Promise<TenantIssue[]> {
  return apiFetch<TenantIssue[]>(`/api/v1/tenant/issues${toQs(filter)}`);
}

export function listTenantChanges(
  filter: TenantCrossFilter & { status?: string } = {},
): Promise<TenantChange[]> {
  return apiFetch<TenantChange[]>(`/api/v1/tenant/change-requests${toQs(filter)}`);
}

export function listTenantMinutes(
  filter: TenantCrossFilter = {},
): Promise<TenantMinute[]> {
  return apiFetch<TenantMinute[]>(`/api/v1/tenant/meeting-minutes${toQs(filter)}`);
}

export type TenantReport = WithProject<{
  id: string;
  project_id: string;
  folio: string;
  title: string;
  report_type: string | null;
  period: string | null;
  status: string;
  created_at: string;
}>;

export function listTenantReports(
  filter: TenantCrossFilter = {},
): Promise<TenantReport[]> {
  return apiFetch<TenantReport[]>(`/api/v1/tenant/reports${toQs(filter)}`);
}

// FASE-8 (revamp v2, US-A/B/C) — botón "Descargar Excel" de las pestañas
// RAID y Cambios de `/pmo/reports`. Mismo patrón que `_downloadXlsx` de
// `lib/api/analytics.ts`: el filename ya viene listo por `Content-Disposition`.
const XLSX_ACCEPT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

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

async function _downloadXlsx(path: string, fallbackFilename: string): Promise<void> {
  const res = await fetch(`${apiBase()}${path}`, {
    headers: { Accept: XLSX_ACCEPT },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`No se pudo generar el archivo (${res.status}): ${txt.slice(0, 200)}`);
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

export function downloadTenantRaidExcel(filter: TenantCrossFilter = {}): Promise<void> {
  return _downloadXlsx(`/api/v1/tenant/raid/export${toQs(filter)}`, "raid.xlsx");
}

export function downloadTenantChangesExcel(filter: TenantCrossFilter = {}): Promise<void> {
  return _downloadXlsx(
    `/api/v1/tenant/change-requests/export${toQs(filter)}`,
    "cambios.xlsx",
  );
}
