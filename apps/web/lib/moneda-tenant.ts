import { useTenantBranding } from "@/components/tenant-branding-provider";
import { POR_DEFECTO } from "@/lib/moneda";

/**
 * BUG-092 — la moneda **preferida** del inquilino, para lo que no cuelga de un
 * proyecto: gráficos de cartera, filas agregadas, encabezados de sección.
 *
 * No sirve para el importe de un proyecto concreto: ese trae la suya ya
 * resuelta por la API (`project.currency`), y usar la preferida en su lugar es
 * exactamente el bug que esto viene a cerrar, un escalón más arriba.
 *
 * Vive aparte de `lib/moneda.ts` porque aquello es puro —formatea— y esto lee
 * el contexto de React. Juntarlos obligaría a marcar el módulo entero como de
 * cliente para poder formatear un número.
 */
export function useMonedaPreferida(): string {
  const { branding } = useTenantBranding();
  return branding?.preferred_currency ?? POR_DEFECTO;
}
