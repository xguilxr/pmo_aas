"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SuperadminHealthSection } from "@/components/superadmin-health-section";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiBand, KpiCard } from "@/components/kpi-card";
import { ApiError } from "@/lib/api";
import {
  getPlatformDashboard,
  type PlatformDashboard,
} from "@/lib/api/superadmin-panel";
import { getStoredUser } from "@/lib/auth-storage";
import { SIN_DATO } from "@/lib/sin-dato";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";

function formatNumber(n: number): string {
  return new Intl.NumberFormat("es-MX").format(n);
}

/** Botón secundario del toolbar de cabecera — mismas clases que
 *  `Button variant="secondary"` (components/ui/button.tsx) pero sobre un
 *  `<Link>`, porque son rutas y no acciones. */
const TOOLBAR_LINK =
  "inline-flex h-8 items-center gap-1.75 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-[12.5px] font-medium text-[var(--text-secondary)] shadow-[var(--relieve-control)] hover:bg-[var(--color-subtle)]";

export default function SuperadminHomePage() {
  const user = getStoredUser();
  const [data, setData] = useState<PlatformDashboard | null>(null);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(data);
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
      <div>
        <Banner variant="danger">Solo Super Admin puede acceder a este panel.</Banner>
      </div>
    );
  }

  const kpis = data?.kpis;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Super Admin · Visión general
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Estado de la plataforma completa. Auto-refresh cada 60 segundos.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/superadmin/tenants" className={TOOLBAR_LINK}>
            Tenants
          </Link>
          <Link href="/superadmin/logs" className={TOOLBAR_LINK}>
            Logs
          </Link>
          <Link href="/superadmin/me" className={TOOLBAR_LINK}>
            Mi cuenta
          </Link>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <SuperadminHealthSection />

      <KpiBand className="grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
        <KpiCard
          label="Tenants"
          value={kpis?.tenants_total}
          hint={kpis ? `${kpis.tenants_active} activos` : undefined}
          icon={<Icono nombre="folder" size={13} />}
          loading={loading}
        />
        <KpiCard
          label="Usuarios"
          value={kpis?.users_total}
          icon={<Icono nombre="users" size={13} />}
          loading={loading}
        />
        <KpiCard
          label="Proyectos"
          value={kpis?.projects_total}
          icon={<Icono nombre="folder" size={13} />}
          loading={loading}
        />
        <KpiCard
          label="Tokens IA (30d)"
          value={kpis ? kpis.ai_tokens_30d.in + kpis.ai_tokens_30d.out : undefined}
          hint={
            kpis
              ? `${formatNumber(kpis.ai_tokens_30d.in)} in · ${formatNumber(kpis.ai_tokens_30d.out)} out`
              : undefined
          }
          icon={<Icono nombre="info" size={13} />}
          loading={loading}
          tone="accent"
        />
        {/* MRR y Uptime 30d: sin endpoint hoy (ver nota de la pantalla) — se
            marcan con SIN_DATO y la leyenda «pendiente de backend», nunca con
            una cifra inventada. */}
        <PendingKpi label="MRR" icon="trending-up" />
        <PendingKpi label="Uptime 30d" icon="circle-check" />
      </KpiBand>

      <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
          <header className="flex h-10 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
            <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
              Actividad reciente
            </h2>
            <Icono nombre="clock" size={15} className="text-[var(--text-faint)]" />
          </header>
          <ul className="flex flex-col divide-y divide-[var(--border-subtle)] text-[13px]">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <li key={i} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </li>
                ))
              : data?.activity_recent.map((a) => (
                  <li key={a.id} className="flex h-10 items-center gap-2.5 px-4">
                    <Badge>{a.action}</Badge>
                    <span className="text-[12px] text-[var(--text-secondary)]">
                      {a.module ?? "—"}
                    </span>
                    <span className="ml-auto text-[11px] text-[var(--text-faint)]">
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

        <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
          <header className="flex h-10 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
            <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
              Top tenants
            </h2>
            <Icono nombre="server" size={15} className="text-[var(--text-faint)]" />
          </header>
          <ul className="flex flex-col divide-y divide-[var(--border-subtle)]">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <li key={i} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </li>
                ))
              : data?.top_tenants.map((t) => (
                  <li key={t.id} className="flex h-11 items-center justify-between gap-2 px-4">
                    <div className="min-w-0">
                      <Link
                        href={`/superadmin/tenants/${t.id}`}
                        className="block overflow-hidden text-ellipsis whitespace-nowrap text-[13px] font-medium text-[var(--text-primary)] hover:underline"
                      >
                        {t.name}
                      </Link>
                      <p className="text-[11px] text-[var(--text-tertiary)]">{t.slug}</p>
                    </div>
                    <span className="inline-flex h-5 shrink-0 items-center rounded-full bg-[var(--color-muted)] px-2 font-mono text-[11px] text-[var(--text-secondary)]">
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

      {/* US: historial de incidentes — sin tabla propia hoy, se documenta el
          hueco en vez de inventar filas (ver nota de la pantalla). */}
      <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <header className="flex h-10 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Incidentes recientes
          </h2>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled
            title="Pendiente de backend: todavía no hay tabla de incidentes"
          >
            Declarar incidente
          </Button>
        </header>
        <p className="px-4 py-3 text-[11px] italic text-[var(--text-faint)]">
          Pendiente de backend — hoy se infiere de logs, no hay tabla de incidentes.
        </p>
      </article>
    </div>
  );
}

/** KPI sin endpoint real: SIN_DATO + leyenda, nunca una cifra inventada. */
function PendingKpi({ label, icon }: { label: string; icon: string }) {
  return (
    <div className="flex h-full flex-col gap-2 p-4">
      <div className="flex items-center justify-between">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
          {label}
        </span>
        <span className="text-[var(--text-tertiary)]">
          <Icono nombre={icon} size={13} />
        </span>
      </div>
      <span className="font-mono text-[26px] font-medium tabular-nums text-[var(--text-faint)]">
        {SIN_DATO}
      </span>
      <span className="text-[11.5px] italic text-[var(--text-faint)]">pendiente de backend</span>
    </div>
  );
}
