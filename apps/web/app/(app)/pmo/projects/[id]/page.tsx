"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRightLeft, Pencil } from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { getOrganization, type Organization } from "@/lib/api/organizations";
import { getProjectCharter, type ProjectCharter } from "@/lib/api/project-charters";
import { listTasks, type Task } from "@/lib/api/tasks";
import {
  HEALTH_LABEL,
  PHASE_LABEL,
  TYPE_LABEL,
  changePhase,
  getProject,
  updateProject,
  type ProjectDetail,
  type ProjectHealth,
  type ProjectPhase,
} from "@/lib/api/projects";
import { cn } from "@/lib/cn";

const VALID_TRANSITIONS: Record<ProjectPhase, ProjectPhase[]> = {
  planning: ["execution", "closed"],
  execution: ["support", "closed"],
  support: ["closed"],
  closed: [],
};

function formatMxn(v: string | number | null): string {
  if (v === null) return "—";
  const n = typeof v === "string" ? Number(v) : v;
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(n);
}

// ENH-129: presupuesto restante = plan − real. null si no hay plan.
function remainingBudget(
  budget: string | number | null,
  actual: string | number | null,
): number | null {
  if (budget === null) return null;
  const b = typeof budget === "string" ? Number(budget) : budget;
  if (!Number.isFinite(b)) return null;
  const a = actual === null ? 0 : typeof actual === "string" ? Number(actual) : actual;
  return b - (Number.isFinite(a) ? a : 0);
}

