import { apiFetch } from "@/lib/api";

export type Stakeholder = {
  id: string;
  tenant_id: string;
  organization_id: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  job_title: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type StakeholderCreateBody = {
  organization_id?: string | null;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  job_title?: string | null;
  notes?: string | null;
  is_active?: boolean;
};

export type StakeholderUpdateBody = Partial<StakeholderCreateBody>;

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function listStakeholders(
  params: { organization_id?: string; q?: string; is_active?: boolean } = {},
): Promise<Stakeholder[]> {
  return apiFetch<Stakeholder[]>(`/api/v1/stakeholders${qs(params)}`);
}

export function createStakeholder(body: StakeholderCreateBody): Promise<Stakeholder> {
  return apiFetch<Stakeholder>("/api/v1/stakeholders", { method: "POST", body });
}

export function updateStakeholder(
  id: string,
  body: StakeholderUpdateBody,
): Promise<Stakeholder> {
  return apiFetch<Stakeholder>(`/api/v1/stakeholders/${id}`, {
    method: "PATCH",
    body,
  });
}

export function deleteStakeholder(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/stakeholders/${id}`, { method: "DELETE" });
}

// US-088: hard delete (segundo paso) — stakeholders.
import type { HardDeletePreview } from "@/lib/api/organizations";

export function previewHardDeleteStakeholder(
  id: string,
): Promise<HardDeletePreview> {
  return apiFetch<HardDeletePreview>(`/api/v1/stakeholders/${id}/hard-delete-preview`);
}

export function hardDeleteStakeholder(id: string, confirm: string): Promise<void> {
  return apiFetch<void>(
    `/api/v1/stakeholders/${id}/permanent?confirm=${encodeURIComponent(confirm)}`,
    { method: "DELETE" },
  );
}
