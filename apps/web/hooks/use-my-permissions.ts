"use client";

import { useEffect, useState } from "react";

import { fetchMyPermissions, type MyPermissions } from "@/lib/api/permissions";

/**
 * US-060 — hook global que carga `GET /auth/me/permissions` y cachea
 * el resultado en memory del módulo. Se refresca al iniciar cada
 * session (login) y al evento `pmoaas:user-updated`.
 *
 * Uso:
 * ```tsx
 * const { canCreate } = useMyPermissions();
 * {canCreate("projects") && <Button>Nuevo proyecto</Button>}
 * ```
 */

let cached: MyPermissions | null = null;
const pending: Set<(v: MyPermissions | null) => void> = new Set();

async function ensureLoaded(): Promise<MyPermissions | null> {
  if (cached) return cached;
  try {
    const p = await fetchMyPermissions();
    cached = p;
    pending.forEach((fn) => fn(p));
    pending.clear();
    return p;
  } catch {
    return null;
  }
}

export function invalidateMyPermissions(): void {
  cached = null;
}

export type UseMyPermissions = {
  data: MyPermissions | null;
  loading: boolean;
  isSuperadmin: boolean;
  roleType: "admin" | "user" | "viewer" | null;
  has: (moduleAction: string) => boolean;
  canCreate: (module: string) => boolean;
  canUpdate: (module: string) => boolean;
  canDelete: (module: string) => boolean;
};

export function useMyPermissions(): UseMyPermissions {
  const [data, setData] = useState<MyPermissions | null>(cached);
  const [loading, setLoading] = useState(cached === null);

  useEffect(() => {
    let cancelled = false;
    if (!cached) {
      setLoading(true);
      ensureLoaded().then((p) => {
        if (!cancelled) {
          setData(p);
          setLoading(false);
        }
      });
    }
    const onUserUpdated = () => {
      invalidateMyPermissions();
      ensureLoaded().then((p) => {
        if (!cancelled) setData(p);
      });
    };
    window.addEventListener("pmoaas:user-updated", onUserUpdated);
    return () => {
      cancelled = true;
      window.removeEventListener("pmoaas:user-updated", onUserUpdated);
    };
  }, []);

  const has = (moduleAction: string): boolean => {
    if (!data) return false;
    if (data.is_superadmin) return true;
    return data.permissions.includes(moduleAction);
  };

  return {
    data,
    loading,
    isSuperadmin: data?.is_superadmin ?? false,
    roleType: data?.role_type ?? null,
    has,
    canCreate: (m) => has(`${m}:create`),
    canUpdate: (m) => has(`${m}:update`),
    canDelete: (m) => has(`${m}:delete`),
  };
}