function formatDate(s: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("es-MX", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return s;
  }
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const ctx = search.get("ctx") === "admin" ? "admin" : "pmo";

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [charter, setCharter] = useState<ProjectCharter | null>(null);
  // ENH-130: tareas para el mini-Gantt resumido (nivel 1, por meses).
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(
    search.get("created") === "1" ? "Proyecto creado" : null,
  );

  const [phaseModal, setPhaseModal] = useState(false);
  const [phaseTarget, setPhaseTarget] = useState<ProjectPhase>("execution");
  const [phaseComment, setPhaseComment] = useState("");
  const [phaseSubmitting, setPhaseSubmitting] = useState(false);

  // Stakeholders informativos del charter: sponsor / business_leader /
  // tech_leader. Sólo se listan los que tienen `name` no vacío.
  const charterStakeholders = useMemo(() => {
    if (!charter) return [];
    const rows: { role: string; name: string; email: string | null }[] = [];
    if (charter.sponsor?.trim()) {
      rows.push({ role: "Sponsor", name: charter.sponsor, email: charter.sponsor_email ?? null });
    }
    if (charter.business_leader?.trim()) {
      rows.push({
        role: "Líder de negocio",
        name: charter.business_leader,
        email: charter.business_leader_email ?? null,
      });
    }
    if (charter.tech_leader?.trim()) {
      rows.push({
        role: "Líder técnico",
        name: charter.tech_leader,
        email: charter.tech_leader_email ?? null,
      });
    }
    return rows;
  }, [charter]);

  const [healthPending, setHealthPending] = useState<ProjectHealth | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const p = await getProject(id);
      setProject(p);
      if (p.organization_id) {
        try {
          setOrg(await getOrganization(p.organization_id));
        } catch {
          setOrg(null);
        }
      }
      try {
        setCharter(await getProjectCharter(id));
      } catch {
        // Sin charter creado todavía o sin permiso; el tab de Stakeholders
        // queda oculto.
        setCharter(null);
      }
      try {
        setTasks(await listTasks(id));
      } catch {
        setTasks([]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el proyecto");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submitPhase() {
    if (!project) return;
    setPhaseSubmitting(true);
    try {
      await changePhase(project.id, { new_phase: phaseTarget, comment: phaseComment.trim() || null });
      setPhaseModal(false);
      setPhaseComment("");
      setNotice(`Fase actualizada a ${PHASE_LABEL[phaseTarget]}`);
      await reload();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "No se pudo cambiar la fase");
    } finally {
      setPhaseSubmitting(false);
    }
  }

  async function setHealth(h: ProjectHealth) {
    if (!project) return;
    setHealthPending(h);
    try {
      await updateProject(project.id, { health_status: h });
      await reload();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "No se pudo actualizar la salud");
    } finally {
      setHealthPending(null);
    }
  }

  const validTargets = useMemo(() => {
    if (!project) return [];
    return VALID_TRANSITIONS[project.phase];
  }, [project]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">{error ?? "Proyecto no encontrado"}</Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="space-y-3">
        <div className="flex items-center gap-2">
          <BackLink
            fallbackHref={
              ctx === "admin" && project.organization_id
                ? `/admin/organizations/${project.organization_id}`
                : "/pmo/projects"
            }
          />
          <nav className="text-[11px] text-[var(--text-tertiary)]">
            {ctx === "admin" ? (
              <>
                <Link href="/admin" className="hover:underline">
                  Admin
                </Link>
                <span className="mx-1">/</span>
                {project.organization_id ? (
                  <>
                    <Link
                      href={`/admin/organizations/${project.organization_id}`}
                      className="hover:underline"
                    >
                      {org?.name ?? "Organización"}
                    </Link>
                    <span className="mx-1">/</span>
                  </>
                ) : null}
                <span>{project.folio}</span>
              </>
            ) : (
              <>
                <Link href="/pmo/projects" className="hover:underline">
                  Proyectos
                </Link>
                <span className="mx-1">/</span>
                <span>{project.folio}</span>
              </>
            )}
          </nav>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                {project.name}
              </h1>
              <PhaseBadge phase={project.phase} />
              {project.type ? <Badge>{TYPE_LABEL[project.type]}</Badge> : null}
            </div>
            <p className="mt-1 font-mono text-[11px] text-[var(--text-tertiary)]">{project.folio}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/pmo/projects/${project.id}/edit`}>
              <Button variant="secondary">
                <Pencil className="h-4 w-4" aria-hidden /> Editar
              </Button>
            </Link>
            <Button
              onClick={() => setPhaseModal(true)}
              disabled={validTargets.length === 0}
              variant="secondary"
            >
              <ArrowRightLeft className="h-4 w-4" aria-hidden />
              Cambiar fase
            </Button>
          </div>
        </div>

        {/* ENH-128: Descripción + datos clave + stakeholders como parte de
            la hoja (bajo el ID), no como panel separado. */}
        <div className="space-y-3 border-t border-[var(--border-subtle)] pt-3">
          {project.description ? (
            <p className="max-w-3xl whitespace-pre-wrap text-[14px] text-[var(--text-secondary)]">
              {project.description}
            </p>
          ) : null}
          <dl className="flex flex-wrap gap-x-8 gap-y-2">
            <SheetField label="Organización" value={org?.name ?? "—"} />
            <SheetField label="Sponsor" value={project.sponsor ?? "—"} />
            <SheetField label="Prioridad" value={String(project.priority ?? "—")} />
            <SheetField label="Inicio" value={formatDate(project.start_date)} />
            <SheetField label="Fin" value={formatDate(project.end_date)} />
            {charterStakeholders.length > 0 ? (
              <SheetField
                label="Stakeholders"
                value={charterStakeholders
                  .map((s) => `${s.name} · ${s.role}`)
                  .join("   ")}
              />
            ) : null}
          </dl>
        </div>
      </header>

      {notice ? (
        <Banner variant="info" onClick={() => setNotice(null)}>
          {notice}
        </Banner>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <AvanceCard progress={project.progress} kpis={project.task_kpis} />
        <HealthCard
          value={project.health_status}
          pending={healthPending}
          onChange={setHealth}
        />
        <MetricCard label="Fase" value={PHASE_LABEL[project.phase]} />
        <MetricCard
          label="Presupuesto restante"
          value={formatMxn(remainingBudget(project.budget, project.actual_budget))}
        />
      </section>

      {/* ENH-130: tarjetas RAID (con link a detalle) + mini-Gantt nivel 1. */}
      <section aria-label="RAID y cronograma" className="grid gap-3 lg:grid-cols-[300px_1fr]">
        <div className="grid gap-3">
          <RaidCard
            label="Riesgos"
            count={project.module_counts.risks ?? 0}
            href={`/pmo/projects/${project.id}/raid?tab=risks`}
            tone="danger"
          />
          <RaidCard
            label="Acciones"
            count={project.module_counts.actions ?? 0}
            href={`/pmo/projects/${project.id}/raid?tab=actions`}
            tone="info"
          />
          <RaidCard
            label="Incidentes"
            count={project.module_counts.incidents ?? 0}
            href={`/pmo/projects/${project.id}/raid?tab=incidents`}
            tone="warning"
          />
          <RaidCard
            label="Decisiones"
            count={project.module_counts.decisions ?? 0}
            href={`/pmo/projects/${project.id}/raid?tab=decisions`}
            tone="success"
          />
        </div>
        <MiniGantt tasks={tasks} />
      </section>

      {/* ENH-131: solo el feed de actividad queda en la parte baja del
          Resumen (US-149 lo cablea con eventos reales del audit log). */}
      <Card title="Actividad">
        <div className="flex items-start gap-3">
          <Activity className="mt-0.5 h-4 w-4 text-[var(--text-tertiary)]" aria-hidden />
          <p className="text-[13px] text-[var(--text-tertiary)]">
            El feed completo de eventos del proyecto se integrará con el panel de auditoría del
            administrador. Mientras tanto, los cambios críticos (fase, asignaciones, salud) quedan
            registrados en el audit log global.
          </p>
        </div>
      </Card>

      <Modal
        open={phaseModal}
        onClose={() => !phaseSubmitting && setPhaseModal(false)}
        title="Cambiar fase del proyecto"
        description={
          validTargets.length
            ? `Transiciones válidas desde ${PHASE_LABEL[project.phase]}`
            : "No hay transiciones disponibles desde el estado actual"
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setPhaseModal(false)} disabled={phaseSubmitting}>
              Cancelar
            </Button>
            <Button onClick={submitPhase} loading={phaseSubmitting} disabled={!validTargets.length}>
              Confirmar
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-[12px] font-medium text-[var(--text-secondary)]">
            Nueva fase
          </label>
          <Select
            value={phaseTarget}
            onChange={(e) => setPhaseTarget(e.target.value as ProjectPhase)}
          >
            {validTargets.map((p) => (
              <option key={p} value={p}>
                {PHASE_LABEL[p]}
              </option>
            ))}
          </Select>
          <label className="block text-[12px] font-medium text-[var(--text-secondary)]">
            Comentario (opcional)
          </label>
          <Textarea
            rows={3}
            value={phaseComment}
            onChange={(e) => setPhaseComment(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  );
}

function PhaseBadge({ phase }: { phase: ProjectPhase }) {
  const map: Record<ProjectPhase, "info" | "success" | "warning" | "neutral"> = {
    planning: "info",
    execution: "success",
    support: "warning",
    closed: "neutral",
  };
  return <Badge variant={map[phase]}>{PHASE_LABEL[phase]}</Badge>;
}

function MetricCard({
  label,
  value,
  manualEdit,
}: {
  label: string;
  value: string;
  manualEdit?: { edited_at: string; edited_by: string } | null;
}) {
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
          {label}
        </p>
        {manualEdit ? (
          <span
            title={`Editado manualmente el ${new Date(manualEdit.edited_at).toLocaleString("es-MX")}`}
            className="text-[10px] font-medium text-[var(--color-warning-fg)]"
          >
            ✏️ Manual
          </span>
        ) : null}
      </div>
      <p className="mt-1 text-[22px] font-semibold tracking-tight text-[var(--text-primary)] tabular-nums">
        {value}
      </p>
    </article>
  );
}

// ENH-130: tarjeta RAID con count y link al detalle del módulo.
function RaidCard({
  label,
  count,
  href,
  tone,
}: {
  label: string;
  count: number;
  href: string;
  tone: "danger" | "info" | "warning" | "success";
}) {
  const dot = {
    danger: "bg-[var(--color-danger-fg)]",
    info: "bg-[var(--color-info-fg)]",
    warning: "bg-[var(--color-warning-fg)]",
    success: "bg-[var(--color-success-fg)]",
  }[tone];
  return (
    <Link
      href={href}
      className="group flex items-center justify-between rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] px-4 py-3 transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--color-subtle)]"
    >
      <span className="flex items-center gap-2">
        <span className={cn("h-2 w-2 rounded-full", dot)} />
        <span className="text-[13px] font-medium text-[var(--text-primary)]">{label}</span>
      </span>
      <span className="text-[18px] font-semibold tabular-nums text-[var(--text-primary)]">
        {count}
      </span>
    </Link>
  );
}

// ENH-130: mini-Gantt resumido del plan (tareas de nivel 1, columnas por
// mes). Read-only; vista panorámica sin entrar al tab Plan.
function MiniGantt({ tasks }: { tasks: Task[] }) {
  const level1 = tasks.filter((t) =>
    t.outline_level != null ? t.outline_level === 1 : !!t.wbs && !t.wbs.includes("."),
  );
  const dated = level1.filter((t) => t.start_date && t.end_date);
  const months: Date[] = [];
  let span = 0;
  let totalStart = 0;
  if (dated.length > 0) {
    const starts = dated.map((t) => new Date(t.start_date as string).getTime());
    const ends = dated.map((t) => new Date(t.end_date as string).getTime());
    const min = new Date(Math.min(...starts));
    const max = new Date(Math.max(...ends));
    const cur = new Date(min.getFullYear(), min.getMonth(), 1);
    const last = new Date(max.getFullYear(), max.getMonth(), 1);
    while (cur <= last) {
      months.push(new Date(cur));
      cur.setMonth(cur.getMonth() + 1);
    }
    totalStart = new Date(months[0].getFullYear(), months[0].getMonth(), 1).getTime();
    const totalEnd = new Date(
      months[months.length - 1].getFullYear(),
      months[months.length - 1].getMonth() + 1,
      1,
    ).getTime();
    span = totalEnd - totalStart;
  }
  function barPos(t: Task): { left: number; width: number } | null {
    if (!t.start_date || !t.end_date || span <= 0) return null;
    const s = new Date(t.start_date).getTime();
    const e = new Date(t.end_date).getTime();
    const left = ((s - totalStart) / span) * 100;
    const width = Math.max(2, ((e - s) / span) * 100);
    return { left: Math.max(0, left), width };
  }
  return (
    <article className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-3 text-[14px] font-semibold text-[var(--text-primary)]">
        Cronograma (nivel 1)
      </h2>
      {dated.length === 0 ? (
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Sin tareas de nivel 1 con fechas para mostrar.
        </p>
      ) : (
        <>
          <div className="flex border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)]">
            {months.map((mo) => (
              <div
                key={`${mo.getFullYear()}-${mo.getMonth()}`}
                className="flex-1 border-l border-[var(--border-subtle)] px-1 py-1 text-center first:border-l-0"
              >
                {mo.toLocaleDateString("es-MX", { month: "short", year: "2-digit" })}
              </div>
            ))}
          </div>
          <ul className="mt-2 space-y-2">
            {level1.map((t) => {
              const p = barPos(t);
              return (
                <li key={t.id}>
                  <div className="mb-0.5 truncate text-[12px] text-[var(--text-secondary)]">
                    {t.wbs ? `${t.wbs} ` : ""}
                    {t.name}
                  </div>
                  <div className="relative h-2.5 rounded bg-[var(--color-muted)]">
                    {p ? (
                      <div
                        className="absolute h-2.5 rounded bg-[var(--text-primary)]"
                        style={{ left: `${p.left}%`, width: `${p.width}%` }}
                        title={`${t.start_date} → ${t.end_date}`}
                      />
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </article>
  );
}

// ENH-129: gauge tipo dona con el % de avance al centro.
function ProgressGauge({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const r = 34;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <svg viewBox="0 0 80 80" className="h-20 w-20 -rotate-90" aria-hidden>
      <circle cx="40" cy="40" r={r} fill="none" stroke="var(--color-muted)" strokeWidth="8" />
      <circle
        cx="40"
        cy="40"
        r={r}
        fill="none"
        stroke="var(--text-primary)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`}
      />
    </svg>
  );
}

