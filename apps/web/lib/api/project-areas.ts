/**
 * ENH-078 (2026-05-07): shim de compatibilidad post drop de
 * `project_areas`. Las áreas ahora viven en el catálogo tenant
 * (`/api/v1/areas`) con `area_assignments` controlando visibilidad
 * por proyecto. Este módulo expone la API legacy mapeada al nuevo
 * endpoint para que RAID/Plan no requieran rewrite inmediato.
 *
 * Se mantienen sólo las funciones consumidas por componentes vivos.
 * CRUD de áreas/equipos/actores se hace ahora vía `/lib/api/areas.ts`.
 */
import { apiFetch } from "@/lib/api";

export type ProjectAreaType = "area" | "actor" | "team";

export type ProjectArea = {
  id: string;
  project_id: string;
  name: string;
  type: ProjectAreaType;
  description: string | null;
  contact_name: string | null;
  contact_email: string | null;
  area_leader_id: string | null;
  team_id: string | null;
  area_id: string | null;
  phone: string | null;
  is_active: boolean;
};

type AreaCatalogRead = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  lead_actor_id: string | null;
  is_active: boolean;
};

/**
 * Lista las áreas visibles para el proyecto (cascada org/program/proj/global).
 * Sólo retorna áreas (type='area'); equipos/actores no se exponen aquí.
 * Si el caller filtra por type !== 'area', devuelve [].
 */
export async function listProjectAreas(
  projectId: string,
  params: { q?: string; is_active?: boolean; type?: ProjectAreaType } = {},
): Promise<ProjectArea[]> {
  if (params.type && params.type !== "area") return [];
  const rows = await apiFetch<AreaCatalogRead[]>(
    `/api/v1/admin/areas/by-project/${projectId}`,
  );
  const q = params.q?.trim().toLowerCase();
  return rows
    .filter((a) =>
      params.is_active !== undefined ? a.is_active === params.is_active : true,
    )
    .filter((a) => (q ? a.name.toLowerCase().includes(q) : true))
    .map<ProjectArea>((a) => ({
      id: a.id,
      project_id: projectId,
      name: a.name,
      type: "area",
      description: a.description,
      contact_name: null,
      contact_email: null,
      area_leader_id: a.lead_actor_id,
      team_id: null,
      area_id: null,
      phone: null,
      is_active: a.is_active,
    }));
}
