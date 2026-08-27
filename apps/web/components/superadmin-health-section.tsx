"use client";

import { useEffect, useState } from "react";

import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getPlatformHealth,
  type PlatformHealth,
} from "@/lib/api/superadmin-panel";

/**
 * Sección de Health reutilizable (US-026).
 *
 * Muestra un grid de HealthCard con estado API/DB/etc. Refresca cada 15s.
 */
export function SuperadminHealthSection() {
  const [data, setData] = useState<PlatformHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;
    function load() {
      getPlatformHealth()
        .then((r) => {
          if (cancelled) return;
          setData(r);
          setLastRefresh(new Date());
        })
        .catch(() => {
          /* silencioso: el KPI panel arriba ya muestra errores generales */
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }
    load();
    const t = setInterval(load, 15_000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <section className="space-y-3">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icono nombre="heart" size={15} className="text-[var(--text-faint)]" />
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Health de plataforma
          </h2>
        </div>
        {lastRefresh ? (
          <span className="font-mono text-[11px] text-[var(--text-tertiary)]">
            última verificación {lastRefresh.toLocaleTimeString("es-MX")}
          </span>
        ) : null}
      </header>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <HealthCard
          title="API"
          status={loading ? null : data?.api ? "ok" : "down"}
          hint="Latencia promedio dentro del p95"
        />
        <HealthCard
          title="Base de datos"
          status={loading ? null : data?.db ? "ok" : "down"}
          hint="Conexión y consultas base"
        />
        <HealthCard
          title="Worker"
          status="unknown"
          hint="Cola y jobs (instrumentación pendiente)"
        />
        <HealthCard title="Redis" status="unknown" hint="Hit rate y memoria" />
        <HealthCard
          title="IA providers"
          status="unknown"
          hint="Groq / BYO providers — ping por tenant"
        />
        <HealthCard title="Storage" status="unknown" hint="Volume / S3 usage" />
      </div>
    </section>
  );
}

function HealthCard({
  title,
  status,
  hint,
}: {
  title: string;
  status: "ok" | "down" | "unknown" | null;
  hint?: string;
}) {
  if (status === null) {
    return (
      <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="mt-3 h-4 w-40" />
      </article>
    );
  }
  const dot =
    status === "ok"
      ? "bg-[var(--color-success-fg)]"
      : status === "down"
        ? "bg-[var(--color-danger-fg)]"
        : "bg-[var(--color-muted)]";
  const label =
    status === "ok"
      ? "Operativo"
      : status === "down"
        ? "Con problemas"
        : "Sin instrumentar";
  const nombreIcono =
    status === "ok" ? "circle-check" : status === "down" ? "circle-x" : "activity";
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[14px] font-semibold text-[var(--text-primary)]">
            {title}
          </p>
          <p className="mt-0.5 text-[12px] text-[var(--text-tertiary)]">{hint}</p>
        </div>
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full shadow-[var(--hundido)] ${dot}`}
          aria-hidden
        />
      </div>
      <p className="mt-3 inline-flex items-center gap-1.5 text-[13px] text-[var(--text-secondary)]">
        <Icono nombre={nombreIcono} size={15} /> {label}
      </p>
    </article>
  );
}
