"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { FileText, LayoutGrid, Sparkles } from "lucide-react";

import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";
import { listTenantReports, type TenantReport } from "@/lib/api/tenant-cross";
import { getStoredUser } from "@/lib/auth-storage";

type TenantReportsTab = "operational" | "builder";

const ADMIN_ROLES = new Set(["admin", "Administrador", "PMO Manager", "pmo"]);

function userIsAdmin(): boolean {
  const u = getStoredUser();
  if (!u) return false;
  if (u.is_superadmin) return true;
  const roles = (u.roles ?? []) as string[];
  return roles.some((r) => ADMIN_ROLES.has(r));
}

export default function TenantReportsPage() {
  const search = useSearchParams();
  const activeTab: TenantReportsTab =
    search?.get("tab") === "builder" ? "builder" : "operational";
  const isAdmin = useMemo(() => userIsAdmin(), []);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Reportes · Tenant
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Reportes operacionales y plantillas del Report Builder accesibles
          en el tenant.
        </p>
      </header>

      {/* US-139: tabs Operacionales / Report Builder */}
      <div
        role="tablist"
        aria-label="Vistas de reportes del tenant"
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
      >
        {(
          [
            { v: "operational" as const, label: "Operacionales", icon: <FileText className="h-3.5 w-3.5" aria-hidden /> },
            { v: "builder" as const, label: "Report Builder", icon: <LayoutGrid className="h-3.5 w-3.5" aria-hidden /> },
          ]
        ).map((opt) => {
          const active = activeTab === opt.v;
          const href = opt.v === "operational" ? "/pmo/reports" : "/pmo/reports?tab=builder";
          return (
            <Link
              key={opt.v}
              href={href}
              role="tab"
              aria-selected={active}
              className={`inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] px-4 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]"
              }`}
            >
              {opt.icon}
              {opt.label}
            </Link>
          );
        })}
      </div>

      {activeTab === "builder" ? (
        <BuilderTemplatesView isAdmin={isAdmin} />
      ) : (
        <OperationalReportsView />
      )}
    </div>
  );
}

function OperationalReportsView() {
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  const [rows, setRows] = useState<TenantReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenantReports(filter)
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <>
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <TenantCrossFilters value={filter} onChange={setFilter} />
      </section>

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin reportes para los filtros actuales.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <th className="px-3 py-2 font-medium">Folio</th>
                <th className="px-3 py-2 font-medium">Título</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium">Período</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2 font-medium">Proyecto</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
                  <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
                    {r.folio}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/pmo/projects/${r.project_id}/reports`}
                      className="text-[var(--color-primary)] hover:underline"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.report_type ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.period ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-[var(--color-secondary)]">
                    {r.status}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/pmo/projects/${r.project_id}`}
                      className="text-xs text-[var(--color-accent)] hover:underline"
                      title={r.project_name}
                    >
                      <span className="font-mono">{r.project_folio}</span>
                      <span className="ml-1 text-[var(--color-secondary)]">
                        — {r.project_name}
                      </span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}

function BuilderTemplatesView({ isAdmin }: { isAdmin: boolean }) {
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const all = await listBuilderTemplates({});
        if (!cancelled) setTemplates(all);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  if (error) {
    return <Banner variant="danger">{error}</Banner>;
  }

  const seeds = templates.filter((t) => t.is_seed);
  const customs = templates.filter((t) => !t.is_seed);

  return (
    <div className="space-y-5">
      {isAdmin && (
        <section className="rounded-[var(--radius-xl)] border border-violet-200 bg-violet-50 p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-violet-900">
            <Sparkles className="h-4 w-4" /> Builder Portafolio (PMO)
          </h2>
          <p className="mt-1 text-xs text-violet-800">
            Genera reportes Nivel 1 con scope tenant-wide.
          </p>
          <Link
            href="/pmo/reports/portfolio"
            className="mt-2 inline-flex items-center gap-1 rounded-[var(--radius-sm)] bg-violet-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-800"
          >
            Abrir Portafolio →
          </Link>
        </section>
      )}

      <section>
        <h2 className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
          Plantillas seed
        </h2>
        {seeds.length === 0 ? (
          <p className="text-xs text-[var(--text-tertiary)]">
            Sin plantillas seed instaladas.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {seeds.map((t) => (
              <TemplateRow key={t.id} tpl={t} />
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold text-[var(--text-primary)]">
          Mis plantillas + del tenant
        </h2>
        {customs.length === 0 ? (
          <p className="text-xs text-[var(--text-tertiary)]">
            Aún no hay plantillas custom. Crea una desde el builder de un
            proyecto.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {customs.map((t) => (
              <TemplateRow key={t.id} tpl={t} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function TemplateRow({ tpl }: { tpl: ReportBuilderTemplate }) {
  const levelLabel: Record<number, string> = {
    1: "Portafolio",
    2: "Organización",
    3: "Proyecto",
    4: "Custom",
  };
  return (
    <li className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-[var(--text-primary)]">
          <FileText className="mr-1 inline h-3.5 w-3.5 text-[var(--text-tertiary)]" />
          {tpl.name}
          {tpl.is_seed && (
            <Badge variant="neutral" className="ml-2 text-[10px]">
              seed
            </Badge>
          )}
        </p>
        {tpl.description && (
          <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
            {tpl.description}
          </p>
        )}
        <p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">
          Nivel: {levelLabel[tpl.level] ?? tpl.level} · {tpl.section_codes.length}{" "}
          secciones · Modo {tpl.composition_mode}
        </p>
      </div>
    </li>
  );
}
