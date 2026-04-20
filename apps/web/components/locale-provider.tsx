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

import { ApiError } from "@/lib/api";
import { hasSession } from "@/lib/auth-storage";
import { getMyPreferences, updateMyPreferences } from "@/lib/api/users";

const STORAGE_KEY = "pmoaas.locale";
export const SUPPORTED_LOCALES = ["es-MX", "en-US"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];
const DEFAULT_LOCALE: Locale = "es-MX";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (l: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue>({
  locale: DEFAULT_LOCALE,
  setLocale: () => undefined,
});

function coerce(v: string | null | undefined): Locale {
  return SUPPORTED_LOCALES.includes(v as Locale) ? (v as Locale) : DEFAULT_LOCALE;
}

function readStoredLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  return coerce(window.localStorage.getItem(STORAGE_KEY));
}

function applyLocaleAttr(locale: Locale): void {
  if (typeof document !== "undefined") {
    document.documentElement.lang = locale;
  }
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    const l = readStoredLocale();
    setLocaleState(l);
    applyLocaleAttr(l);
  }, []);

  // sync con backend al montar si hay sesión
  useEffect(() => {
    if (!hasSession()) return;
    let cancelled = false;
    getMyPreferences()
      .then((prefs) => {
        if (cancelled || !prefs.locale) return;
        const l = coerce(prefs.locale);
        if (l !== readStoredLocale()) {
          window.localStorage.setItem(STORAGE_KEY, l);
          setLocaleState(l);
          applyLocaleAttr(l);
        }
      })
      .catch(() => {
        /* ignorar */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    applyLocaleAttr(l);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, l);
    }
    if (hasSession()) {
      updateMyPreferences({ locale: l }).catch((err) => {
        if (err instanceof ApiError) {
          // eslint-disable-next-line no-console
          console.warn("No se pudo guardar idioma:", err.message);
        }
      });
    }
  }, []);

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  return useContext(LocaleContext);
}
