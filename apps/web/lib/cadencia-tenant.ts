import { useTenantBranding } from "@/components/tenant-branding-provider";

/**
 * US-213 — cada cuántos días reporta esta PMO.
 *
 * Catorce por defecto: la cadencia bi-semanal que piden los mockups. El valor
 * llega con el branding del inquilino por el mismo motivo que la moneda —lo
 * necesitan el rótulo de la tendencia, el muestreo de la serie y el historial de
 * cortes—, así que ninguna pantalla tiene que ir a pedirlo aparte.
 *
 * Vive junto a `moneda-tenant.ts` y por la misma razón: lee el contexto de
 * React, y meterlo en un módulo puro obligaría a marcarlo entero como de
 * cliente.
 */
export const CADENCIA_POR_DEFECTO_DIAS = 14;

export function useCadenciaDeReporte(): number {
  const { branding } = useTenantBranding();
  const dias = branding?.reporting_cadence_days;
  // Un valor no positivo se descarta: cero días haría que el muestreo devolviera
  // la serie cruda y el rótulo dijera «cada 0 días».
  return typeof dias === "number" && dias > 0 ? dias : CADENCIA_POR_DEFECTO_DIAS;
}

/**
 * Cómo se dice esa cadencia en una frase.
 *
 * Se nombra el caso conocido y se cae a los días para el resto: «cada 17 días»
 * es feo pero es verdad, y «bi-semanal» de una cadencia de diecisiete días es
 * mentira. Los tres nombres que existen son los que una PMO usa.
 */
export function etiquetaDeCadencia(dias: number): string {
  if (dias === 7) return "semanal";
  if (dias === 14) return "bi-semanal";
  if (dias === 30 || dias === 31) return "mensual";
  return `cada ${dias} días`;
}
