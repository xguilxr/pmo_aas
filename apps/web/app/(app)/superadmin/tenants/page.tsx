"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { listTenants, type Tenant } from "@/lib/api/superadmin";
import { cn } from "@/lib/cn";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";

export default function TenantsListPage() {
  const user = getStoredUser();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(tenants);
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
      <div>
        <Banner variant="danger">Solo los super administradores pueden ver esta página.</Banner>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Tenants
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Administra los clientes multi-tenant de la plataforma.
          </p>
        </div>
        <Link href="/superadmin/tenants/new">
          <Button>
            <Icono nombre="plus" size={15} />
            Provisionar tenant
          </Button>
        </Link>
      </header>

      <div className="flex items-center gap-2 text-sm">
        <Switch
          id="include_inactive"
          checked={includeInactive}
          onChange={(v) => setIncludeInactive(v)}
        />
        <label htmlFor="include_inactive" className="text-[var(--text-secondary)]">
          Incluir inactivos
        </label>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="grid gap-3.5 sm:grid-cols-2">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <article
                key={i}
                className="space-y-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]"
              >
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </article>
            ))
          : tenants.map((t) => <TenantCard key={t.id} tenant={t} />)}
        {!loading && tenants.length === 0 && !error ? (
          <p className="col-span-full text-center text-sm text-[var(--text-tertiary)]">
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
        "inline-block h-2 w-2 flex-none rounded-full",
        active ? "bg-[var(--color-success-fg)]" : "bg-[var(--color-danger-fg)]",
      )}
    />
  );
}

function IconStat({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: number;
}) {
  return (
    <div
      className="flex h-6 items-center gap-1.5 rounded-[var(--radius-sm)] bg-[var(--color-muted)] px-2 text-[var(--text-secondary)]"
      title={label}
    >
      <Icono nombre={icon} size={13} />
      <span className="text-[10.5px]">{label}</span>
      <span className="font-mono text-[11.5px] font-semibold tabular-nums">{value}</span>
    </div>
  );
}

function TenantCard({ tenant }: { tenant: Tenant }) {
  return (
    <Link
      href={`/superadmin/tenants/${tenant.id}`}
      className="group flex flex-col gap-2.5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)] transition-colors hover:border-[var(--border-strong)]"
    >
      <div className="flex items-start justify-between gap-2.5">
        <div className="flex items-center gap-2.5">
          <Icono nombre="server" size={19} className="text-[var(--text-tertiary)]" />
          <div className="flex flex-col">
            <h2 className="flex items-center gap-1.75 text-[15px] font-semibold text-[var(--text-primary)] group-hover:underline">
              {tenant.name}
              <StatusDot active={tenant.is_active} />
            </h2>
            <p className="text-[11.5px] text-[var(--text-tertiary)]">{tenant.slug}</p>
          </div>
        </div>
        {!tenant.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
      </div>
      <div className="flex flex-wrap gap-1.5">
        <IconStat icon="building" label="Orgs" value={tenant.organization_count} />
        <IconStat icon="users" label="Usuarios" value={tenant.user_count} />
        <IconStat icon="git-branch" label="Programas" value={tenant.program_count} />
        <IconStat icon="folder" label="Proyectos" value={tenant.project_count} />
      </div>
    </Link>
  );
}
