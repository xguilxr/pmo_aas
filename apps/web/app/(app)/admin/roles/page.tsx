"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Plus, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { listRoles, type AdminRole } from "@/lib/api/admin";

export default function RolesListPage() {
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listRoles()
      .then((r) => {
        if (!cancelled) setRoles(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudieron cargar los roles");
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
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Roles y permisos</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Define qué puede hacer cada perfil. Los roles del sistema no se pueden borrar.
          </p>
        </div>
        <Link href="/admin/roles/new">
          <Button>
            <Plus className="h-4 w-4" aria-hidden />
            Nuevo rol
          </Button>
        </Link>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="grid gap-3 sm:grid-cols-2">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <article
                key={i}
                className="space-y-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]"
              >
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </article>
            ))
          : roles.map((r) => {
              const moduleCount = Object.keys(r.permissions).length;
              return (
                <Link
                  key={r.id}
                  href={`/admin/roles/${r.id}`}
                  className="group rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--border-strong)]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h2 className="text-base font-semibold text-[var(--color-primary)] group-hover:underline">
                        {r.name}
                      </h2>
                      {r.description ? (
                        <p className="mt-1 text-sm text-[var(--color-tertiary)]">{r.description}</p>
                      ) : null}
                    </div>
                    {r.is_system ? (
                      <Badge variant="info" title="Rol del sistema">
                        <ShieldCheck className="h-3 w-3" aria-hidden />
                        Sistema
                      </Badge>
                    ) : null}
                  </div>
                  <div className="mt-3 text-xs text-[var(--color-secondary)]">
                    {moduleCount} módulo{moduleCount === 1 ? "" : "s"} con permisos asignados
                  </div>
                </Link>
              );
            })}
        {!loading && roles.length === 0 && !error ? (
          <p className="col-span-full text-center text-sm text-[var(--color-tertiary)]">
            Aún no hay roles. Crea el primero.
          </p>
        ) : null}
      </section>
    </div>
  );
}
