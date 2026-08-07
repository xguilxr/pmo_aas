import { ApiError, apiFetch } from "@/lib/api";

export type TenantBranding = {
  tenant_id: string | null;
  tenant_name: string | null;
  tenant_slug: string | null;
  logo_url: string | null;
  primary_color: string | null;
  // ENH-190: per-tenant UI label ("organizations" | "portfolios").
  // UI-only — no schema/route/API change to the underlying entity.
  org_label?: "organizations" | "portfolios" | null;
  // BUG-092: la moneda PREFERIDA del inquilino — el valor inicial de los
  // proyectos que no eligen una propia. La efectiva de un importe la trae el
  // objeto que lo lleva, ya resuelta por la API.
  preferred_currency?: string | null;
};

export function getMyTenantBranding(): Promise<TenantBranding> {
  return apiFetch<TenantBranding>("/api/v1/me/tenant-branding");
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function apiBase(): string {
  if (!API_URL) {
    throw new ApiError(0, "NETWORK_ERROR", "NEXT_PUBLIC_API_URL no está configurada");
  }
  return API_URL.replace(/\/+$/, "");
}

/**
 * Resolve a `logo_url` as returned by the API into a fully-qualified URL
 * that the browser can fetch. Supports two shapes:
 *   - Absolute (`https://…`) — returned verbatim (e.g. CDN logo).
 *   - Relative starting with `/api/v1/…` — prefixed with the API base.
 */
export function resolveLogoUrl(logoUrl: string | null | undefined): string | null {
  if (!logoUrl) return null;
  if (/^https?:\/\//i.test(logoUrl)) return logoUrl;
  if (logoUrl.startsWith("/api/")) return `${apiBase()}${logoUrl}`;
  return logoUrl;
}

export async function uploadTenantLogo(file: File): Promise<{ logo_url: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${apiBase()}/api/v1/admin/tenant/logo`, {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const envelope =
      data && typeof data === "object"
        ? ((data as { detail?: { detail?: string; code?: string } }).detail ?? {})
        : {};
    throw new ApiError(
      res.status,
      envelope.code ?? "UNKNOWN",
      envelope.detail ?? `Error ${res.status}`,
    );
  }
  return data as { logo_url: string };
}

export function deleteTenantLogo(): Promise<{ deleted: boolean; logo_url: string | null }> {
  return apiFetch<{ deleted: boolean; logo_url: string | null }>(
    "/api/v1/admin/tenant/logo",
    { method: "DELETE" },
  );
}
