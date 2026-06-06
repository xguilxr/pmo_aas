"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Scale,
  Trash2,
  TriangleAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch, ApiError } from "@/lib/api";
import { listUsers } from "@/lib/api/admin";
import {
  addIssueComment,
  addRiskComment,
  deleteIssue,
  deleteRisk,
  ISSUE_STATUS_LABEL,
  ISSUE_TYPE_LABEL,
  RISK_STATUS_LABEL,
  updateIssue,
  updateRisk,
  type Issue,
  type IssueType,
  type Risk,
} from "@/lib/api/modules";
import { listProjectAreas, type ProjectArea } from "@/lib/api/project-areas";
import { cn } from "@/lib/cn";
import { RiskActionsCard } from "@/components/risk-actions-card";

/**
 * US-100 — vista detalle item RAID layout "Denso".
 *
 * Aplica a 4 tipos: risk, action, incident, decision. Spec canónica
 * en `docs/design-system/raid-detail-denso.md`. Mantiene el contenido
 * existente; cambia la organización: header card + strip 6 columnas
 * + cards stacked + edit toggle global (no inline).
 *
 * Ruta scope-proyecto: `/pmo/projects/[id]/raid/[raidId]`.
 * Ruta cross-tenant: `/pmo/raid/[type]/[raidId]`.
 */

export type RaidDetailType = "risk" | "action" | "incident" | "decision";

type HistoryEntry = {
  id: number;
  user_id: string | null;
  action: string;
  occurred_at: string;
  details: Record<string, unknown>;
};

type EditDraft = {
  title: string;
  description: string;
  area_id: string;
  owner_id: string;
  category: string; // risk only
  probability: number; // risk only
  impact: number; // risk only
  mitigation_strategy: string; // risk only
  identified_at: string; // risk only
  due_date: string; // risk only
  closure_note: string; // risk only
  type: IssueType;
  priority: number | "";
  reported_at: string;
  committed_date: string;
  resolution: string;
};

function emptyDraft(): EditDraft {
  return {
    title: "",
    description: "",
    area_id: "",
    owner_id: "",
    category: "",
    probability: 1,
    impact: 1,
    mitigation_strategy: "",
    identified_at: "",
    due_date: "",
    closure_note: "",
    type: "action",
    priority: "",
    reported_at: "",
    committed_date: "",
    resolution: "",
  };
}

function draftFromRisk(r: Risk): EditDraft {
  return {
    ...emptyDraft(),
    title: r.title,
    description: r.description ?? "",
    area_id: r.area_id ?? "",
    owner_id: r.owner_id ?? "",
    category: r.category ?? "",
    probability: r.probability ?? 1,
    impact: r.impact ?? 1,
    mitigation_strategy: r.mitigation_strategy ?? "",
    identified_at: r.identified_at ?? "",
    due_date: r.due_date ?? "",
    closure_note: r.closure_note ?? "",
  };
}

function draftFromIssue(i: Issue): EditDraft {
  return {
    ...emptyDraft(),
    title: i.title,
    description: i.description ?? "",
    area_id: i.area_id ?? "",
    owner_id: i.owner_id ?? "",
    type: i.type,
    priority: i.priority ?? "",
    reported_at: i.reported_at
      ? new Date(i.reported_at).toISOString().slice(0, 10)
      : "",
    committed_date: i.committed_date ?? "",
    resolution: i.resolution ?? "",
  };
}

