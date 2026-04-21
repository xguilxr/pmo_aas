import { apiFetch } from "@/lib/api";
import type {
  ChangeRequest,
  Issue,
  IssueType,
  MeetingMinute,
  Risk,
} from "./modules";

export type TenantCrossFilter = {
  organization_id?: string;
  program_id?: string;
  project_id?: string;
};

function toQs(filter: TenantCrossFilter & Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filter)) {
    if (v) params.append(k, v);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function listTenantRisks(filter: TenantCrossFilter = {}): Promise<Risk[]> {
  return apiFetch<Risk[]>(`/api/v1/tenant/risks${toQs(filter)}`);
}

export function listTenantIssues(
  filter: TenantCrossFilter & { type?: IssueType } = {},
): Promise<Issue[]> {
  return apiFetch<Issue[]>(`/api/v1/tenant/issues${toQs(filter)}`);
}

export function listTenantChanges(
  filter: TenantCrossFilter & { status?: string } = {},
): Promise<ChangeRequest[]> {
  return apiFetch<ChangeRequest[]>(`/api/v1/tenant/change-requests${toQs(filter)}`);
}

export function listTenantMinutes(
  filter: TenantCrossFilter = {},
): Promise<MeetingMinute[]> {
  return apiFetch<MeetingMinute[]>(`/api/v1/tenant/meeting-minutes${toQs(filter)}`);
}

export type TenantReport = {
  id: string;
  project_id: string;
  folio: string;
  title: string;
  report_type: string | null;
  period: string | null;
  status: string;
  created_at: string;
};

export function listTenantReports(
  filter: TenantCrossFilter = {},
): Promise<TenantReport[]> {
  return apiFetch<TenantReport[]>(`/api/v1/tenant/reports${toQs(filter)}`);
}
