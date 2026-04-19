"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Plus, ServerCog } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { listTenants, type Tenant } from "@/lib/api/superadmin";

export default function TenantsListPage() {
  const user = getStoredUser();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenants(includeInactive)
      .then((r) => {
        if (!cancelled) setTenants(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudieron cargar los tenants");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [includeInactive]);

  if (user && !user.is_superadmin) {
    return (
      <div className="mx-auto max-w-2xl">
        <Banner variant="danger">Solo los super administradores pueden ver esta página.</Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Tenants</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Administra los clientes multi-tenant de la plataforma.
          </p>
        </div>
        <Link href="/superadmin/tenants/new">
          <Button>
            <Plus className="h-4 w-4" aria-hidden />
            Provisionar tenant
          </Button>
        </Link>
      </header>

      <div className="flex items-center gap-3 text-sm">
        <Switch
          id="include_inactive"
          checked={includeInactive}
          onChange={(v) => setIncludeInactive(v)}
        />
        <label htmlFor="include_inactive" className="text-[var(--color-secondary)]">
          Incluir inactivos
        </label>
      </div>

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
          : tenants.map((t) => (
              <Link
                key={t.id}
                href={`/superadmin/tenants/${t.id}`}
                className="group rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--border-strong)]"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ServerCog className="h-5 w-5 text-[var(--color-tertiary)]" aria-hidden />
                    <div>
                      <h2 className="text-base font-semibold text-[var(--color-primary)] group-hover:underline">
                        {t.name}
                      </h2>
                      <p className="text-xs text-[var(--color-tertiary)]">{t.slug}</p>
                    </div>
                  </div>
                  {!t.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
                </div>
                <dl className="mt-3 flex gap-4 text-xs text-[var(--color-secondary)]">
                  <div>
                    <dt className="text-[var(--color-tertiary)]">Usuarios</dt>
                    <dd className="font-medium text-[var(--color-primary)]">{t.user_count}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--color-tertiary)]">Proyectos</dt>
                    <dd className="font-medium text-[var(--color-primary)]">{t.project_count}</dd>
                  </div>
                </dl>
              </Link>
            ))}
        {!loading && tenants.length === 0 && !error ? (
          <p className="col-span-full text-center text-sm text-[var(--color-tertiary)]">
            No hay tenants para mostrar.
          </p>
        ) : null}
      </section>
    </div>
  );
}