export function RaidDetailPage({
  raidType,
  itemId,
  breadcrumb,
}: {
  raidType: RaidDetailType;
  itemId: string;
  breadcrumb: React.ReactNode;
}) {
  const router = useRouter();
  const isRisk = raidType === "risk";
  const [risk, setRisk] = useState<Risk | null>(null);
  const [issue, setIssue] = useState<Issue | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ENH-112: borrar el ítem RAID (riesgo o incidente/acción/decisión).
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ENH-069: edit toggle global con draft transaccional.
  // US-100 fix (rework): el owner reportó que el botón Editar no
  // aparecía. La causa probable era que `useMyPermissions` no
  // devolvía las caps `raid:update`/`raid:write` para el rol activo.
  // Permissive default: el backend valida la PATCH si el usuario no
  // tiene permiso. Mismo enfoque que el resto del módulo.
  const canEdit = true;
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<EditDraft>(emptyDraft());
  const [editError, setEditError] = useState<string | null>(null);

  // Selects del form: áreas + usuarios. Se cargan al entrar a edición.
  const [areas, setAreas] = useState<ProjectArea[]>([]);
  const [users, setUsers] = useState<
    { id: string; full_name: string; email: string }[]
  >([]);

  // ENH-070: card unificada Comentarios + Historial.
  const [commentText, setCommentText] = useState("");
  const [postingComment, setPostingComment] = useState(false);

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

  // ENH-070 fix: cargar usuarios + áreas EAGER al tener el item
  // cargado. Necesario para mostrar nombre del autor en comentarios
  // (no user_id) y resolver áreas/responsables del strip incluso en
  // modo lectura.
  useEffect(() => {
    const projectId = isRisk ? risk?.project_id : issue?.project_id;
    if (!projectId) return;
    let cancelled = false;
    Promise.all([
      listProjectAreas(projectId, { is_active: true }),
      listUsers({ is_active: true, page: 1, limit: 200 }).catch(() => ({
        items: [] as { id: string; full_name?: string | null; email: string }[],
      })),
    ])
      .then(([areaRows, usersResp]) => {
        if (cancelled) return;
        setAreas(areaRows);
        setUsers(
          (
            usersResp as {
              items: { id: string; full_name?: string | null; email: string }[];
            }
          ).items.map((u) => ({
            id: u.id,
            full_name: u.full_name ?? "",
            email: u.email,
          })),
        );
      })
      .catch(() => {
        /* non-fatal */
      });
    return () => {
      cancelled = true;
    };
  }, [isRisk, risk?.project_id, issue?.project_id]);

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

  // Iconos por tipo (spec): warning Riesgo, check Acción, alert
  // Issue, scale Decisión.
  const Icon = isRisk
    ? TriangleAlert
    : issueTypeFromTab === "action"
      ? CheckCircle2
      : issueTypeFromTab === "decision"
        ? Scale
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

  const statusVariant: "info" | "success" | "danger" | "neutral" = isRisk
    ? raidStatusVariant((risk as Risk).status)
    : issueStatusVariant((issue as Issue).status);

  function startEdit() {
    if (isRisk && risk) setDraft(draftFromRisk(risk));
    else if (!isRisk && issue) setDraft(draftFromIssue(issue));
    setEditError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setEditError(null);
  }

  async function saveEdit() {
    if (saving) return;
    if (draft.title.trim().length < 2) {
      setEditError("El título es obligatorio (mín. 2 caracteres).");
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      if (isRisk && risk) {
        const updated = await updateRisk(risk.id, {
          title: draft.title.trim(),
          description: draft.description.trim() || null,
          category: draft.category.trim() || null,
          area_id: draft.area_id || undefined,
          owner_id: draft.owner_id || null,
          probability: draft.probability,
          impact: draft.impact,
          mitigation_strategy: draft.mitigation_strategy.trim() || null,
          identified_at: draft.identified_at || null,
          due_date: draft.due_date || null,
          closure_note: draft.closure_note.trim() || null,
        });
        setRisk(updated);
      } else if (!isRisk && issue) {
        const updated = await updateIssue(issue.id, {
          title: draft.title.trim(),
          description: draft.description.trim() || null,
          type: draft.type,
          area_id: draft.area_id || undefined,
          owner_id: draft.owner_id || null,
          priority: draft.priority === "" ? null : Number(draft.priority),
          reported_at: draft.reported_at
            ? new Date(`${draft.reported_at}T00:00:00Z`).toISOString()
            : null,
          committed_date: draft.committed_date || null,
          resolution: draft.resolution.trim() || null,
        });
        setIssue(updated);
      }
      setEditing(false);
    } catch (err) {
      setEditError(
        err instanceof ApiError ? err.message : "No se pudo guardar los cambios",
      );
    } finally {
      setSaving(false);
    }
  }

  async function postComment() {
    if (postingComment) return;
    const text = commentText.trim();
    if (!text) return;
    setPostingComment(true);
    try {
      if (isRisk && risk) {
        const updated = await addRiskComment(risk.id, { text });
        setRisk(updated);
      } else if (!isRisk && issue) {
        const updated = await addIssueComment(issue.id, { text });
        setIssue(updated);
      }
      setCommentText("");
    } catch {
      /* el caller no tiene un banner global; se puede mejorar */
    } finally {
      setPostingComment(false);
    }
  }

  async function handleDelete() {
    if (deleting) return;
    const current = isRisk ? risk : issue;
    if (!current) return;
    setDeleting(true);
    setError(null);
    try {
      const projectId = current.project_id;
      if (isRisk) await deleteRisk(current.id);
      else await deleteIssue(current.id);
      router.replace(`/pmo/projects/${projectId}/raid?deleted=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar el ítem");
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  const fmtDate = (iso: string | null | undefined) => {
    if (!iso) return null;
    if (iso.length === 10) return iso; // YYYY-MM-DD
    try {
      return new Date(iso).toISOString().slice(0, 10);
    } catch {
      return iso;
    }
  };

  // BUG-052: el breadcrumb canónico vive en el padre (route page).
  return (
    <div className="mx-auto max-w-5xl space-y-3 p-6">
      {/* Fila de navegación: breadcrumb + botón Editar global */}
      <div className="flex items-center justify-between gap-2 px-0">
        <div className="min-w-0 flex-1">{breadcrumb}</div>
        <div className="flex flex-none items-center gap-2">
          {canEdit ? (
            <Button
              type="button"
              variant={editing ? "secondary" : "primary"}
              size="sm"
              onClick={() => (editing ? cancelEdit() : startEdit())}
              disabled={saving}
            >
              {editing ? "Editando…" : "Editar"}
            </Button>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setConfirmDelete(true)}
            disabled={saving}
            aria-label="Borrar ítem"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden /> Borrar
          </Button>
        </div>
      </div>

      {/* Header card: bloque superior (icono + ID/tipo/estado/sev + título)
          + strip de metadatos (6 columnas) */}
      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="flex flex-col gap-2 px-[18px] py-[14px]">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 flex-none items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)]">
              <Icon className="h-5 w-5 text-[var(--color-tertiary)]" aria-hidden />
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-[11px] text-[var(--color-tertiary)]">
                    {item.folio}
                  </span>
                  <span className="text-[var(--color-tertiary)]">·</span>
                  <span
                    className="rounded border border-[var(--chrome-soft-border,_var(--border-default))] bg-[var(--chrome-soft-bg,_var(--color-subtle))] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--chrome-soft-text,_var(--color-tertiary))]"
                  >
                    {typeLabel}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant}>{statusLabel}</Badge>
                  {isRisk && (risk as Risk).severity != null ? (
                    <Badge
                      variant={
                        ((risk as Risk).severity ?? 0) >= 12
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
              {editing ? (
                <Input
                  value={draft.title}
                  onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  className="text-[17px] font-semibold"
                />
              ) : (
                <h1
                  className="text-[17px] font-semibold leading-snug text-[var(--color-primary)]"
                  style={{ lineHeight: 1.4 }}
                >
                  {item.title}
                </h1>
              )}
            </div>
          </div>
        </header>

        {/* Strip 6 columnas con borde superior + fondo soft. */}
        <div className="grid gap-4 border-t border-[var(--border-default)] bg-[var(--chrome-soft-bg,_var(--color-subtle))] px-[18px] py-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
          {/* Área */}
          <StripCell label="Área">
            {editing ? (
              <Select
                value={draft.area_id}
                onChange={(e) => setDraft({ ...draft, area_id: e.target.value })}
              >
                <option value="">— sin área —</option>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
            ) : (
              item.area?.name ?? <Empty />
            )}
          </StripCell>
          {/* Responsable / Decisor */}
          <StripCell label={raidType === "decision" ? "Decisor" : "Responsable"}>
            {editing ? (
              <Select
                value={draft.owner_id}
                onChange={(e) => setDraft({ ...draft, owner_id: e.target.value })}
              >
                <option value="">— sin asignar —</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name?.trim() || u.email}
                  </option>
                ))}
              </Select>
            ) : item.owner?.full_name || item.owner?.email ? (
              item.owner.full_name || item.owner.email
            ) : (
              <Empty />
            )}
          </StripCell>
          {/* Centro: P×I (risk) | Prioridad (action) | Severidad (issue) | Tipo decisión (decision) */}
          {isRisk ? (
            <StripCell label="P × I">
              {editing ? (
                <div className="flex items-center gap-1">
                  <Select
                    value={String(draft.probability)}
                    onChange={(e) =>
                      setDraft({ ...draft, probability: Number(e.target.value) })
                    }
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </Select>
                  <span className="text-[var(--color-tertiary)]">×</span>
                  <Select
                    value={String(draft.impact)}
                    onChange={(e) =>
                      setDraft({ ...draft, impact: Number(e.target.value) })
                    }
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </Select>
                </div>
              ) : (
                <span>
                  {(risk as Risk).probability ?? "—"} ×{" "}
                  {(risk as Risk).impact ?? "—"}
                  <span className="ml-1 text-[var(--color-tertiary)]">
                    = {(risk as Risk).severity ?? "—"}
                  </span>
                </span>
              )}
            </StripCell>
          ) : raidType === "decision" ? (
            <StripCell label="Tipo decisión">{typeLabel}</StripCell>
          ) : raidType === "incident" ? (
            <StripCell label="Severidad">
              {(issue as Issue).priority != null ? (
                `P${(issue as Issue).priority}`
              ) : (
                <Empty />
              )}
            </StripCell>
          ) : (
            <StripCell label="Prioridad">
              {editing ? (
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={draft.priority}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      priority: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                />
              ) : (issue as Issue).priority != null ? (
                `P${(issue as Issue).priority}`
              ) : (
                <Empty />
              )}
            </StripCell>
          )}
          {/* Categoría / Estado de aprobación */}
          {isRisk ? (
            <StripCell label="Categoría">
              {editing ? (
                <Input
                  value={draft.category}
                  onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                />
              ) : (
                (risk as Risk).category ?? <Empty />
              )}
            </StripCell>
          ) : raidType === "decision" ? (
            <StripCell label="Estado aprobación">{statusLabel}</StripCell>
          ) : (
            <StripCell label="Categoría">
              <Empty />
            </StripCell>
          )}
          {/* F. Creación */}
          <StripCell label="F. Creación">
            {editing && isRisk ? (
              <Input
                type="date"
                value={draft.identified_at}
                onChange={(e) =>
                  setDraft({ ...draft, identified_at: e.target.value })
                }
              />
            ) : editing && !isRisk ? (
              <Input
                type="date"
                value={draft.reported_at}
                onChange={(e) =>
                  setDraft({ ...draft, reported_at: e.target.value })
                }
              />
            ) : (
              fmtDate(
                isRisk
                  ? (risk as Risk).identified_at
                  : (issue as Issue).reported_at,
              ) ?? <Empty />
            )}
          </StripCell>
          {/* F. Compromiso / Resolución / Vigencia */}
          <StripCell
            label={
              raidType === "incident"
                ? "F. Resolución"
                : raidType === "decision"
                  ? "F. Vigencia"
                  : "F. Compromiso"
            }
          >
            {editing && isRisk ? (
              <Input
                type="date"
                value={draft.due_date}
                onChange={(e) => setDraft({ ...draft, due_date: e.target.value })}
              />
            ) : editing && !isRisk ? (
              <Input
                type="date"
                value={draft.committed_date}
                onChange={(e) =>
                  setDraft({ ...draft, committed_date: e.target.value })
                }
              />
            ) : (
              fmtDate(
                isRisk
                  ? (risk as Risk).due_date
                  : (issue as Issue).committed_date,
              ) ?? <Empty />
            )}
          </StripCell>
        </div>
      </section>

      {/* ENH-069: banner modo edición + Cancelar/Guardar */}
      {editing ? (
        <section className="flex items-center justify-between gap-3 rounded-[var(--radius-xl)] border border-[var(--info-border,_var(--border-default))] bg-[var(--info-bg,_var(--color-subtle))] px-[18px] py-2.5">
          <p className="text-[13px] text-[var(--info-fg,_var(--color-primary))]">
            Modo edición activo.
          </p>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={cancelEdit}
              disabled={saving}
            >
              Cancelar
            </Button>
            <Button type="button" size="sm" onClick={saveEdit} loading={saving}>
              Guardar
            </Button>
          </div>
        </section>
      ) : null}

      {editError ? <Banner variant="danger">{editError}</Banner> : null}

      {/* Card Descripción */}
      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="border-b border-[var(--border-default)] px-4 py-2.5">
          <h2 className="text-[13px] font-semibold text-[var(--color-primary)]">
            Descripción
          </h2>
        </header>
        <div className="px-4 py-3">
          {editing ? (
            <Textarea
              value={draft.description}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              rows={4}
            />
          ) : item.description ? (
            <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
              {item.description}
            </p>
          ) : (
            <p className="text-[13px] italic text-[var(--color-tertiary)]">
              Sin descripción.
            </p>
          )}
          {/* Mitigation strategy / Resolution editables en edit mode */}
          {editing && isRisk ? (
            <div className="mt-3">
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                Estrategia de mitigación
              </label>
              <Textarea
                value={draft.mitigation_strategy}
                onChange={(e) =>
                  setDraft({ ...draft, mitigation_strategy: e.target.value })
                }
                rows={2}
              />
            </div>
          ) : isRisk && (risk as Risk).mitigation_strategy ? (
            <div className="mt-3">
              <h3 className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                Estrategia de mitigación
              </h3>
              <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
                {(risk as Risk).mitigation_strategy}
              </p>
            </div>
          ) : null}
          {editing && !isRisk ? (
            <div className="mt-3">
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                Resolución
              </label>
              <Textarea
                value={draft.resolution}
                onChange={(e) => setDraft({ ...draft, resolution: e.target.value })}
                rows={2}
              />
            </div>
          ) : !isRisk && (issue as Issue).resolution ? (
            <div className="mt-3">
              <h3 className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                Resolución
              </h3>
              <p className="whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
                {(issue as Issue).resolution}
              </p>
            </div>
          ) : null}
          {editing && isRisk ? (
            <div className="mt-3">
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                Nota de cierre (opcional)
              </label>
              <Textarea
                value={draft.closure_note}
                onChange={(e) =>
                  setDraft({ ...draft, closure_note: e.target.value })
                }
                rows={2}
                placeholder="Solo aplica si el estado pasa a Cerrado o Materializado"
              />
            </div>
          ) : null}
        </div>
      </section>

      {/* ENH-083: Card Acciones de mitigación (solo en riesgos) */}
      {isRisk && risk ? <RiskActionsCard riskId={risk.id} /> : null}

      {/* Card Proyecto */}
      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="border-b border-[var(--border-default)] px-4 py-2.5">
          <h2 className="text-[13px] font-semibold text-[var(--color-primary)]">
            Proyecto
          </h2>
        </header>
        <div className="flex items-center gap-2 px-4 py-3 text-[13px]">
          <Link
            href={`/pmo/projects/${item.project_id}`}
            className="font-mono text-[12px] text-[var(--color-accent)] underline-offset-2 hover:underline"
          >
            {item.project_id.slice(0, 8)}…
          </Link>
        </div>
      </section>

      {/* ENH-070: Card Comentarios + Historial unificada */}
      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <header className="border-b border-[var(--border-default)] px-4 py-2.5">
          <h2 className="text-[13px] font-semibold text-[var(--color-primary)]">
            Comentarios &amp; Historial
          </h2>
        </header>
        <div className="grid gap-5 px-4 py-3 md:grid-cols-2">
          {/* Comentarios */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
              Comentarios
            </h3>
            <CommentList
              comments={
                isRisk
                  ? (risk as Risk).comments ?? []
                  : (issue as Issue).comments ?? []
              }
              users={users}
            />
            <div className="space-y-2">
              <Textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                rows={2}
                placeholder="Agregar un comentario…"
              />
              <div className="flex justify-end">
                <Button
                  type="button"
                  size="sm"
                  onClick={postComment}
                  loading={postingComment}
                  disabled={!commentText.trim()}
                >
                  Agregar
                </Button>
              </div>
            </div>
          </div>
          {/* Historial */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
              Historial de cambios
            </h3>
            {history.length === 0 ? (
              <p className="text-[12px] italic text-[var(--color-tertiary)]">
                Sin eventos registrados.
              </p>
            ) : (
              <ol className="space-y-1 text-[12px]">
                {history.map((h) => (
                  <li
                    key={h.id}
                    className="flex flex-wrap items-baseline gap-2 border-b border-[var(--border-subtle)] pb-1 last:border-b-0"
                  >
                    <span className="font-mono text-[11px] text-[var(--color-tertiary)]">
                      {new Date(h.occurred_at).toLocaleString("es-MX", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </span>
                    <span className="text-[var(--color-tertiary)]">·</span>
                    <span className="font-medium text-[var(--color-primary)]">
                      {h.action}
                    </span>
                    {h.user_id ? (
                      <>
                        <span className="text-[var(--color-tertiary)]">·</span>
                        <span className="text-[11px] text-[var(--color-secondary)]">
                          {(() => {
                            const u = users.find((x) => x.id === h.user_id);
                            return u
                              ? u.full_name?.trim() || u.email
                              : (h.user_id as string).slice(0, 8);
                          })()}
                        </span>
                      </>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </section>

      <Modal
        open={confirmDelete}
        onClose={() => !deleting && setConfirmDelete(false)}
        title="¿Borrar ítem?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden /> Borrar
            </Button>
          </>
        }
      >
        <p className="text-[13px] text-[var(--color-primary)]">
          ¿Borrar <strong>{item.folio}</strong>? Esta acción lo retira de la
          lista RAID y no se puede deshacer.
        </p>
      </Modal>
    </div>
  );
}

function StripCell({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
        {label}
      </p>
      <div className="mt-0.5 break-words text-[13px] text-[var(--color-primary)]">
        {children}
      </div>
    </div>
  );
}

function Empty() {
  return <span className="text-[var(--color-tertiary)]">—</span>;
}

function CommentList({
  comments,
  users,
}: {
  comments: { text: string; author_id?: string; created_at?: string }[];
  users: { id: string; full_name: string; email: string }[];
}) {
  if (comments.length === 0) {
    return (
      <p className="text-[12px] italic text-[var(--color-tertiary)]">
        Sin comentarios todavía.
      </p>
    );
  }
  // ENH-070 fix: lookup id → nombre completo o email; fallback al
  // user_id mono cortado si el usuario no está en la lista cargada.
  const userById = new Map(users.map((u) => [u.id, u]));
  function authorLabel(id?: string): string {
    if (!id) return "—";
    const u = userById.get(id);
    if (u) return u.full_name?.trim() || u.email;
    return id.slice(0, 8);
  }
  return (
    <ol className="space-y-2 text-[12px]">
      {comments.map((c, i) => (
        <li
          key={i}
          className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-2 py-1.5"
        >
          <div className="flex items-baseline gap-2 text-[11px] text-[var(--color-tertiary)]">
            {c.author_id ? (
              <span className="font-medium text-[var(--color-secondary)]">
                {authorLabel(c.author_id)}
              </span>
            ) : null}
            {c.created_at ? (
              <span className="font-mono">
                {new Date(c.created_at).toLocaleString("es-MX", {
                  dateStyle: "short",
                  timeStyle: "short",
                })}
              </span>
            ) : null}
          </div>
          <p className="mt-0.5 whitespace-pre-wrap text-[13px] text-[var(--color-primary)]">
            {c.text}
          </p>
        </li>
      ))}
    </ol>
  );
}

function raidStatusVariant(
  status: "identified" | "analyzing" | "mitigating" | "materialized" | "closed",
): "info" | "success" | "danger" | "neutral" {
  if (status === "identified" || status === "analyzing") return "info";
  if (status === "mitigating") return "info";
  if (status === "materialized") return "danger";
  if (status === "closed") return "neutral";
  return "neutral";
}

function issueStatusVariant(
  status: "open" | "in_progress" | "resolved" | "closed",
): "info" | "success" | "danger" | "neutral" {
  if (status === "open" || status === "in_progress") return "info";
  if (status === "resolved") return "success";
  if (status === "closed") return "neutral";
  return "neutral";
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
