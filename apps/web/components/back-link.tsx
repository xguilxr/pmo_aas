"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  /** Fallback href usado si no hay historial disponible (p. ej. deep-link). */
  fallbackHref: string;
  /** Label accesible; por default "Volver". */
  label?: string;
};

/**
 * Botón "Volver" reutilizable (ENH-001).
 *
 * Prefiere `router.back()` cuando hay historial de misma sesión; si no,
 * navega al `fallbackHref`. Esto cubre los dos casos comunes:
 * (1) entraste desde un listado → volver te regresa al listado;
 * (2) llegaste por deep-link / hard-refresh → volver te lleva al padre
 *     lógico en vez de quedarte atorado.
 *
 * Detectamos ausencia de historial con `window.history.length <= 1`
 * (no perfecto pero robusto para la mayoría de casos).
 */
export function BackLink({ fallbackHref, label = "Volver" }: Props) {
  const router = useRouter();

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={() => {
        if (typeof window !== "undefined" && window.history.length > 1) {
          router.back();
          return;
        }
        router.push(fallbackHref);
      }}
      aria-label={label}
    >
      <ArrowLeft className="h-4 w-4" aria-hidden />
      {label}
    </Button>
  );
}

/**
 * Variante <Link>-only (sin `router.back`) cuando el destino es estable y
 * preferimos que "volver" funcione igual aunque la nav tab sea nueva.
 */
export function BackLinkStatic({ href, label = "Volver" }: { href: string; label?: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
      aria-label={label}
    >
      <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
      {label}
    </Link>
  );
}
