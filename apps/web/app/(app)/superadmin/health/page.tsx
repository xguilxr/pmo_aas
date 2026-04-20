"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, HeartPulse, XCircle } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getPlatformHealth,
  type PlatformHealth,
} from "@/lib/api/superadmin-panel";

export default function HealthPage() {
  const [data, setData] = useState<PlatformHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    function load() {
      getPlatformHealth()
        .then((r) => {
          setData(r);
          setLastRefresh(new Date());
        })
        .catch((err) => {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el health");
        })
        .finally(() => setLoading(false));
    }
    load();
    const t = setInterval(load, 15_000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex items-start gap-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--text-secondary)]">
          <HeartPulse className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Health
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Estado de la infraestructura. Refresh automático cada 15 segundos.
            {lastRefresh ? (
              <span className="ml-2 font-mono text-[11px]">
                · última verificación {lastRefresh.toLocaleTimeString("es-MX")}
              </span>
            ) : null}
          </p>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
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
        <HealthCard title="Worker" status="unknown" hint="Cola y jobs (instrumentación pendiente)" />
        <HealthCard title="Redis" status="unknown" hint="Hit rate y memoria" />
        <HealthCard
          title="IA providers"
          status="unknown"
          hint="Ollama / Gemini / Claude — ping por tenant"
        />
        <HealthCard title="Storage" status="unknown" hint="Volume / S3 usage" />
      </section>
    </div>
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
      <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
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
    status === "ok" ? "Operativo" : status === "down" ? "Con problemas" : "Sin instrumentar";
  const Icon = status === "ok" ? CheckCircle2 : status === "down" ? XCircle : Activity;
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[14px] font-semibold text-[var(--text-primary)]">{title}</p>
          <p className="mt-0.5 text-[12px] text-[var(--text-tertiary)]">{hint}</p>
        </div>
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full shadow-[inset_0_-1px_2px_oklch(0%_0_0/0.12)] ${dot}`}
          aria-hidden
        />
      </div>
      <p className="mt-3 inline-flex items-center gap-1.5 text-[13px] text-[var(--text-secondary)]">
        <Icon className="h-4 w-4" aria-hidden /> {label}
      </p>
    </article>
  );
}
