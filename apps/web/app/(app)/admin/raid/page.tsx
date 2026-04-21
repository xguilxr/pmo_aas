"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Eye, Shield } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  ISSUE_TYPE_LABEL,
  RISK_STATUS_LABEL,
  type IssueType,
} from "@/lib/api/modules";
import {
  listTenantIssues,
  listTenantRisks,
  type TenantIssue,
  type TenantRisk,
} from "@/lib/api/tenant-cross";

type Kind = "risks" | "actions" | "issues" | "decisions";

const KIND_LABEL: Record<Kind, string> = {
  risks: "Riesgos",
  actions: "Acciones",
  issues: "Incidentes",
  decisions: "Decisiones",
};

function parseKind(v: string | null): Kind {
  return v === "actions" || v === "issues" || v === "decisions" || v === "risks"
    ? v
    : "risks";
}

function TenantRaidInner() {
  const searchParams = useSearchParams();
  // ENH-009: el KPI del dashboard puede landear directo en un kind
  // específico vía ?kind=... (risks|actions|issues|decisions).
  // severity_min permite el caso "Riesgos severos".
  const severityMin = Number(searchParams.get("severity_min") ?? "") || null;
  const [kind, setKind] = useState<Kind>(parseKind(searchParams.get("kind")));
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  const [risks, setRisks] = useState<TenantRisk[]>([]);
  const [issues, setIssues] = useState<TenantIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewRisk, setPreviewRisk] = useState<TenantRisk | null>(null);
  const [previewIssue, setPreviewIssue] = useState<TenantIssue | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const issueType: IssueType | undefined =
      kind === "actions" ? "action" : kind === "decisions" ? "decision" : kind === "issues" ? "issue" : undefined;
    const promise =
      kind === "risks"
        ? listTenantRisks(filter).then((r) => {
            if (!cancelled) {
              setRisks(r);
              setIssues([]);
            }
          })
        : listTenantIssues({ ...filter, type: issueType }).then((r) => {
            if (!cancelled) {
              setIssues(r);
              setRisks([]);
            }
          });
    promise
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar RAID");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kind, filter]);

  // ENH-009: cuando el link trae ?severity_min=N (típicamente 13 para
  // "Riesgos severos" desde el dashboard), filtramos client-side.
  const visibleRisks = useMemo(
    () => (severityMin ? risks.filter((r) => (r.severity ?? 0) >= severityMin) : risks),
    [risks, severityMin],
  );
  const rows = kind === "risks" ? visibleRisks : issues;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            RAID · Tenant
          </h1>
        </div>
        <p className="text-sm text-[var(--color-tertiary)]">
          Vista consolidada de Riesgos · Acciones · Incidentes · Decisiones de
          todos los proyectos accesibles.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <TenantCrossFilters
          value={filter}
          onChange={setFilter}
          extras={
            <Select
              aria-label="Tipo"
              className="h-9 min-w-[160px]"
              value={kind}
              onChange={(e) => setKind(e.target.value as Kind)}
            >
              {(Object.keys(KIND_LABEL) as Kind[]).map((k) => (
                <option key={k} value={k}>
                  {KIND_LABEL[k]}
                </option>
              ))}
            </Select>
          }
        />
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
            Sin registros para los filtros actuales.
          </div>
        ) : kind === "risks" ? (
          <RiskTable rows={visibleRisks} onPreview={setPreviewRisk} />
        ) : (
          <IssueTable rows={issues} kind={kind} onPreview={setPreviewIssue} />
        )}
      </section>

      <ItemPreviewModal
        open={previewRisk !== null}
        onClose={() => setPreviewRisk(null)}
        title={previewRisk?.title ?? ""}
        subtitle={previewRisk?.folio}
        fields={
          previewRisk
            ? [
                { label: "ID", value: previewRisk.id, mono: true },
                {
                  label: "Proyecto",
                  value: `${previewRisk.project_folio} — ${previewRisk.project_name}`,
                },
                { label: "Severidad", value: previewRisk.severity ?? "—" },
                {
                  label: "Estado",
                  value: RISK_STATUS_LABEL[previewRisk.status] ?? previewRisk.status,
                },
                { label: "Fecha límite", value: previewRisk.due_date ?? "—" },
              ]
            : []
        }
        description={previewRisk?.description ?? null}
      />

      <ItemPreviewModal
        open={previewIssue !== null}
        onClose={() => setPreviewIssue(null)}
        title={previewIssue?.title ?? ""}
        subtitle={previewIssue?.folio}
        fields={
          previewIssue
            ? [
                { label: "ID", value: previewIssue.id, mono: true },
                {
                  label: "Proyecto",
                  value: `${previewIssue.project_folio} — ${previewIssue.project_name}`,
                },
                { label: "Tipo", value: ISSUE_TYPE_LABEL[previewIssue.type] ?? previewIssue.type },
                { label: "Prioridad", value: previewIssue.priority ?? "—" },
                { label: "Estado", value: previewIssue.status },
                { label: "Compromiso", value: previewIssue.committed_date ?? "—" },
              ]
            : []
        }
        description={previewIssue?.description ?? null}
      />
    </div>
  );
}

