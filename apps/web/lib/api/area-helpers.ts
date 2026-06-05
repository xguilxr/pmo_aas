// BUG-071 — helpers compartidos entre los flujos que crean áreas en
// contexto de proyecto (DirectoryView inline-create, AreasAndTeamsPanel).
// El objetivo es que ambos flujos manejen el mismo edge-case: si el área
// ya existe en el catálogo tenant sin assignment al proyecto, "adoptarla"
// en lugar de tirar 409.

import { ApiError } from "@/lib/api";
import {
  createArea,
  listAreaAssignments,
  setAreaAssignments,
  type Area,
} from "@/lib/api/areas";

/**
 * Garantiza que `areaId` quede visible para `projectId` sin pisar otros
 * scopes ya configurados (merge no destructivo de assignments). Idempotente.
 */
export async function ensureProjectAssignment(
  areaId: string,
  projectId: string,
): Promise<void> {
  const existing = await listAreaAssignments(areaId);
  const alreadyVisible = existing.some(
    (a) => a.is_global || a.project_id === projectId,
  );
  if (alreadyVisible) return;
  await setAreaAssignments(areaId, [
    ...existing.map((a) => ({
      organization_id: a.organization_id,
      program_id: a.program_id,
      project_id: a.project_id,
      is_global: a.is_global,
    })),
    { project_id: projectId },
  ]);
}

/**
 * Crea un área y la asigna al proyecto. Si ya existe un área con el
 * mismo nombre en el tenant (409 AREA_NAME_DUPLICATE), se adopta la
 * existente y se le agrega un assignment al proyecto en lugar de fallar.
 *
 * Devuelve el id del área (ya sea recién creada o adoptada).
 *
 * Si la creación tiene éxito pero la asignación falla, propaga el error
 * — no lo traga silencioso. El área queda en el catálogo tenant pero el
 * usuario sabe que algo salió mal.
 */
export async function createOrAdoptAreaForProject(
  name: string,
  projectId: string,
): Promise<{ id: string; adopted: boolean; area?: Area }> {
  try {
    const created = await createArea({ name, is_active: true });
    await ensureProjectAssignment(created.id, projectId);
    return { id: created.id, adopted: false, area: created };
  } catch (err) {
    if (err instanceof ApiError && err.code === "AREA_NAME_DUPLICATE") {
      const existingId = err.fields?.existing_area_id;
      if (typeof existingId === "string" && existingId) {
        await ensureProjectAssignment(existingId, projectId);
        return { id: existingId, adopted: true };
      }
    }
    throw err;
  }
}
