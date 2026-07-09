"use client";

/**
 * ENH-190 — Label de UI configurable por tenant para
 * "Organización/Organizaciones" (algunos tenants prefieren
 * "Portafolio/Portafolios" cuando el cliente gestiona su propio
 * portafolio).
 *
 * Puramente cosmético: NO cambia rutas, tipos ni el shape de las APIs
 * de `organizations`. Solo el texto visible en la UI.
 *
 * Fuente del valor efectivo: `org_label` en la respuesta de
 * `/api/v1/me/tenant-branding`, ya cacheada/consumida por
 * `<TenantBrandingProvider>` (ver `components/tenant-branding-provider.tsx`).
 */
import { useTenantBranding } from "@/components/tenant-branding-provider";

export type OrgLabelValue = "organizations" | "portfolios";

export type OrgLabelStrings = {
  singular: string;
  plural: string;
  /** "una organización" / "un portafolio" (para frases tipo "Selecciona ___") */
  singularArticled: string;
};

const LABELS: Record<OrgLabelValue, OrgLabelStrings> = {
  organizations: {
    singular: "Organización",
    plural: "Organizaciones",
    singularArticled: "una organización",
  },
  portfolios: {
    singular: "Portafolio",
    plural: "Portafolios",
    singularArticled: "un portafolio",
  },
};

export function orgLabelStrings(value: OrgLabelValue | null | undefined): OrgLabelStrings {
  return LABELS[value === "portfolios" ? "portfolios" : "organizations"];
}

/**
 * Hook para consumir el label efectivo del tenant activo. Debe usarse
 * dentro de `<TenantBrandingProvider>` (ver `app/(app)/layout.tsx`).
 */
export function useOrgLabel(): OrgLabelStrings {
  const { branding } = useTenantBranding();
  return orgLabelStrings(branding?.org_label);
}