function RiskTable({
  rows,
  onPreview,
}: {
  rows: TenantRisk[];
  onPreview: (r: TenantRisk) => void;
}) {
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
        <tr>
          <th className="w-10 px-3 py-2" />
          <th className="px-3 py-2 font-medium">Folio</th>
          <th className="px-3 py-2 font-medium">Título</th>
          <th className="px-3 py-2 font-medium">Severidad</th>
          <th className="px-3 py-2 font-medium">Estado</th>
          <th className="px-3 py-2 font-medium">Proyecto</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
            <td className="px-3 py-2">
              <button
                type="button"
                onClick={() => onPreview(r)}
                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                aria-label="Preview"
              >
                <Eye className="h-3.5 w-3.5" aria-hidden />
              </button>
            </td>
            <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
              {r.folio}
            </td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}/raid?tab=risks`}
                className="text-[var(--color-primary)] hover:underline"
              >
                {r.title}
              </Link>
            </td>
            <td className="px-3 py-2">
              <Badge variant={(r.severity ?? 0) >= 13 ? "danger" : (r.severity ?? 0) >= 6 ? "warning" : "success"}>
                {r.severity ?? "—"}
              </Badge>
            </td>
            <td className="px-3 py-2 text-[var(--color-secondary)]">
              {RISK_STATUS_LABEL[r.status] ?? r.status}
            </td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}`}
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
  );
}

function IssueTable({
  rows,
  kind,
  onPreview,
}: {
  rows: TenantIssue[];
  kind: Kind;
  onPreview: (r: TenantIssue) => void;
}) {
  const typeLabel = useMemo(
    () =>
      kind === "actions"
        ? "Acción"
        : kind === "decisions"
          ? "Decisión"
          : "Incidente",
    [kind],
  );
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
        <tr>
          <th className="w-10 px-3 py-2" />
          <th className="px-3 py-2 font-medium">Folio</th>
          <th className="px-3 py-2 font-medium">Título</th>
          <th className="px-3 py-2 font-medium">Tipo</th>
          <th className="px-3 py-2 font-medium">Estado</th>
          <th className="px-3 py-2 font-medium">Proyecto</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
            <td className="px-3 py-2">
              <button
                type="button"
                onClick={() => onPreview(r)}
                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
                aria-label="Preview"
              >
                <Eye className="h-3.5 w-3.5" aria-hidden />
              </button>
            </td>
            <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
              {r.folio}
            </td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}/raid?tab=${kind}`}
                className="text-[var(--color-primary)] hover:underline"
              >
                {r.title}
              </Link>
            </td>
            <td className="px-3 py-2 text-[var(--color-secondary)]">{typeLabel}</td>
            <td className="px-3 py-2 text-[var(--color-secondary)]">{r.status}</td>
            <td className="px-3 py-2">
              <Link
                href={`/admin/projects/${r.project_id}`}
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
  );
}

export default function TenantRaidPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-[var(--color-tertiary)]">Cargando…</div>}>
      <TenantRaidInner />
    </Suspense>
  );
}
