import { apiFetch } from "@/lib/api";

/**
 * US-060 (DEC-020) — role_type fijo del usuario actual + permisos.
 */
export type RoleType = "admin" | "user" | "viewer";

export type MyPermissions = {
  role_type: RoleType;
  is_superadmin: boolean;
  /** Lista plana `module:action`, ej. "projects:create". */
  permissions: string[];
};

export function fetchMyPermissions(): Promise<MyPermissions> {
  return apiFetch<MyPermissions>("/api/v1/auth/me/permissions");
}
