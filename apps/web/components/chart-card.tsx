"use client";

/**
 * FASE-3 (revamp v2, US-D) — sacado de `dashboard/page.tsx` para que la
 * fase 8 (Reportes) lo reuse en sus tabs sin duplicar el marcado.
 */
import type { ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";

export function ChartCard({
  title,
  children,
  loading,
}: {
  title: string;
  children: ReactNode;
  loading?: boolean;
}) {
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">{title}</h2>
      {loading ? <Skeleton className="h-[180px] w-full" /> : children}
    </article>
  );
}
