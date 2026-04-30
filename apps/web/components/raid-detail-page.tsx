"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, CheckCircle2, GitCommit, Shield, TriangleAlert } from "lucide-react";

import { IssueDetailBody, RiskDetailBody } from "@/components/raid-detail-body";
import { RaidEditFields } from "@/components/raid-edit-fields";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch, ApiError } from "@/lib/api";
import {
  ISSUE_STATUS_LABEL,
  ISSUE_TYPE_LABEL,
  RISK_STATUS_LABEL,
  type Issue,
  type IssueType,
  type Risk,
} from "@/lib/api/modules";
import { cn } from "@/lib/cn";

/**
 * US-065 — página dedicada de un ítem RAID.
 *
 * Se usa en dos rutas:
 * - `/pmo/projects/[id]/raid/[raidId]` (scope proyecto).
 * - `/pmo/raid/[type]/[raidId]` (vista cross-tenant).
 *
 * Diferencia: el breadcrumb superior. El resto del layout es idéntico
 * (header + metadata + descripción + panel editable + historial).
 */

export type RaidDetailType = "risk" | "action" | "incident" | "decision";

type HistoryEntry = {
  id: number;
  user_id: string | null;
  action: string;
  occurred_at: string;
  details: Record<string, unknown>;
};

export function RaidDetailPage({
  raidType,
  itemId,
  breadcrumb,
}: {
  raidType: RaidDetailType;
  itemId: string;
  breadcrumb: React.ReactNode;
}) {
  const isRisk = raidType === "risk";
  const [risk, setRisk] = useState<Risk | null>(null);
  const [issue, setIssue] = useState<Issue | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const detailUrl = isRisk
      ? `/api/v1/risks/${itemId}`
      : `/api/v1/issues/${itemId}`;
    const entityType = isRisk ? "risk" : "issue";
    const historyUrl = `/api/v1/history?entity_type=${entityType}&entity_id=${itemId}`;

    Promise.all([
      apiFetch<Risk | Issue>(detailUrl),
      apiFetch<HistoryEntry[]>(historyUrl).catch(() => []),
    ])
      .then(([detail, hist]) => {
        if (cancelled) return;
        if (isRisk) setRisk(detail as Risk);
        else setIssue(detail as Issue);
        setHistory(hist);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.status === 404
                ? "Este ítem no existe o no tienes permiso para verlo."
                : err.message
              : "No se pudo cargar el ítem",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isRisk, itemId]);

  const issueTypeFromTab = useMemo<IssueType | null>(() => {
    if (raidType === "action") return "action";
    if (raidType === "incident") return "issue";
    if (raidType === "decision") return "decision";
    return null;
  }, [raidType]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        {breadcrumb}
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  const item = isRisk ? risk : issue;
  if (!item) return null;

  const Icon = isRisk
    ? TriangleAlert
    : issueTypeFromTab === "action"
      ? GitCommit
      : issueTypeFromTab === "decision"
        ? CheckCircle2
        : AlertTriangle;

  const statusLabel = isRisk
    ? RISK_STATUS_LABEL[(risk as Risk).status] ?? (risk as Risk).status
    : ISSUE_STATUS_LABEL[(issue as Issue).status] ?? (issue as Issue).status;

  const typeLabel = isRisk
    ? "Riesgo"
    : issueTypeFromTab
      ? ISSUE_TYPE_LABEL[issueTypeFromTab] ??
        ISSUE_TYPE_LABEL[(issue as Issue).type] ??
        (issue as Issue).type
      : "";

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      {breadcrumb}

      <header className="flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)]">
              <Icon className="h-5 w-5 text-[var(--color-tertiary)]" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-mono uppercase tracking-wide text-[var(--color-tertiary)]">
                {item.folio} · {typeLabel}
              </p>
              <h1 className="mt-0.5 text-xl font-semibold text-[var(--color-primary)]">
                {item.title}
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="neutral">{statusLabel}</Badge>
            {isRisk && (risk as Risk).severity != null ? (
              <Badge
                variant={
                  ((risk as Risk).severity ?? 0) >= 13
                    ? "danger"
                    : ((risk as Risk).severity ?? 0) >= 6
                      ? "warning"
                      : "success"
                }
              >
                Sev {(risk as Risk).severity}
              </Badge>
            ) : null}
            {!isRisk && (issue as Issue).priority != null ? (
              <Badge variant="neutral">P{(issue as Issue).priority}</Badge>
            ) : null}
          </div>
        </div>
      </header>

      <div className="grid gap-5 md:grid-cols-[260px_1fr]">
        <aside className="space-y-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
          <SidebarField label="Área" value={item.area?.name ?? "—"} />
          <SidebarField
            label="Responsable"
            value={
              item.owner?.full_name ||
              item.owner?.email ||
              (item.owner_id ? "Usuario eliminado" : "—")
            }
          />
          <SidebarField
            label="F. Creación"
            value={
              isRisk
                ? (risk as Risk).identified_at ?? "—"
                : (issue as Issue).reported_at
                  ? new Date((issue as Issue).reported_at as string)
                      .toISOString()
                      .slice(0, 10)
                  : "—"
            }
          />
          <SidebarField
            label="F. Compromiso"
            value={
              isRisk
                ? (risk as Risk).due_date ?? "—"
                : (issue as Issue).committed_date ?? "—"
            }
          />
          {isRisk ? (
            <SidebarField
              label="P × I"
              value={`${(risk as Risk).probability ?? "—"} × ${(risk as Risk).impact ?? "—"}`}
            />
          ) : null}
          {isRisk ? (
            <SidebarField
              label="Categoría"
              value={(risk as Risk).category ?? "—"}
            />
          ) : null}
          <SidebarField
            label="Proyecto"
            value={
              <Link
                href={`/pmo/projects/${item.project_id}`}
                className="font-mono text-[12px] text-[var(--color-accent)] hover:underline"
              >
                {item.project_id.slice(0, 8)}…
              </Link>
            }
          />
        </aside>

        <div className="space-y-5">
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <h2 className="mb-2 text-sm font-semibold text-[var(--color-primary)]">
              Descripción
            </h2>
            <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
              {item.description || (
                <span className="italic text-[var(--color-tertiary)]">
                  Sin descripción.
                </span>
              )}
            </p>
            {isRisk && (risk as Risk).mitigation_strategy ? (
              <div className="mt-4">
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                  Estrategia de mitigación
                </h3>
                <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
                  {(risk as Risk).mitigation_strategy}
                </p>
              </div>
            ) : null}
            {!isRisk && (issue as Issue).resolution ? (
              <div className="mt-4">
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                  Resolución
                </h3>
                <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
                  {(issue as Issue).resolution}
                </p>
              </div>
            ) : null}
          </section>

          <section className="space-y-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-[var(--color-primary)]">
                Editar / comentarios
              </h2>
              {/* ENH-036: edición completa de área, responsable, fechas
                  y otros campos. */}
              {isRisk ? (
                <RaidEditFields
                  kind="risk"
                  item={risk as Risk}
                  onSaved={(r) => setRisk(r)}
                />
              ) : (
                <RaidEditFields
                  kind="issue"
                  item={issue as Issue}
                  onSaved={(i) => setIssue(i)}
                />
              )}
            </div>
            {isRisk ? (
              <RiskDetailBody
                risk={risk as Risk}
                onUpdated={(r) => setRisk((prev) => (prev ? { ...prev, ...r } : prev))}
              />
            ) : (
              <IssueDetailBody
                issue={issue as Issue}
                onUpdated={(i) => setIssue((prev) => (prev ? { ...prev, ...i } : prev))}
              />
            )}
          </section>

          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">
              Historial de cambios
            </h2>
            {history.length === 0 ? (
              <p className="text-[13px] italic text-[var(--color-tertiary)]">
                Sin eventos registrados.
              </p>
            ) : (
              <ol className="space-y-2 text-[12px]">
                {history.map((h) => (
                  <li
                    key={h.id}
                    className="flex items-start gap-3 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2"
                  >
                    <span className="font-mono text-[11px] text-[var(--color-tertiary)]">
                      {new Date(h.occurred_at).toLocaleString("es-MX", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </span>
                    <span className="flex-1">
                      <span className="font-medium text-[var(--color-primary)]">
                        {h.action}
                      </span>
                      {h.user_id ? (
                        <span className="ml-2 font-mono text-[11px] text-[var(--color-tertiary)]">
                          {h.user_id.slice(0, 8)}
                        </span>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function SidebarField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
        {label}
      </p>
      <p
        className={cn(
          "mt-0.5 break-words text-[13px] text-[var(--color-primary)]",
          mono ? "font-mono text-[11px]" : "",
        )}
      >
        {value}
      </p>
    </div>
  );
}

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
    >
      <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
      {label}
    </Link>
  );
}
