import { apiFetch } from "@/lib/api";

export type Organization = {
  id: string;
  name: string;
  reason_social: string | null;
  industry: string | null;
  country: string | null;
  contact_email: string | null;
  logo_url: string | null;
  is_active: boolean;
};

export type OrganizationCreateBody = {
  name: string;
  reason_social?: string | null;
  industry?: string | null;
  country?: string | null;
  contact_email?: string | null;
  is_active?: boolean;
};

export type OrganizationUpdateBody = Partial<OrganizationCreateBody>;

export type ListOrgsParams = {
  q?: string;
  is_active?: boolean;
};

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function listOrganizations(params: ListOrgsParams = {}): Promise<Organization[]> {
  return apiFetch<Organization[]>(`/api/v1/organizations${qs(params)}`);
}

export function getOrganization(id: string): Promise<Organization> {
  return apiFetch<Organization>(`/api/v1/organizations/${id}`);
}

export function createOrganization(body: OrganizationCreateBody): Promise<Organization> {
  return apiFetch<Organization>("/api/v1/organizations", { method: "POST", body });
}

export function updateOrganization(
  id: string,
  body: OrganizationUpdateBody,
): Promise<Organization> {
  return apiFetch<Organization>(`/api/v1/organizations/${id}`, { method: "PATCH", body });
}

export function deleteOrganization(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/organizations/${id}`, { method: "DELETE" });
}

export type Program = {
  id: string;
  name: string;
  organization_id: string;
  description: string | null;
  strategic_alignment: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
};

export type ProgramCreateBody = {
  name: string;
  organization_id: string;
  description?: string | null;
  strategic_alignment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ProgramUpdateBody = {
  name?: string;
  description?: string | null;
  strategic_alignment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
};

export type ListProgramsParams = {
  organization_id?: string;
  is_active?: boolean;
};

export function listPrograms(params: ListProgramsParams = {}): Promise<Program[]> {
  return apiFetch<Program[]>(`/api/v1/programs${qs(params)}`);
}

export function createProgram(body: ProgramCreateBody): Promise<Program> {
  return apiFetch<Program>("/api/v1/programs", { method: "POST", body });
}

export function updateProgram(id: string, body: ProgramUpdateBody): Promise<Program> {
  return apiFetch<Program>(`/api/v1/programs/${id}`, { method: "PATCH", body });
}

export function deleteProgram(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/programs/${id}`, { method: "DELETE" });
}
