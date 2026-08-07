import { apiFetch } from "@/lib/api";

export type RequestStatus = "in_review" | "needs_info" | "approved" | "rejected";

export type RequestAttachment = {
  filename: string;
  url: string;
  size: number;
  mime: string;
};

export type ProjectRequest = {
  /** BUG-092 — moneda del importe, ya resuelta por la API. */
  currency: string;
  id: string;
  folio: string;
  title: string;
  description: string;
  objective: string;
  organization_id: string;
  business_unit: string;
  department: string;
  business_unit_id: string | null;
  department_id: string | null;
  sponsor: string;
  sponsor_email: string | null;
  benefits: string;
  budget: string | null;
  scope: string;
  entregables: string | null;
  key_people: string | null;
  if_not_done: string | null;
  observations: string | null;
  requester_name: string | null;
  requester_email: string | null;
  delivery_constraint_date: string | null;
  status: RequestStatus;
  requested_by: string;
  requested_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_comment: string | null;
  attachments: RequestAttachment[];
  project_id: string | null;
};

export type ProjectRequestCreateBody = {
  title: string;
  /** BUG-092 — moneda del presupuesto. `null` = la preferida del inquilino. */
  currency?: string | null;
  description: string;
  objective: string;
  // US-085: si null + organization_name_new presente, backend crea la
  // org como inactiva.
  organization_id: string | null;
  organization_name_new?: string | null;
  business_unit: string;
  department: string;
  business_unit_id?: string | null;
  department_id?: string | null;
  sponsor: string;
  sponsor_email: string;
  benefits: string;
  budget?: number | string | null;
  scope: string;
  entregables?: string | null;
  key_people?: string | null;
  if_not_done?: string | null;
  observations?: string | null;
  requester_name?: string | null;
  requester_email?: string | null;
  delivery_constraint_date?: string | null;
  attachments?: RequestAttachment[];
};

export type ProjectRequestUpdateBody = Partial<
  Omit<ProjectRequestCreateBody, "organization_id" | "attachments">
>;

export type ListRequestsParams = {
  status?: RequestStatus;
  organization_id?: string;
  q?: string;
  page?: number;
  limit?: number;
};

export type ReviewDecision = "approve" | "reject" | "needs_info";

export type ReviewBody = {
  decision: ReviewDecision;
  comment?: string | null;
};

export type CreateProjectFromRequestBody = {
  pm_id: string;
};

export type CreateProjectFromRequestResult = {
  project_id: string;
  folio?: string;
  idempotent: boolean;
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

export function listRequests(params: ListRequestsParams = {}): Promise<ProjectRequest[]> {
  return apiFetch<ProjectRequest[]>(`/api/v1/project-requests${qs(params)}`);
}

export function getRequest(id: string): Promise<ProjectRequest> {
  return apiFetch<ProjectRequest>(`/api/v1/project-requests/${id}`);
}

export function createRequest(body: ProjectRequestCreateBody): Promise<ProjectRequest> {
  return apiFetch<ProjectRequest>("/api/v1/project-requests", { method: "POST", body });
}

export function updateRequest(
  id: string,
  body: ProjectRequestUpdateBody,
): Promise<ProjectRequest> {
  return apiFetch<ProjectRequest>(`/api/v1/project-requests/${id}`, { method: "PATCH", body });
}

export function reviewRequest(id: string, body: ReviewBody): Promise<ProjectRequest> {
  return apiFetch<ProjectRequest>(`/api/v1/project-requests/${id}/review`, {
    method: "POST",
    body,
  });
}

export function resubmitRequest(id: string): Promise<ProjectRequest> {
  return apiFetch<ProjectRequest>(`/api/v1/project-requests/${id}/resubmit`, {
    method: "POST",
  });
}

/**
 * ENH-016: reabrir una solicitud aprobada (devuelve a `in_review`). Solo
 * disponible si aún no se creó un proyecto desde la solicitud.
 */
export function reopenRequest(id: string): Promise<ProjectRequest> {
  return apiFetch<ProjectRequest>(`/api/v1/project-requests/${id}/reopen`, {
    method: "POST",
  });
}

export function createProjectFromRequest(
  id: string,
  body: CreateProjectFromRequestBody,
): Promise<CreateProjectFromRequestResult> {
  return apiFetch<CreateProjectFromRequestResult>(
    `/api/v1/project-requests/${id}/create-project`,
    { method: "POST", body },
  );
}

export const REQUEST_STATUS_LABEL: Record<RequestStatus, string> = {
  in_review: "En revisión",
  needs_info: "Pendiente info",
  approved: "Aprobada",
  rejected: "Rechazada",
};
