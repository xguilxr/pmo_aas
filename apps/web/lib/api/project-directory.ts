// US-115/US-116 — cliente API para directorio de proyecto.
import { apiFetch } from "@/lib/api";

export type ProjectRole = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
};

export type ActorMini = {
  id: string;
  name: string;
  email: string | null;
  company: string | null;
  job_title: string | null;
};

// US-183: FTE% asignado + ciclo de vida de capacidad.
export type AssignmentType =
  | "directa"
  | "advisory"
  | "backup"
  | "shared_service"
  | "steerco_only";
export type AssignmentStatus = "tentativa" | "activa" | "cerrada" | "cancelada";

export const ASSIGNMENT_TYPE_LABEL: Record<AssignmentType, string> = {
  directa: "Directa",
  advisory: "Advisory",
  backup: "Backup",
  shared_service: "Servicio compartido",
  steerco_only: "Solo SteerCo",
};

export const ASSIGNMENT_STATUS_LABEL: Record<AssignmentStatus, string> = {
  tentativa: "Tentativa",
  activa: "Activa",
  cerrada: "Cerrada",
  cancelada: "Cancelada",
};

// US-217 — RACI. Las etiquetas y descripciones son las mismas que
// `app/dominio/raci.py`: si una letra cambia de significado, cambia en los dos
// sitios o la interfaz miente sobre lo que valida el backend.
export type RaciPapel = "A" | "R" | "C" | "I";

export const RACI_ORDEN: RaciPapel[] = ["A", "R", "C", "I"];

export const RACI_LABEL: Record<RaciPapel, string> = {
  A: "Responsable último (A)",
  R: "Ejecuta (R)",
  C: "Consultado (C)",
  I: "Informado (I)",
};

export const RACI_DESCRIPCION: Record<RaciPapel, string> = {
  A: "Responde por el resultado ante el sponsor. Solo puede haber una persona.",
  R: "Hace el trabajo. Puede haber varias.",
  C: "Se le pregunta antes de decidir.",
  I: "Se le informa de lo decidido.",
};

// Para ordenar la columna: la A primero, «sin papel» al final.
export const RACI_RANGO: Record<string, number> = { A: 0, R: 1, C: 2, I: 3 };

// US-215 — la unidad de tiempo de una tarifa. Sin ella `fte_cost_rate` es un
// número sin significado: «tarifa de un FTE» puede ser por hora, por día o por
// mes, y multiplicar suponiendo una da un costo creíble y falso.
export type PeriodoTarifa = "hora" | "dia" | "mes";

export const PERIODO_TARIFA_LABEL: Record<PeriodoTarifa, string> = {
  hora: "por hora",
  dia: "por día laborable",
  mes: "por mes",
};

export type Participation = {
  id: string;
  tenant_id: string;
  project_id: string;
  actor_id: string;
  operational_team_id: string | null;
  project_role_id: string | null;
  functional_area_id: string | null;
  is_area_lead: boolean;
  is_primary: boolean;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  // US-183.
  allocation_pct: number | null;
  assignment_type: AssignmentType;
  status: AssignmentStatus;
  is_critical: boolean;
  phase: string | null;
  // US-217.
  raci: RaciPapel | null;
  is_key_stakeholder: boolean;
  // US-215 — la tarifa congelada al asignar. Los cuatro nulos juntos significan
  // «sin tarifa congelada», que no es costo cero (DAT-12).
  cost_rate_snapshot: number | null;
  cost_currency: string | null;
  cost_rate_period: string | null;
  cost_rate_captured_at: string | null;
  // Derivado al leer, no guardado: un costo almacenado se queda viejo el día que
  // alguien mueve las fechas. `null` = no calculable, no cero.
  cost_total: number | null;
  created_at: string;
  actor?: ActorMini | null;
};

