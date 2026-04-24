"use client";

import Link from "next/link";
import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  listOrganizationPanels,
  type OrganizationPanel,
} from "@/lib/api/organizations";

/**
 * US-068 — Landing PMO.
 *
 * Vista informativa de los paneles de las organizaciones del tenant.
 * Click en un panel → `/pmo/organizations/[id]` (programas + proyectos).
 * Es el contraparte "info" del `/admin/organizations` (gestión CRUD).
 */
export default function PmoHome() {
  const [panels, setPanels] = useState<OrganizationPanel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listOrganizationPanels({ is_active: true })
      .then((r) => {
        if (!cancelled) setPanels(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudieron cargar las organizaciones",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          PMO
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Vista informativa del portafolio. Selecciona una organización para
          ver sus programas y proyectos. La gestión (CRUD) vive en{" "}
          <Link href="/admin/organizations" className="text-[var(--color-accent)] hover:underline">
            Admin → Gestión de Organizaciones
          </Link>
          .
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-[var(--radius-xl)]" />
          ))}
        </div>
      ) : panels.length === 0 ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
          No hay organizaciones activas. Pide a un admin que cree una en{" "}
          <Link
            href="/admin/organizations"
            className="text-[var(--color-accent)] hover:underline"
          >
            Admin → Gestión de Organizaciones
          </Link>
          .
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {panels.map((p) => (
            <Link
              key={p.id}
              href={`/pmo/organizations/${p.id}`}
              className="group flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--color-accent)]"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                  {p.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.logo_url} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <Building2 className="h-5 w-5" aria-hidden />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-[var(--color-primary)] group-hover:text-[var(--color-accent)]">
                      {p.name}
                    </span>
                  </div>
                  <div className="truncate text-xs text-[var(--color-tertiary)]">
                    {[p.industry, p.country].filter(Boolean).join(" · ") ||
                      "Sin datos de industria"}
                  </div>
                </div>
              </div>
              <div className="flex gap-3 text-[11px]">
                <Badge variant="neutral">
                  {p.program_count} programas
                </Badge>
                <Badge variant="neutral">
                  {p.active_project_count} proyectos activos
                </Badge>
              </div>
              <div className="flex gap-3 text-[11px] text-[var(--color-tertiary)]">
                <span>🟢 {p.portfolio_health.green}</span>
                <span>🟡 {p.portfolio_health.yellow}</span>
                <span>🔴 {p.portfolio_health.red}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
