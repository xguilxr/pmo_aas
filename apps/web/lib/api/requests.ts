import { apiFetch } from "@/lib/api";

export type RequestStatus = "in_review" | "needs_info" | "approved" | "rejected";

export type RequestAttachment = {
  filename: string;
  url: string;
  size: number;
  mime: string;
};

export type ProjectRequest = {
  id: string;
  folio: string;
  title: string;
  description: string;
  objective: string;
  organization_id: string;
  business_unit: string;
  department: string;
  sponsor: string;
  benefits: string;
  budget: string;
  scope: string;
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
  description: string;
  objective: string;
  organization_id: string;
  business_unit: string;
  department: string;
  sponsor: string;
  benefits: string;
  budget: number | string;
  scope: string;
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