export type ParticipationCreate = {
  actor_id: string;
  operational_team_id?: string | null;
  project_role_id?: string | null;
  functional_area_id?: string | null;
  is_area_lead?: boolean;
  is_primary?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  is_active?: boolean;
  // US-183.
  allocation_pct?: number | null;
  assignment_type?: AssignmentType;
  status?: AssignmentStatus;
  is_critical?: boolean;
  phase?: string | null;
  // US-217.
  raci?: RaciPapel | null;
  is_key_stakeholder?: boolean;
  // US-215: la tarifa **no** se manda. Se congela del catálogo al crear, o con
  // `freezeCostRate` después. Dictarla desde aquí permitiría registrar un costo
  // que no corresponde a ninguna tarifa aprobada.
};

export type ParticipationUpdate = Omit<Partial<ParticipationCreate>, "raci"> & {
  // US-217: `undefined` es «no lo mandes» —el PATCH usa `exclude_unset`—, así
  // que para **quitar** el papel hace falta un valor que viaje. Es `""` y no
  // `null` porque el schema lo declara así: un `Literal[""]` explícito deja el
  // borrado documentado en el contrato en vez de escondido en un `None`.
  raci?: RaciPapel | "" | null;
};

// Project roles
export const listProjectRoles = (params?: { is_active?: boolean }) =>
  apiFetch<ProjectRole[]>(
    `/api/v1/project-roles${params?.is_active !== undefined ? `?is_active=${params.is_active}` : ""}`,
  );

export const createProjectRole = (body: {
  name: string;
  description?: string | null;
  is_active?: boolean;
}) =>
  apiFetch<ProjectRole>(`/api/v1/project-roles`, {
    method: "POST",
    body,
  });

export const updateProjectRole = (
  id: string,
  body: { name?: string; description?: string | null; is_active?: boolean },
) =>
  apiFetch<ProjectRole>(`/api/v1/project-roles/${id}`, {
    method: "PATCH",
    body,
  });

export const deleteProjectRole = (id: string) =>
  apiFetch<void>(`/api/v1/project-roles/${id}`, { method: "DELETE" });

// Participations
export const listParticipations = (
  projectId: string,
  opts?: { include?: "actor"; is_active?: boolean; is_primary?: boolean },
) => {
  const qp = new URLSearchParams();
  if (opts?.include) qp.set("include", opts.include);
  if (opts?.is_active !== undefined) qp.set("is_active", String(opts.is_active));
  if (opts?.is_primary !== undefined) qp.set("is_primary", String(opts.is_primary));
  const qs = qp.toString();
  return apiFetch<Participation[]>(
    `/api/v1/projects/${projectId}/participations${qs ? `?${qs}` : ""}`,
  );
};

export const createParticipation = (
  projectId: string,
  body: ParticipationCreate,
) =>
  apiFetch<Participation>(`/api/v1/projects/${projectId}/participations`, {
    method: "POST",
    body,
  });

export const updateParticipation = (
  projectId: string,
  participationId: string,
  body: ParticipationUpdate,
) =>
  apiFetch<Participation>(
    `/api/v1/projects/${projectId}/participations/${participationId}`,
    { method: "PATCH", body },
  );

export const deleteParticipation = (projectId: string, participationId: string) =>
  apiFetch<void>(`/api/v1/projects/${projectId}/participations/${participationId}`, {
    method: "DELETE",
  });

// US-215 — costo de recursos.
export type ResumenCosto = {
  // Un importe por moneda, nunca un total único: dos personas facturadas en
  // monedas distintas no tienen un costo total.
  by_currency: Record<string, number>;
  assignments: number;
  // Cuántas asignaciones quedaron sin costo calculable. Viene con el total
  // porque un total sin este número miente por omisión.
  without_rate: number;
  // El código si todo está en la misma moneda; `null` si hay varias o ninguna.
  single_currency: string | null;
};

export const freezeCostRate = (projectId: string, participationId: string) =>
  apiFetch<Participation>(
    `/api/v1/projects/${projectId}/participations/${participationId}/freeze-cost-rate`,
    { method: "POST" },
  );

export const getProjectCostSummary = (projectId: string) =>
  apiFetch<ResumenCosto>(
    `/api/v1/projects/${projectId}/participations/cost-summary`,
  );

// US-117 — actores eligibles para dropdowns de assignee/owner.
export const listEligibleActors = (projectId: string) =>
  apiFetch<ActorMini[]>(`/api/v1/projects/${projectId}/eligible-actors`);
