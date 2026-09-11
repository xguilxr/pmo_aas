"use client";

/**
 * FASE-7 (revamp v2, US-E) — Idioma y tema, extraídos de `user-menu.tsx`
 * para que el menú del avatar y `/account` compartan el mismo componente.
 * Nada se pierde del menú: solo se comparte.
 */
import { useLocale, type Locale } from "@/components/locale-provider";
import { useTheme } from "@/components/theme-provider";
import { Icono } from "@/components/ui/icono";
import { cn } from "@/lib/cn";

export function PreferenciasDeInterfaz({
  variant = "menu",
}: {
  /** "menu": compacto, dentro del dropdown. "page": con títulos de sección, para /account. */
  variant?: "menu" | "page";
}) {
  const { theme, setTheme } = useTheme();
  const { locale, setLocale } = useLocale();

  return (
    <div className={variant === "page" ? "space-y-4" : "space-y-0"}>
      <div className={variant === "page" ? "" : "border-b border-[var(--border-subtle)] px-3 py-2"}>
        <div
          className={
            variant === "page"
              ? "mb-1.5 text-[12.5px] font-medium text-[var(--text-secondary)]"
              : "mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]"
          }
        >
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
      <div className={variant === "page" ? "" : "border-b border-[var(--border-subtle)] px-3 py-2"}>
        <div
          className={
            variant === "page"
              ? "mb-1.5 text-[12.5px] font-medium text-[var(--text-secondary)]"
              : "mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]"
          }
        >
          Tema
        </div>
        <div
          role="radiogroup"
          aria-label="Tema de la interfaz"
          className="grid grid-cols-3 gap-1 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-0.5"
        >
          {(
            [
              { v: "light", icono: "sun", label: "Claro" },
              { v: "dark", icono: "moon", label: "Oscuro" },
              { v: "system", icono: "monitor", label: "Sistema" },
            ] as const
          ).map((opt) => {
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
                <Icono nombre={opt.icono} size={13} />
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
