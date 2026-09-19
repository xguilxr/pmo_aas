import { apiFetch } from "@/lib/api";

/**
 * US-286 — los catálogos de proyecto del inquilino.
 *
 * Dos, y solo dos: `tipo_proyecto` y `fase_proyecto`. La lista se escribe aquí
 * y no se deriva de la respuesta del servidor porque es el contrato: una
 * pantalla que pinte pestañas desde lo que le devuelvan no sabe qué hacer con
 * una tercera que no reconoce.
 */
export const CATALOGOS = ["tipo_proyecto", "fase_proyecto"] as const;

export type Catalogo = (typeof CATALOGOS)[number];

export const CATALOGO_LABEL: Record<Catalogo, string> = {
  tipo_proyecto: "Tipos de proyecto",
  fase_proyecto: "Fases",
};

export type ValorDeCatalogo = {
  id: string;
  catalogo: Catalogo;
  /** Lo que se guarda en el proyecto. No se edita. */
  clave: string;
  /** Lo que se lee en pantalla. Esto sí. */
  etiqueta: string;
  orden: number;
  activo: boolean;
  datos: Record<string, unknown>;
};

export function listarCatalogo(
  catalogo: Catalogo,
  params?: { incluirInactivos?: boolean },
): Promise<ValorDeCatalogo[]> {
  const qs = params?.incluirInactivos ? "?incluir_inactivos=true" : "";
  return apiFetch<ValorDeCatalogo[]>(`/api/v1/admin/catalogos/${catalogo}${qs}`);
}

export function crearValor(
  catalogo: Catalogo,
  body: { etiqueta: string; clave?: string; datos?: Record<string, unknown> },
): Promise<ValorDeCatalogo> {
  return apiFetch<ValorDeCatalogo>(`/api/v1/admin/catalogos/${catalogo}`, {
    method: "POST",
    body,
  });
}

export function editarValor(
  catalogo: Catalogo,
  id: string,
  body: { etiqueta?: string; activo?: boolean; datos?: Record<string, unknown> },
): Promise<ValorDeCatalogo> {
  return apiFetch<ValorDeCatalogo>(`/api/v1/admin/catalogos/${catalogo}/${id}`, {
    method: "PATCH",
    body,
  });
}

/** Reescribe el orden completo: el backend exige todas las claves. */
export function reordenarCatalogo(
  catalogo: Catalogo,
  claves: string[],
): Promise<ValorDeCatalogo[]> {
  return apiFetch<ValorDeCatalogo[]>(`/api/v1/admin/catalogos/${catalogo}/orden`, {
    method: "PUT",
    body: { claves },
  });
}

/**
 * US-288 — el catálogo para las pantallas que lo consumen, sin capability de
 * admin.
 *
 * Trae el catálogo **completo**, retirados incluidos, con `activo` en cada
 * valor. Quien llama hace dos cosas distintas con esta lista: ofrecer valores
 * —y ahí filtra por `activo`— y nombrar el que un proyecto ya tiene. Sin los
 * retirados, un proyecto con un tipo que se dejó de usar se pintaría con su
 * clave cruda.
 */
export function listarCatalogoVigente(
  catalogo: Catalogo,
): Promise<ValorDeCatalogo[]> {
  return apiFetch<ValorDeCatalogo[]>(`/api/v1/catalogos/${catalogo}`);
}
