"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Building2,
  FolderKanban,
  Network,
  Plus,
  ServerCog,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { listTenants, type Tenant } from "@/lib/api/superadmin";
import { cn } from "@/lib/cn";

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
          : tenants.map((t) => <TenantCard key={t.id} tenant={t} />)}
        {!loading && tenants.length === 0 && !error ? (
          <p className="col-span-full text-center text-sm text-[var(--color-tertiary)]">
            No hay tenants para mostrar.
          </p>
        ) : null}
      </section>
    </div>
  );
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span
      aria-label={active ? "Activo" : "Inactivo"}
      title={active ? "Activo" : "Inactivo"}
      className={cn(
        "inline-block h-2.5 w-2.5 flex-none rounded-full",
        active ? "bg-emerald-500" : "bg-rose-500",
      )}
    />
  );
}

function IconStat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div
      className="flex items-center gap-1.5 rounded-[var(--radius-sm)] bg-[var(--color-subtle)] px-2 py-1"
      title={label}
    >
      <span className="text-[var(--color-tertiary)]">{icon}</span>
      <span className="text-[10px] text-[var(--color-tertiary)]">{label}</span>
      <span className="text-xs font-semibold text-[var(--color-primary)] tabular-nums">
        {value}
      </span>
    </div>
  );
}

function TenantCard({ tenant }: { tenant: Tenant }) {
  return (
    <Link
      href={`/superadmin/tenants/${tenant.id}`}
      className="group rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--border-strong)]"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <ServerCog
            className="h-5 w-5 text-[var(--color-tertiary)]"
            aria-hidden
          />
          <div>
            <h2 className="flex items-center gap-2 text-base font-semibold text-[var(--color-primary)] group-hover:underline">
              {tenant.name}
              <StatusDot active={tenant.is_active} />
            </h2>
            <p className="font-mono text-xs text-[var(--color-tertiary)]">
              {tenant.slug}
            </p>
          </div>
        </div>
        {!tenant.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <IconStat
          icon={<Building2 className="h-3.5 w-3.5" aria-hidden />}
          label="Orgs"
          value={tenant.organization_count}
        />
        <IconStat
          icon={<Users className="h-3.5 w-3.5" aria-hidden />}
          label="Usuarios"
          value={tenant.user_count}
        />
        <IconStat
          icon={<Network className="h-3.5 w-3.5" aria-hidden />}
          label="Programas"
          value={tenant.program_count}
        />
        <IconStat
          icon={<FolderKanban className="h-3.5 w-3.5" aria-hidden />}
          label="Proyectos"
          value={tenant.project_count}
        />
      </div>
    </Link>
  );
}
