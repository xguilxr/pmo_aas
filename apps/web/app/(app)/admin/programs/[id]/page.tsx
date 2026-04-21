"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, FolderKanban, Network, TrendingUp } from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getProgramSummary, type ProgramSummary } from "@/lib/api/organizations";

function Donut({ green, yellow, red }: { green: number; yellow: number; red: number }) {
  const total = green + yellow + red;
  if (total === 0) {
    return (
      <div className="flex h-32 w-32 items-center justify-center rounded-full border-4 border-[var(--border-subtle)] text-xs text-[var(--color-tertiary)]">
        sin datos
      </div>
    );
  }
  const c = 2 * Math.PI * 40;
  const seg = (n: number) => (n / total) * c;
  const gSeg = seg(green);
  const ySeg = seg(yellow);
  const rSeg = seg(red);
  return (
    <svg viewBox="0 0 100 100" className="h-32 w-32 -rotate-90">
      <circle cx="50" cy="50" r="40" fill="none" stroke="var(--border-subtle)" strokeWidth="10" />
      <circle
        cx="50" cy="50" r="40" fill="none" stroke="var(--color-success, #16a34a)"
        strokeWidth="10"
        strokeDasharray={`${gSeg} ${c - gSeg}`}
        strokeDashoffset="0"
      />
      <circle
        cx="50" cy="50" r="40" fill="none" stroke="var(--color-warning, #eab308)"
        strokeWidth="10"
        strokeDasharray={`${ySeg} ${c - ySeg}`}
        strokeDashoffset={`-${gSeg}`}
      />
      <circle
        cx="50" cy="50" r="40" fill="none" stroke="var(--color-danger, #dc2626)"
        strokeWidth="10"
        strokeDasharray={`${rSeg} ${c - rSeg}`}
        strokeDashoffset={`-${gSeg + ySeg}`}
      />
    </svg>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4">
      <div className="text-xs text-[var(--color-tertiary)]">{label}</div>
      <div className="text-2xl font-semibold tabular-nums text-[var(--color-primary)]">
        {value}
      </div>
    </div>
  );
}

function healthBadge(h: string | null) {
  if (!h) return null;
  const variant =
    h === "green" ? "success" : h === "yellow" ? "warning" : "danger";
  return <Badge variant={variant}>{h}</Badge>;
}

function money(n: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(n);
}

export default function ProgramSummaryPage() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<ProgramSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProgramSummary(params.id)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el programa");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error && !data) {
    return (
      <div className="mx-auto max-w-4xl">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center gap-2">
        <BackLink
          fallbackHref={
            data.organization_id
              ? `/admin/organizations/${data.organization_id}`
              : "/admin/organizations"
          }
        />
        <Breadcrumb
          items={[
            { href: "/admin/organizations", label: "Organizaciones" },
            data.organization_name
              ? {
                  href: `/admin/organizations/${data.organization_id}`,
                  label: data.organization_name,
                }
              : { label: "Organización" },
            { label: data.name },
          ]}
        />
      </div>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
            <Network className="h-6 w-6" aria-hidden />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              {data.name}
            </h1>
            <div className="mt-1 flex items-center gap-2 text-xs text-[var(--color-tertiary)]">
              {data.organization_name ?? ""}
              {!data.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
            </div>
            {data.description ? (
              <p className="mt-1 max-w-xl text-sm text-[var(--color-secondary)]">
                {data.description}
              </p>
            ) : null}
          </div>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Proyectos" value={data.project_total} />
        <StatCard label="Activos" value={data.project_active} />
        <StatCard label="En riesgo" value={data.project_at_risk} />
        <StatCard label="Cerrados" value={data.project_closed} />
      </section>

      <section className="grid gap-3 md:grid-cols-[auto_1fr]">
        <div className="flex flex-col items-center gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
          <div className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Salud del portafolio
          </div>
          <Donut {...data.health} />
          <div className="flex gap-3 text-xs">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
              {data.health.green}
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-yellow-500" />
              {data.health.yellow}
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
              {data.health.red}
            </span>
          </div>
        </div>

        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
            <TrendingUp className="h-4 w-4" aria-hidden /> Presupuesto agregado
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-[var(--color-tertiary)]">Plan</dt>
              <dd className="text-xl font-semibold tabular-nums">
                {money(data.budget_planned)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-tertiary)]">Real</dt>
              <dd className="text-xl font-semibold tabular-nums">
                {money(data.budget_actual)}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-xs text-[var(--color-tertiary)]">Desviación</dt>
              <dd className="text-sm tabular-nums">
                {data.budget_planned > 0
                  ? `${(((data.budget_actual - data.budget_planned) / data.budget_planned) * 100).toFixed(1)}%`
                  : "—"}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <AlertTriangle className="h-4 w-4" aria-hidden /> Riesgos top del programa
        </div>
        {data.top_risks.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Sin riesgos críticos (severidad ≥ 13) abiertos.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="py-2">Folio</th>
                <th className="py-2">Riesgo</th>
                <th className="py-2">Proyecto</th>
                <th className="py-2">Estado</th>
                <th className="py-2 text-right">Severidad</th>
              </tr>
            </thead>
            <tbody>
              {data.top_risks.map((r) => (
                <tr key={r.id} className="border-t border-[var(--border-subtle)]">
                  <td className="py-2 font-mono text-xs">{r.folio ?? "—"}</td>
                  <td className="py-2">{r.title}</td>
                  <td className="py-2">
                    <Link
                      href={`/admin/projects/${r.project_id}`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      {r.project_name ?? "—"}
                    </Link>
                  </td>
                  <td className="py-2">{r.status}</td>
                  <td className="py-2 text-right font-semibold tabular-nums">
                    {r.severity}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <FolderKanban className="h-4 w-4" aria-hidden /> Proyectos del programa
        </div>
        {data.projects.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Este programa aún no tiene proyectos.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="py-2">Folio</th>
                <th className="py-2">Nombre</th>
                <th className="py-2">Fase</th>
                <th className="py-2">Salud</th>
                <th className="py-2">PM</th>
                <th className="py-2 text-right">Avance</th>
                <th className="py-2 text-right">Plan / Real</th>
              </tr>
            </thead>
            <tbody>
              {data.projects.map((p) => (
                <tr key={p.id} className="border-t border-[var(--border-subtle)]">
                  <td className="py-2 font-mono text-xs">{p.folio ?? "—"}</td>
                  <td className="py-2">
                    <Link
                      href={`/admin/projects/${p.id}`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      {p.name}
                    </Link>
                  </td>
                  <td className="py-2">{p.phase ?? "—"}</td>
                  <td className="py-2">{healthBadge(p.health_status)}</td>
                  <td className="py-2">{p.pm_name ?? "—"}</td>
                  <td className="py-2 text-right tabular-nums">{p.progress}%</td>
                  <td className="py-2 text-right tabular-nums text-xs">
                    {money(p.budget)} / {money(p.actual_budget)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
