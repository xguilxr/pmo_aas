"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertOctagon, Eye } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import {
  forceCloseProject,
  listAdminProjects,
  listOrgMetrics,
  type AdminProjectRow,
  type OrgMetrics,
} from "@/lib/api/admin-panel";
import { PHASE_LABEL } from "@/lib/api/projects";
import { cn } from "@/lib/cn";

function formatMxn(n: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(n);
}

export default function SupervisionPage() {
  const [rows, setRows] = useState<AdminProjectRow[]>([]);
  const { sortedRows, ctrl: supCtrl } = useSortableRows<AdminProjectRow>(rows);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [metrics, setMetrics] = useState<OrgMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [closeTarget, setCloseTarget] = useState<AdminProjectRow | null>(null);
  const [closeComment, setCloseComment] = useState("");
  const [closeSubmitting, setCloseSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, o, m] = await Promise.all([
        listAdminProjects({ include_inactive_orgs: true }),
        listOrganizations(),
        listOrgMetrics(),
      ]);
      setRows(p);
      setOrgs(o);
      setMetrics(m);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el panel");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const byOrg = useMemo(() => Object.fromEntries(orgs.map((o) => [o.id, o.name])), [orgs]);

  async function submitClose() {
    if (!closeTarget) return;
    setCloseSubmitting(true);
    try {
      await forceCloseProject(closeTarget.id, closeComment);
      setCloseTarget(null);
      setCloseComment("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar el proyecto");
    } finally {
      setCloseSubmitting(false);
    }
  }

  const kpis = useMemo(() => {
    const byPhase: Record<string, number> = {};
    const byHealth: Record<string, number> = {};
    let budget = 0;
    for (const p of rows) {
      byPhase[p.phase] = (byPhase[p.phase] ?? 0) + 1;
      byHealth[p.health_status] = (byHealth[p.health_status] ?? 0) + 1;
      budget += p.budget;
    }
    return { total: rows.length, byPhase, byHealth, budget };
  }, [rows]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex items-start gap-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--text-secondary)]">
          <Eye className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Panel del Tenant
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Vista global del tenant: todos los proyectos sin filtro de membresía. Uso restringido a
            Administradores.
          </p>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Proyectos" value={String(kpis.total)} loading={loading} />
        <Metric
          label="En ejecución"
          value={String(kpis.byPhase.execution ?? 0)}
          loading={loading}
        />
        <Metric
          label="En riesgo"
          value={String((kpis.byHealth.yellow ?? 0) + (kpis.byHealth.red ?? 0))}
          loading={loading}
          tone="warning"
        />
        <Metric label="Presupuesto" value={formatMxn(kpis.budget)} loading={loading} />
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {metrics.map((m) => (
          <article
            key={m.id}
            className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[14px] font-semibold text-[var(--text-primary)]">{m.name}</p>
                <p className="text-[11px] text-[var(--text-tertiary)]">
                  {m.is_active ? "Activa" : "Inactiva"}
                </p>
              </div>
              <Link
                href={`/admin/organizations/${m.id}`}
                className="text-[12px] text-[var(--color-accent)] hover:underline"
              >
                Detalle →
              </Link>
            </div>
            <div className="mt-4 flex items-baseline gap-3">
              <span className="text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {m.project_count_active}
              </span>
              <span className="text-[12px] text-[var(--text-tertiary)]">proyectos activos</span>
            </div>
            <p className="mt-1 text-[12px] tabular-nums text-[var(--text-secondary)]">
              {formatMxn(m.budget_total)} presupuesto total
            </p>
          </article>
        ))}
      </section>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <header className="flex items-center justify-between border-b border-[var(--border-subtle)] p-4">
          <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">Todos los proyectos</h2>
          <span className="text-[11px] text-[var(--text-tertiary)]">
            Incluye orgs inactivas
          </span>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
              <tr>
                <SortableTh<AdminProjectRow> sortKey="project" getter={(r) => (r as any).name ?? ""} ctrl={supCtrl} className="h-10 px-4">Proyecto</SortableTh>
                <SortableTh<AdminProjectRow> sortKey="org" getter={(r) => (r as any).organization_name ?? ""} ctrl={supCtrl} className="h-10 px-4">Organización</SortableTh>
                <SortableTh<AdminProjectRow> sortKey="phase" getter={(r) => (r as any).phase ?? ""} ctrl={supCtrl} className="h-10 px-4">Fase</SortableTh>
                <SortableTh<AdminProjectRow> sortKey="health" getter={(r) => (r as any).health ?? ""} ctrl={supCtrl} className="h-10 px-4">Salud</SortableTh>
                <SortableTh<AdminProjectRow> sortKey="budget" getter={(r) => (r as any).budget ?? 0} ctrl={supCtrl} className="h-10 px-4">Presupuesto</SortableTh>
                <th className="h-10 px-4" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="h-12 px-4">
                        <Skeleton className="h-4 w-20" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : rows.length ? (
                sortedRows.map((r) => (
                  <tr key={r.id} className="h-14 border-b border-[var(--border-subtle)]">
                    <td className="px-4">
                      <Link
                        href={`/pmo/projects/${r.id}?ctx=admin`}
                        className="font-medium text-[var(--text-primary)] hover:underline"
                      >
                        {r.name}
                      </Link>
                      <div className="font-mono text-[11px] text-[var(--text-tertiary)]">
                        {r.folio}
                      </div>
                    </td>
                    <td className="px-4 text-[var(--text-secondary)]">
                      {byOrg[r.organization_id] ?? "—"}
                    </td>
                    <td className="px-4">
                      <Badge>{PHASE_LABEL[r.phase as keyof typeof PHASE_LABEL] ?? r.phase}</Badge>
                    </td>
                    <td className="px-4">
                      <HealthDot health={r.health_status} />
                    </td>
                    <td className="px-4 tabular-nums text-[var(--text-secondary)]">
                      {formatMxn(r.budget)}
                    </td>
                    <td className="px-4 text-right">
                      {r.phase !== "closed" ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setCloseTarget(r)}
                        >
                          <AlertOctagon className="h-3.5 w-3.5" aria-hidden /> Forzar cierre
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-[var(--text-tertiary)]">
                    Sin proyectos registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        open={closeTarget !== null}
        onClose={() => !closeSubmitting && setCloseTarget(null)}
        title="Forzar cierre de proyecto"
        description="Esta acción marca el proyecto como cerrado y queda auditada. Úsala sólo si el PM no puede cerrarlo."
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setCloseTarget(null)}
              disabled={closeSubmitting}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={submitClose}
              loading={closeSubmitting}
              disabled={closeComment.trim().length < 5}
            >
              Cerrar proyecto
            </Button>
          </>
        }
      >
        <label className="mb-1.5 block text-[12px] font-medium text-[var(--text-secondary)]">
          Motivo (mínimo 5 caracteres)
        </label>
        <Textarea
          rows={4}
          value={closeComment}
          onChange={(e) => setCloseComment(e.target.value)}
          placeholder="Explicación breve que quedará en el audit log."
        />
      </Modal>
    </div>
  );
}

function Metric({
  label,
  value,
  loading,
  tone,
}: {
  label: string;
  value: string;
  loading?: boolean;
  tone?: "warning";
}) {
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
        {label}
      </p>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-20" />
      ) : (
        <p
          className={cn(
            "mt-1 text-[22px] font-semibold tabular-nums tracking-tight",
            tone === "warning" ? "text-[var(--color-warning-fg)]" : "text-[var(--text-primary)]",
          )}
        >
          {value}
        </p>
      )}
    </article>
  );
}

function HealthDot({ health }: { health: string }) {
  const color =
    health === "green"
      ? "bg-[var(--color-success-fg)]"
      : health === "yellow"
        ? "bg-[var(--color-warning-fg)]"
        : health === "red"
          ? "bg-[var(--color-danger-fg)]"
          : "bg-[var(--color-muted)]";
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] text-[var(--text-secondary)]">
      <span className={cn("h-2 w-2 rounded-full shadow-[inset_0_-1px_2px_oklch(0%_0_0/0.12)]", color)} />
      {health === "green" ? "Verde" : health === "yellow" ? "Amarillo" : health === "red" ? "Rojo" : health}
    </span>
  );
}
