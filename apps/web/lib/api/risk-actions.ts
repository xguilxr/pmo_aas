// US-107 / ENH-083 — Acciones de mitigación del Riesgo (multi-actor).
import { apiFetch } from "@/lib/api";

export const RISK_ACTION_STATUS = ["open", "in_progress", "done", "blocked"] as const;
export type RiskActionStatus = (typeof RISK_ACTION_STATUS)[number];

export const RISK_ACTION_STATUS_LABEL: Record<RiskActionStatus, string> = {
  open: "Abierta",
  in_progress: "En curso",
  done: "Hecha",
  blocked: "Bloqueada",
};

export type RiskAction = {
  id: string;
  risk_id: string;
  short_desc: string;
  due_date: string | null;
  status: RiskActionStatus;
  assignee_actor_ids: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type RiskActionCreate = {
  short_desc: string;
  due_date?: string | null;
  status?: RiskActionStatus;
  assignee_actor_ids?: string[];
};

export type RiskActionUpdate = {
  short_desc?: string;
  due_date?: string | null;
  status?: RiskActionStatus;
  assignee_actor_ids?: string[];
};

export function listRiskActions(riskId: string): Promise<RiskAction[]> {
  return apiFetch<RiskAction[]>(`/api/v1/risks/${riskId}/actions`);
}

export function createRiskAction(
  riskId: string,
  body: RiskActionCreate,
): Promise<RiskAction> {
  return apiFetch<RiskAction>(`/api/v1/risks/${riskId}/actions`, {
    method: "POST",
    body,
  });
}

export function updateRiskAction(
  actionId: string,
  body: RiskActionUpdate,
): Promise<RiskAction> {
  return apiFetch<RiskAction>(`/api/v1/risk-actions/${actionId}`, {
    method: "PATCH",
    body,
  });
}

export function deleteRiskAction(actionId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/risk-actions/${actionId}`, { method: "DELETE" });
}
