"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { hasSession } from "@/lib/auth-storage";
import { getMyTenantBranding, type TenantBranding } from "@/lib/api/branding";

const STORAGE_KEY = "pmoaas.branding";

type BrandingContextValue = {
  branding: TenantBranding | null;
  refresh: () => Promise<void>;
};

const BrandingContext = createContext<BrandingContextValue>({
  branding: null,
  refresh: async () => undefined,
});

function readCached(): TenantBranding | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TenantBranding;
  } catch {
    return null;
  }
}

function writeCached(b: TenantBranding | null): void {
  if (typeof window === "undefined") return;
  if (b) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(b));
  else window.localStorage.removeItem(STORAGE_KEY);
}

export function TenantBrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<TenantBranding | null>(() => readCached());

  const refresh = useCallback(async () => {
    if (!hasSession()) {
      setBranding(null);
      writeCached(null);
      return;
    }
    try {
      const b = await getMyTenantBranding();
      setBranding(b);
      writeCached(b);
    } catch {
      /* silencioso: el fallback de texto cubre el caso */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(() => ({ branding, refresh }), [branding, refresh]);

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
}

export function useTenantBranding(): BrandingContextValue {
  return useContext(BrandingContext);
}
