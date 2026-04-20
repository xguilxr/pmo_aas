"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  Briefcase,
  FolderKanban,
  Server,
  Sparkles,
  Users as UsersIcon,
} from "lucide-react";

import { SuperadminHealthSection } from "@/components/superadmin-health-section";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getPlatformDashboard,
  type PlatformDashboard,
} from "@/lib/api/superadmin-panel";
import { getStoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

function formatNumber(n: number): string {
  return new Intl.NumberFormat("es-MX").format(n);
}

export default function SuperadminHomePage() {
  const user = getStoredUser();
  const [data, setData] = useState<PlatformDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function load() {
      getPlatformDashboard()
        .then(setData)
        .catch((err) => {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el panel");
        })
        .finally(() => setLoading(false));
    }
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, []);

  if (user && !user.is_superadmin) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">Solo Super Admin puede acceder a este panel.</Banner>
      </div>
    );
  }

  const kpis = data?.kpis;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Super Admin · Visión general
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Estado de la plataforma completa. Auto-refresh cada 60 segundos.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[12px]">
          <Link
            href="/superadmin/tenants"
            className="inline-flex h-9 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 font-medium text-[var(--text-primary)] hover:bg-[var(--color-subtle)]"
          >
            Tenants
          </Link>
          <Link
            href="/superadmin/logs"
            className="inline-flex h-9 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 font-medium text-[var(--text-primary)] hover:bg-[var(--color-subtle)]"
          >
            Logs
          </Link>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <SuperadminHealthSection />

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi
          label="Tenants"
          value={kpis ? formatNumber(kpis.tenants_total) : "—"}
          sub={kpis ? `${kpis.tenants_active} activos` : undefined}
          icon={<FolderKanban className="h-4 w-4" aria-hidden />}
          loading={loading}
        />
        <Kpi
          label="Usuarios"
          value={kpis ? formatNumber(kpis.users_total) : "—"}
          icon={<UsersIcon className="h-4 w-4" aria-hidden />}
          loading={loading}
        />
        <Kpi
          label="Proyectos"
          value={kpis ? formatNumber(kpis.projects_total) : "—"}
          icon={<Briefcase className="h-4 w-4" aria-hidden />}
          loading={loading}
        />
        <Kpi
          label="Tokens IA (30d)"
          value={
            kpis
              ? `${formatNumber(kpis.ai_tokens_30d.in + kpis.ai_tokens_30d.out)}`
              : "—"
          }
          sub={
            kpis
              ? `${formatNumber(kpis.ai_tokens_30d.in)} in · ${formatNumber(kpis.ai_tokens_30d.out)} out`
              : undefined
          }
          icon={<Sparkles className="h-4 w-4" aria-hidden />}
          loading={loading}
          tone="accent"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <article className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
          <header className="flex items-center justify-between border-b border-[var(--border-subtle)] p-4">
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Actividad reciente
            </h2>
            <Activity className="h-4 w-4 text-[var(--text-tertiary)]" aria-hidden />
          </header>
          <ul className="divide-y divide-[var(--border-subtle)] text-[13px]">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <li key={i} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </li>
                ))
              : data?.activity_recent.map((a) => (
                  <li key={a.id} className="flex items-center gap-3 px-4 py-2.5">
                    <Badge>{a.action}</Badge>
                    <span className="text-[12px] text-[var(--text-secondary)]">
                      {a.module ?? "—"}
                    </span>
                    <span className="ml-auto font-mono text-[11px] text-[var(--text-tertiary)]">
                      {a.occurred_at
                        ? new Date(a.occurred_at).toLocaleString("es-MX")
                        : "—"}
                    </span>
                  </li>
                ))}
            {!loading && !data?.activity_recent.length ? (
              <li className="px-4 py-8 text-center text-[var(--text-tertiary)]">
                Sin actividad registrada.
              </li>
            ) : null}
          </ul>
        </article>

        <article className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
          <header className="flex items-center justify-between border-b border-[var(--border-subtle)] p-4">
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Top tenants
            </h2>
            <Server className="h-4 w-4 text-[var(--text-tertiary)]" aria-hidden />
          </header>
          <ul className="divide-y divide-[var(--border-subtle)]">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <li key={i} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </li>
                ))
              : data?.top_tenants.map((t) => (
                  <li key={t.id} className="flex items-center justify-between gap-2 px-4 py-3">
                    <div className="min-w-0">
                      <Link
                        href={`/superadmin/tenants/${t.id}`}
                        className="truncate font-medium text-[var(--text-primary)] hover:underline"
                      >
                        {t.name}
                      </Link>
                      <p className="font-mono text-[11px] text-[var(--text-tertiary)]">
                        {t.slug}
                      </p>
                    </div>
                    <span className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-[11px] tabular-nums text-[var(--text-secondary)]">
                      {t.project_count} proy
                    </span>
                  </li>
                ))}
            {!loading && !data?.top_tenants.length ? (
              <li className="px-4 py-8 text-center text-[13px] text-[var(--text-tertiary)]">
                No hay tenants aún.
              </li>
            ) : null}
          </ul>
        </article>
      </section>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
  icon,
  loading,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  tone?: "accent";
}) {
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
          {label}
        </span>
        {icon ? <span className="text-[var(--text-tertiary)]">{icon}</span> : null}
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-24" />
      ) : (
        <p
          className={cn(
            "mt-1 text-[24px] font-semibold tabular-nums tracking-tight",
            tone === "accent" ? "text-[var(--color-accent)]" : "text-[var(--text-primary)]",
          )}
        >
          {value}
        </p>
      )}
      {sub && !loading ? (
        <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">{sub}</p>
      ) : null}
    </article>
  );
}
