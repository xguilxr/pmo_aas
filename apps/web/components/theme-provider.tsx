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
import {
  getMyPreferences,
  updateMyPreferences,
  type Theme,
} from "@/lib/api/users";

const STORAGE_KEY = "pmoaas.theme";

type ThemeContextValue = {
  theme: Theme;
  resolved: "dark" | "light";
  setTheme: (t: Theme) => void;
};

const ThemeContext = createContext<ThemeContextValue>({
  theme: "system",
  resolved: "light",
  setTheme: () => undefined,
});

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const v = window.localStorage.getItem(STORAGE_KEY);
  if (v === "dark" || v === "light" || v === "system") return v;
  return "system";
}

function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(theme: Theme): "dark" | "light" {
  const resolved: "dark" | "light" =
    theme === "system" ? (systemPrefersDark() ? "dark" : "light") : theme;
  if (typeof document !== "undefined") {
    const root = document.documentElement;
    if (resolved === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
    root.dataset.theme = resolved;
  }
  return resolved;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolved, setResolved] = useState<"dark" | "light">("light");

  // Hidratar desde localStorage y aplicar de inmediato
  useEffect(() => {
    const t = readStoredTheme();
    setThemeState(t);
    setResolved(applyTheme(t));
  }, []);

  // Reaccionar a cambios del system si el usuario eligió "system"
  useEffect(() => {
    if (theme !== "system" || typeof window === "undefined") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setResolved(applyTheme("system"));
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [theme]);

  // Sincronizar con el backend (si hay sesión)
  useEffect(() => {
    if (!hasSession()) return;
    let cancelled = false;
    getMyPreferences()
      .then((prefs) => {
        if (cancelled) return;
        if (prefs.theme !== readStoredTheme()) {
          window.localStorage.setItem(STORAGE_KEY, prefs.theme);
          setThemeState(prefs.theme);
          setResolved(applyTheme(prefs.theme));
        }
      })
      .catch(() => {
        /* silencioso: si 401, no forzamos nada */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    setResolved(applyTheme(t));
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, t);
    }
    if (hasSession()) {
      updateMyPreferences({ theme: t }).catch((err) => {
        if (err instanceof ApiError) {
          // eslint-disable-next-line no-console
          console.warn("No se pudo guardar tema en backend:", err.message);
        }
      });
    }
  }, []);

  const value = useMemo(
    () => ({ theme, resolved, setTheme }),
    [theme, resolved, setTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
