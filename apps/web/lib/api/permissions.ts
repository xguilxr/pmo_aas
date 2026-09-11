import { apiFetch } from "@/lib/api";

/**
 * US-060 (DEC-020) — role_type fijo del usuario actual + permisos.
 */
// US-250 (FASE-2, DEC-036): "pm_sr" faltaba en este vocabulario — el backend
// (`schemas/user.py`) ya lo devuelve, pero el tipo se había quedado en 2.
export type RoleType = "admin" | "pm_sr" | "user" | "viewer";

export type MyPermissions = {
  role_type: RoleType;
  is_superadmin: boolean;
  /** Lista plana `module:action`, ej. "projects:create". */
  permissions: string[];
};

export function fetchMyPermissions(): Promise<MyPermissions> {
  return apiFetch<MyPermissions>("/api/v1/auth/me/permissions");
}
