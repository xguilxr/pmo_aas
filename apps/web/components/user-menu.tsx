"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  LogOut,
  Monitor,
  Moon,
  Sun,
  UserCircle,
} from "lucide-react";

import { useLocale, type Locale } from "@/components/locale-provider";
import { useTheme } from "@/components/theme-provider";
import { logout } from "@/lib/auth";
import { type StoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

type Props = {
  user: StoredUser | null;
  variant?: "chrome" | "surface";
};

function initials(user: StoredUser | null): string {
  const source = user?.full_name || user?.username || user?.email || "U";
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join("");
}

export function UserMenu({ user, variant = "chrome" }: Props) {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { locale, setLocale } = useLocale();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  async function handleLogout() {
    setSigningOut(true);
    try {
      await logout();
      router.replace("/login");
    } finally {
      setSigningOut(false);
      setOpen(false);
    }
  }

  const triggerColors =
    variant === "chrome"
      ? "text-[var(--chrome-text)] hover:bg-[var(--chrome-hover)] border-transparent"
      : "bg-[var(--color-surface)] text-[var(--text-primary)] hover:bg-[var(--color-subtle)] border-[var(--border-default)]";

  const avatarBg =
    variant === "chrome"
      ? "bg-[var(--chrome-text)] text-[var(--chrome-bg)]"
      : "bg-[var(--text-primary)] text-[var(--color-inverse)]";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          "inline-flex h-9 items-center gap-2 rounded-[var(--radius-md)] border px-1.5 pr-2 text-[12px] font-medium transition-colors",
          triggerColors,
        )}
      >
        <span
          aria-hidden
          className={cn(
            "inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[11px] font-bold",
            avatarBg,
          )}
        >
          {initials(user)}
        </span>
        <span className="hidden max-w-[120px] truncate sm:inline">
          {user?.full_name || user?.username || "Sesión"}
        </span>
        <ChevronDown className="h-3.5 w-3.5 opacity-70" aria-hidden />
      </button>

      {open ? (
        <div
          role="menu"
          className="motion-enter absolute right-0 top-[calc(100%+6px)] z-50 w-64 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] shadow-[var(--shadow-optical-md)]"
        >
          <div className="border-b border-[var(--border-subtle)] px-4 py-3">
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden
                className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--text-primary)] text-[13px] font-bold text-[var(--color-inverse)]"
              >
                {initials(user)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-[13px] font-semibold text-[var(--text-primary)]">
                  {user?.full_name || user?.username || "—"}
                </p>
                <p className="truncate text-[11px] text-[var(--text-tertiary)]">
                  {user?.email ?? ""}
                </p>
              </div>
            </div>
            {user?.is_superadmin ? (
              <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-[var(--color-info-bg)] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-info-fg)]">
                Super admin
              </p>
            ) : user?.roles?.length ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {user.roles.slice(0, 3).map((r) => (
                  <span
                    key={r}
                    className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]"
                  >
                    {r}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
          <div className="border-b border-[var(--border-subtle)] px-3 py-2">
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
              Idioma
            </div>
            <div
              role="radiogroup"
              aria-label="Idioma de la interfaz"
              className="grid grid-cols-2 gap-1 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-0.5"
            >
              {(
                [
                  { v: "es-MX", flag: "🇲🇽", label: "Español" },
                  { v: "en-US", flag: "🇺🇸", label: "English" },
                ] as const
              ).map((opt) => {
                const active = locale === (opt.v as Locale);
                return (
                  <button
                    key={opt.v}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setLocale(opt.v as Locale)}
                    className={cn(
                      "inline-flex items-center justify-center gap-1 rounded-[var(--radius-sm)] px-2 py-1.5 text-[11px] font-medium transition-colors",
                      active
                        ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
                    )}
                    title={opt.label}
                  >
                    <span aria-hidden>{opt.flag}</span>
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="border-b border-[var(--border-subtle)] px-3 py-2">
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
              Tema
            </div>
            <div
              role="radiogroup"
              aria-label="Tema de la interfaz"
              className="grid grid-cols-3 gap-1 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-0.5"
            >
              {(
                [
                  { v: "light", icon: Sun, label: "Claro" },
                  { v: "dark", icon: Moon, label: "Oscuro" },
                  { v: "system", icon: Monitor, label: "Sistema" },
                ] as const
              ).map((opt) => {
                const Icon = opt.icon;
                const active = theme === opt.v;
                return (
                  <button
                    key={opt.v}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setTheme(opt.v)}
                    className={cn(
                      "inline-flex items-center justify-center gap-1 rounded-[var(--radius-sm)] px-2 py-1.5 text-[11px] font-medium transition-colors",
                      active
                        ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
                    )}
                    title={opt.label}
                  >
                    <Icon className="h-3 w-3" aria-hidden />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="p-1">
            <Link
              href="/account"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex w-full items-center gap-2 rounded-[var(--radius-sm)] px-3 py-2 text-left text-[13px] text-[var(--text-primary)] hover:bg-[var(--color-subtle)]"
            >
              <UserCircle className="h-3.5 w-3.5" aria-hidden />
              Administrar cuenta
            </Link>
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              disabled={signingOut}
              className="flex w-full items-center gap-2 rounded-[var(--radius-sm)] px-3 py-2 text-left text-[13px] text-[var(--text-primary)] hover:bg-[var(--color-subtle)] disabled:opacity-60"
            >
              {signingOut ? (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
              ) : (
                <LogOut className="h-3.5 w-3.5" aria-hidden />
              )}
              Cerrar sesión
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
