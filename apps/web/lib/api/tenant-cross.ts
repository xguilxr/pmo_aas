import { apiFetch } from "@/lib/api";
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
