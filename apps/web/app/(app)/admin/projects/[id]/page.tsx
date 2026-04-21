"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRightLeft,
  BarChart3,
  CircleDollarSign,
  ClipboardList,
  FileText,
  GitPullRequest,
  Lightbulb,
  ListTree,
  MessageSquare,
  Pencil,
  Shield,
  Sparkles,
  TriangleAlert,
  UserMinus,
  UserPlus,
  Users,
} from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { listUsers, type AdminUser } from "@/lib/api/admin";
import { getOrganization, type Organization } from "@/lib/api/organizations";
import {
  HEALTH_LABEL,
  MEMBER_ROLE_LABEL,
  PHASE_LABEL,
  TYPE_LABEL,
  addMember,
  changePhase,
  getProject,
  removeMember,
  updateProject,
  type ProjectDetail,
  type ProjectHealth,
  type ProjectMemberRole,
  type ProjectPhase,
} from "@/lib/api/projects";
import { cn } from "@/lib/cn";

type Tab = "overview" | "team" | "progress" | "budget" | "activity";

const VALID_TRANSITIONS: Record<ProjectPhase, ProjectPhase[]> = {
  planning: ["execution", "closed"],
  execution: ["support", "closed"],
  support: ["closed"],
  closed: [],
};

const MODULE_TOOLBAR: { key: keyof ProjectDetail["module_counts"] | string; label: string; href: (id: string) => string; icon: React.ReactNode }[] = [
  { key: "risks", label: "Riesgos", href: (id) => `/admin/projects/${id}/risks`, icon: <TriangleAlert className="h-4 w-4" aria-hidden /> },
  { key: "issues", label: "AIDs", href: (id) => `/admin/projects/${id}/issues`, icon: <Shield className="h-4 w-4" aria-hidden /> },
  { key: "change_requests", label: "Cambios", href: (id) => `/admin/projects/${id}/changes`, icon: <GitPullRequest className="h-4 w-4" aria-hidden /> },
  { key: "documents", label: "Documentos", href: (id) => `/admin/projects/${id}/documents`, icon: <FileText className="h-4 w-4" aria-hidden /> },
  { key: "lessons", label: "Lecciones", href: (id) => `/admin/projects/${id}/lessons`, icon: <Lightbulb className="h-4 w-4" aria-hidden /> },
  { key: "minutes", label: "Minutas", href: (id) => `/admin/projects/${id}/minutes`, icon: <MessageSquare className="h-4 w-4" aria-hidden /> },
  { key: "tasks", label: "Tareas", href: (id) => `/admin/projects/${id}/tasks`, icon: <ListTree className="h-4 w-4" aria-hidden /> },
  { key: "gantt", label: "Gantt", href: (id) => `/admin/projects/${id}/gantt`, icon: <BarChart3 className="h-4 w-4" aria-hidden /> },
  { key: "ai_minutes", label: "Minuta IA", href: (id) => `/admin/projects/${id}/ai-minutes/new`, icon: <Sparkles className="h-4 w-4" aria-hidden /> },
  { key: "reports", label: "Reporte IA", href: (id) => `/admin/projects/${id}/reports`, icon: <Sparkles className="h-4 w-4" aria-hidden /> },
];

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

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [notice, setNotice] = useState<string | null>(
    search.get("created") === "1" ? "Proyecto creado" : null,
  );

  const [phaseModal, setPhaseModal] = useState(false);
  const [phaseTarget, setPhaseTarget] = useState<ProjectPhase>("execution");
  const [phaseComment, setPhaseComment] = useState("");
  const [phaseSubmitting, setPhaseSubmitting] = useState(false);

  const [memberModal, setMemberModal] = useState(false);
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState<ProjectMemberRole>("team");
  const [memberSubmitting, setMemberSubmitting] = useState(false);
  const [users, setUsers] = useState<AdminUser[]>([]);

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

  async function openMemberModal() {
    setMemberModal(true);
    if (users.length === 0) {
      try {
        const r = await listUsers({ is_active: true, limit: 100 });
        setUsers(r.items);
      } catch {
        setUsers([]);
      }
    }
  }

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

  async function submitMember() {
    if (!project || !memberUserId) return;
    setMemberSubmitting(true);
    try {
      await addMember(project.id, { user_id: memberUserId, role_in_project: memberRole });
      setMemberModal(false);
      setMemberUserId("");
      setMemberRole("team");
      await reload();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "No se pudo agregar el miembro");
    } finally {
      setMemberSubmitting(false);
    }
  }

  async function handleRemove(userId: string) {
    if (!project) return;
    if (!confirm("¿Quitar a este miembro del proyecto?")) return;
    try {
      await removeMember(project.id, userId);
      await reload();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "No se pudo quitar el miembro");
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
          <BackLink fallbackHref="/admin/projects" />
          <nav className="text-[11px] text-[var(--text-tertiary)]">
            <Link href="/admin/projects" className="hover:underline">
              Proyectos
            </Link>
            <span className="mx-1">/</span>
            <span>{project.folio}</span>
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
            <Link href={`/admin/projects/${project.id}/edit`}>
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
      </header>

      {notice ? (
        <Banner variant="info" onClick={() => setNotice(null)}>
          {notice}
        </Banner>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Avance" value={`${project.progress}%`} />
        <MetricCard label="Presupuesto plan" value={formatMxn(project.budget)} />
        <MetricCard label="Presupuesto real" value={formatMxn(project.actual_budget)} />
        <HealthCard
          value={project.health_status}
          pending={healthPending}
          onChange={setHealth}
        />
      </section>

      <section
        aria-label="Módulos del proyecto"
        className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-3"
      >
        <div className="flex flex-wrap gap-2">
          {MODULE_TOOLBAR.map((m) => (
            <Link
              key={m.key}
              href={m.href(project.id)}
              className="inline-flex h-10 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-surface)] px-3 text-[13px] font-medium text-[var(--text-secondary)] hover:border-[var(--border-default)] hover:text-[var(--text-primary)]"
            >
              <span className="text-[var(--text-tertiary)]">{m.icon}</span>
              {m.label}
              <span className="ml-1 rounded-full bg-[var(--color-subtle)] px-1.5 text-[11px] tabular-nums text-[var(--text-secondary)]">
                {project.module_counts[m.key as string] ?? 0}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <nav role="tablist" className="flex items-center gap-1 border-b border-[var(--border-subtle)]">
        {(
          [
            { id: "overview", label: "Resumen" },
            { id: "team", label: "Equipo" },
            { id: "progress", label: "Avance" },
            { id: "budget", label: "Presupuesto" },
            { id: "activity", label: "Actividad" },
          ] as { id: Tab; label: string }[]
        ).map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "-mb-px h-9 border-b-2 px-3 text-[13px] font-medium transition-colors",
              tab === t.id
                ? "border-[var(--text-primary)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" ? (
        <section className="grid gap-4 lg:grid-cols-3">
          <Card title="Descripción" full>
            <p className="whitespace-pre-wrap text-[14px] text-[var(--text-primary)]">
              {project.description || "—"}
            </p>
          </Card>
          <Card title="Datos clave">
            <Row label="Organización" value={org?.name ?? "—"} />
            <Row label="Sponsor" value={project.sponsor ?? "—"} />
            <Row label="Prioridad" value={String(project.priority ?? "—")} />
            <Row label="Inicio" value={formatDate(project.start_date)} />
            <Row label="Fin" value={formatDate(project.end_date)} />
          </Card>
        </section>
      ) : null}

      {tab === "team" ? (
        <section className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
          <header className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-[var(--text-tertiary)]" aria-hidden />
              <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">Equipo</h2>
            </div>
            <Button size="sm" onClick={openMemberModal}>
              <UserPlus className="h-4 w-4" aria-hidden /> Agregar
            </Button>
          </header>
          <ul className="divide-y divide-[var(--border-subtle)]">
            {project.members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-[14px] font-medium text-[var(--text-primary)]">
                    {m.full_name || m.username}
                  </p>
                  <p className="text-[12px] text-[var(--text-tertiary)]">
                    {MEMBER_ROLE_LABEL[m.role_in_project] ?? m.role_in_project}
                  </p>
                </div>
                {m.role_in_project !== "pm" ? (
                  <Button variant="ghost" size="sm" onClick={() => handleRemove(m.user_id)}>
                    <UserMinus className="h-4 w-4" aria-hidden /> Quitar
                  </Button>
                ) : (
                  <Badge variant="accent">PM</Badge>
                )}
              </li>
            ))}
            {project.members.length === 0 ? (
              <li className="px-4 py-10 text-center text-[13px] text-[var(--text-tertiary)]">
                Sin miembros asignados.
              </li>
            ) : null}
          </ul>
        </section>
      ) : null}

      {tab === "progress" ? (
        <Card title="Avance">
          <div className="flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-muted)]">
              <div
                className="h-full rounded-full bg-[var(--text-primary)]"
                style={{ width: `${project.progress}%` }}
              />
            </div>
            <span className="w-12 text-right text-[13px] tabular-nums text-[var(--text-secondary)]">
              {project.progress}%
            </span>
          </div>
          <p className="mt-3 text-[13px] text-[var(--text-tertiary)]">
            Para editar el avance, usa <span className="text-[var(--text-primary)]">Editar</span> en el
            encabezado o actualiza desde el módulo de tareas cuando esté disponible.
          </p>
        </Card>
      ) : null}

      {tab === "budget" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Presupuesto plan">
            <div className="flex items-center gap-2">
              <CircleDollarSign className="h-5 w-5 text-[var(--text-tertiary)]" aria-hidden />
              <span className="text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {formatMxn(project.budget)}
              </span>
            </div>
          </Card>
          <Card title="Presupuesto real">
            <div className="flex items-center gap-2">
              <CircleDollarSign className="h-5 w-5 text-[var(--text-tertiary)]" aria-hidden />
              <span className="text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {formatMxn(project.actual_budget)}
              </span>
            </div>
          </Card>
        </div>
      ) : null}

      {tab === "activity" ? (
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
      ) : null}

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

      <Modal
        open={memberModal}
        onClose={() => !memberSubmitting && setMemberModal(false)}
        title="Agregar miembro"
        footer={
          <>
            <Button variant="secondary" onClick={() => setMemberModal(false)} disabled={memberSubmitting}>
              Cancelar
            </Button>
            <Button
              onClick={submitMember}
              loading={memberSubmitting}
              disabled={!memberUserId}
            >
              Agregar
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="block text-[12px] font-medium text-[var(--text-secondary)]">
            Usuario
          </label>
          <Select value={memberUserId} onChange={(e) => setMemberUserId(e.target.value)}>
            <option value="">Selecciona…</option>
            {users
              .filter((u) => !project.members.some((m) => m.user_id === u.id))
              .map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} · {u.email}
                </option>
              ))}
          </Select>
          <label className="block text-[12px] font-medium text-[var(--text-secondary)]">
            Rol en el proyecto
          </label>
          <Select
            value={memberRole}
            onChange={(e) => setMemberRole(e.target.value as ProjectMemberRole)}
          >
            {(Object.keys(MEMBER_ROLE_LABEL) as ProjectMemberRole[])
              .filter((r) => r !== "pm")
              .map((r) => (
                <option key={r} value={r}>
                  {MEMBER_ROLE_LABEL[r]}
                </option>
              ))}
          </Select>
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

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
        {label}
      </p>
      <p className="mt-1 text-[22px] font-semibold tracking-tight text-[var(--text-primary)] tabular-nums">
        {value}
      </p>
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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-0.5 sm:grid-cols-[140px_1fr]">
      <span className="text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">{label}</span>
      <span className="text-[13px] text-[var(--text-primary)]">{value}</span>
    </div>
  );
}