// ENH-129: tarjeta de Avance con gauge + 3 líneas (hitos, críticos,
// atrasados) usando los counts reales de task_kpis.
function AvanceCard({
  progress,
  kpis,
}: {
  progress: number;
  kpis: Record<string, number>;
}) {
  const overdue = kpis.overdue ?? 0;
  const lines: { label: string; value: string; danger?: boolean }[] = [
    { label: "Hitos", value: `${kpis.milestones_done ?? 0}/${kpis.milestones_total ?? 0}` },
    { label: "Críticos", value: `${kpis.critical_done ?? 0}/${kpis.critical_total ?? 0}` },
    { label: "Atrasados", value: String(overdue), danger: overdue > 0 },
  ];
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
        Avance
      </p>
      <div className="mt-2 flex items-center gap-4">
        <div className="relative h-20 w-20 shrink-0">
          <ProgressGauge value={progress} />
          <span className="absolute inset-0 flex items-center justify-center text-[16px] font-semibold tabular-nums text-[var(--text-primary)]">
            {progress}%
          </span>
        </div>
        <dl className="space-y-1">
          {lines.map((l) => (
            <div key={l.label} className="flex items-baseline justify-between gap-3 text-[12px]">
              <dt className="text-[var(--text-tertiary)]">{l.label}</dt>
              <dd
                className={cn(
                  "font-semibold tabular-nums",
                  l.danger ? "text-[var(--color-danger-fg)]" : "text-[var(--text-primary)]",
                )}
              >
                {l.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </article>
  );
}

function HealthCard({
  value,
  pending,
  onChange,
}: {
  value: ProjectHealth;
  pending: ProjectHealth | null;
  onChange: (h: ProjectHealth) => void;
}) {
  const HEALTHS: ProjectHealth[] = ["green", "yellow", "red"];
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
        Salud
      </p>
      <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-1">
        {HEALTHS.map((h) => {
          const active = value === h;
          const tone =
            h === "green"
              ? "bg-[var(--color-success-fg)]"
              : h === "yellow"
                ? "bg-[var(--color-warning-fg)]"
                : "bg-[var(--color-danger-fg)]";
          return (
            <button
              key={h}
              type="button"
              onClick={() => onChange(h)}
              aria-label={HEALTH_LABEL[h]}
              disabled={pending !== null}
              className={cn(
                "inline-flex h-7 items-center gap-1.5 rounded-full px-2 text-[11px] font-medium transition-colors",
                active
                  ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
              )}
            >
              <span className={cn("h-2 w-2 rounded-full", tone)} />
              {HEALTH_LABEL[h]}
            </button>
          );
        })}
      </div>
    </article>
  );
}

function Card({
  title,
  children,
  full,
}: {
  title: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <article
      className={cn(
        "rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5",
        full ? "lg:col-span-2" : undefined,
      )}
    >
      <h2 className="mb-3 text-[14px] font-semibold text-[var(--text-primary)]">{title}</h2>
      <div className="space-y-2">{children}</div>
    </article>
  );
}

// ENH-128: dato clave como parte de la hoja (definición inline, no panel).
function SheetField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">{label}</dt>
      <dd className="text-[13px] text-[var(--text-primary)]">{value}</dd>
    </div>
  );
}
