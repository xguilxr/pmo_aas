"use client";

/**
 * ENH-083 — Card "Acciones de mitigación" inline en raid-detail-page (riesgo).
 * Lista las acciones de US-107 con add/edit/delete inline.
 *
 * UI:
 * - Empty state con CTA "Agregar primera acción".
 * - Cada acción: short desc + chips de actores responsables + fecha + status badge.
 * - Edit inline: short_desc, due_date, status, assignees (multi-select chips).
 *
 * Status del Riesgo NO se toca; cada acción tiene su propio ciclo (CA6 US-107).
 */
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import type { Actor } from "@/lib/api/areas";
import { listActors } from "@/lib/api/areas";
import { confirmarDestructivo } from "@/lib/confirmar";
import {
  RISK_ACTION_STATUS,
  RISK_ACTION_STATUS_LABEL,
  type RiskAction,
  type RiskActionStatus,
  createRiskAction,
  deleteRiskAction,
  listRiskActions,
  updateRiskAction,
} from "@/lib/api/risk-actions";

type EditDraft = {
  short_desc: string;
  due_date: string;
  status: RiskActionStatus;
  assignee_actor_ids: string[];
};

const EMPTY_DRAFT: EditDraft = {
  short_desc: "",
  due_date: "",
  status: "open",
  assignee_actor_ids: [],
};

const STATUS_BADGE_VARIANT: Record<
  RiskActionStatus,
  "info" | "warning" | "success" | "danger"
> = {
  open: "info",
  in_progress: "warning",
  done: "success",
  blocked: "danger",
};

export function RiskActionsCard({ riskId }: { riskId: string }) {
  const [actions, setActions] = useState<RiskAction[]>([]);
  const [actors, setActors] = useState<Actor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [creating, setCreating] = useState(false);
  const [createDraft, setCreateDraft] = useState<EditDraft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);

  const actorById = useMemo(() => {
    const map = new Map<string, Actor>();
    actors.forEach((a) => map.set(a.id, a));
    return map;
  }, [actors]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [list, actorList] = await Promise.all([
        listRiskActions(riskId),
        listActors({}).catch(() => [] as Actor[]),
      ]);
      setActions(list);
      setActors(actorList);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las acciones");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [riskId]);

  async function submitCreate() {
    if (!createDraft.short_desc.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createRiskAction(riskId, {
        short_desc: createDraft.short_desc.trim(),
        due_date: createDraft.due_date || null,
        status: createDraft.status,
        assignee_actor_ids: createDraft.assignee_actor_ids,
      });
      setCreating(false);
      setCreateDraft(EMPTY_DRAFT);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la acción");
    } finally {
      setBusy(false);
    }
  }

  function startEdit(a: RiskAction) {
    setEditingId(a.id);
    setEditDraft({
      short_desc: a.short_desc,
      due_date: a.due_date ?? "",
      status: a.status,
      assignee_actor_ids: a.assignee_actor_ids,
    });
  }

  async function submitEdit() {
    if (!editingId || !editDraft.short_desc.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await updateRiskAction(editingId, {
        short_desc: editDraft.short_desc.trim(),
        due_date: editDraft.due_date || null,
        status: editDraft.status,
        assignee_actor_ids: editDraft.assignee_actor_ids,
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la acción");
    } finally {
      setBusy(false);
    }
  }

  async function remove(a: RiskAction) {
    if (
      !confirmarDestructivo({
        objeto: `la acción «${a.short_desc}»`,
        consecuencia: "El riesgo se queda sin ese plan de mitigación.",
        reversibilidad: "recuperable",
      })
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await deleteRiskAction(a.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar la acción");
    } finally {
      setBusy(false);
    }
  }

  function toggleAssignee(draft: EditDraft, actorId: string): EditDraft {
    const set = new Set(draft.assignee_actor_ids);
    if (set.has(actorId)) set.delete(actorId);
    else set.add(actorId);
    return { ...draft, assignee_actor_ids: Array.from(set) };
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <header className="flex items-center justify-between border-b border-[var(--border-default)] px-4 py-2.5">
        <h2 className="text-[13px] font-semibold text-[var(--color-primary)]">
          Acciones de mitigación
        </h2>
        {!creating && actions.length > 0 ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setCreating(true);
              setCreateDraft(EMPTY_DRAFT);
            }}
          >
            <Icono nombre="plus" size={15} /> Agregar
          </Button>
        ) : null}
      </header>

      <div className="space-y-2 px-4 py-3">
        {error ? <Banner variant="danger">{error}</Banner> : null}

        {loading ? (
          <p className="text-[13px] text-[var(--color-tertiary)]">Cargando…</p>
        ) : actions.length === 0 && !creating ? (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <Icono nombre="clock" size={20} className="text-[var(--color-tertiary)]" />
            <p className="text-[13px] text-[var(--color-tertiary)]">
              Sin acciones de mitigación todavía.
            </p>
            <Button
              size="sm"
              onClick={() => {
                setCreating(true);
                setCreateDraft(EMPTY_DRAFT);
              }}
            >
              <Icono nombre="plus" size={15} /> Agregar primera acción
            </Button>
          </div>
        ) : null}

        {actions.map((a) =>
          editingId === a.id ? (
            <div
              key={a.id}
              className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-2.5"
            >
              <Textarea
                rows={2}
                value={editDraft.short_desc}
                onChange={(e) =>
                  setEditDraft({ ...editDraft, short_desc: e.target.value })
                }
                placeholder="Descripción corta de la acción"
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="date"
                  value={editDraft.due_date}
                  onChange={(e) =>
                    setEditDraft({ ...editDraft, due_date: e.target.value })
                  }
                />
                <Select
                  value={editDraft.status}
                  onChange={(e) =>
                    setEditDraft({
                      ...editDraft,
                      status: e.target.value as RiskActionStatus,
                    })
                  }
                >
                  {RISK_ACTION_STATUS.map((s) => (
                    <option key={s} value={s}>
                      {RISK_ACTION_STATUS_LABEL[s]}
                    </option>
                  ))}
                </Select>
              </div>
              <AssigneePicker
                actors={actors}
                selected={editDraft.assignee_actor_ids}
                onToggle={(id) => setEditDraft(toggleAssignee(editDraft, id))}
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setEditingId(null)}
                  disabled={busy}
                >
                  <Icono nombre="x" size={15} /> Cancelar
                </Button>
                <Button size="sm" onClick={submitEdit} loading={busy}>
                  <Icono nombre="circle-check" size={15} /> Guardar
                </Button>
              </div>
            </div>
          ) : (
            <ActionRow
              key={a.id}
              action={a}
              actorById={actorById}
              onEdit={() => startEdit(a)}
              onDelete={() => remove(a)}
            />
          ),
        )}

        {creating ? (
          <div className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-2.5">
            <Textarea
              rows={2}
              value={createDraft.short_desc}
              onChange={(e) =>
                setCreateDraft({ ...createDraft, short_desc: e.target.value })
              }
              placeholder="Descripción corta de la acción"
            />
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="date"
                value={createDraft.due_date}
                onChange={(e) =>
                  setCreateDraft({ ...createDraft, due_date: e.target.value })
                }
              />
              <Select
                value={createDraft.status}
                onChange={(e) =>
                  setCreateDraft({
                    ...createDraft,
                    status: e.target.value as RiskActionStatus,
                  })
                }
              >
                {RISK_ACTION_STATUS.map((s) => (
                  <option key={s} value={s}>
                    {RISK_ACTION_STATUS_LABEL[s]}
                  </option>
                ))}
              </Select>
            </div>
            <AssigneePicker
              actors={actors}
              selected={createDraft.assignee_actor_ids}
              onToggle={(id) =>
                setCreateDraft(toggleAssignee(createDraft, id))
              }
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setCreating(false);
                  setCreateDraft(EMPTY_DRAFT);
                }}
                disabled={busy}
              >
                <Icono nombre="x" size={15} /> Cancelar
              </Button>
              <Button
                size="sm"
                onClick={submitCreate}
                loading={busy}
                disabled={!createDraft.short_desc.trim()}
              >
                <Icono nombre="plus" size={15} /> Crear
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function ActionRow({
  action,
  actorById,
  onEdit,
  onDelete,
}: {
  action: RiskAction;
  actorById: Map<string, Actor>;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2.5">
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-[13px] text-[var(--color-primary)]">{action.short_desc}</p>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--color-tertiary)]">
          <Badge variant={STATUS_BADGE_VARIANT[action.status]}>
            {RISK_ACTION_STATUS_LABEL[action.status]}
          </Badge>
          {action.due_date ? (
            <span className="font-mono">Vence {action.due_date}</span>
          ) : null}
          <div className="flex flex-wrap gap-1">
            {action.assignee_actor_ids.length === 0 ? (
              <span className="italic">Sin responsables</span>
            ) : (
              action.assignee_actor_ids.map((id) => {
                const actor = actorById.get(id);
                return (
                  <span
                    key={id}
                    className="rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] px-2 py-0.5 text-[11px] text-[var(--color-secondary)]"
                  >
                    {actor?.name ?? id.slice(0, 6)}
                  </span>
                );
              })
            )}
          </div>
        </div>
      </div>
      <div className="flex shrink-0 gap-1">
        <button
          type="button"
          onClick={onEdit}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          aria-label="Editar acción"
        >
          <Icono nombre="pen" size={15} />
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
          aria-label="Borrar acción"
        >
          <Icono nombre="bin" size={15} />
        </button>
      </div>
    </div>
  );
}

function AssigneePicker({
  actors,
  selected,
  onToggle,
}: {
  actors: Actor[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  if (actors.length === 0) {
    return (
      <p className="text-[11px] italic text-[var(--color-tertiary)]">
        No hay actores disponibles. Crea actores en /admin/areas.
      </p>
    );
  }
  const set = new Set(selected);
  return (
    <div className="space-y-1">
      <p className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--color-tertiary)]">
        Responsables
      </p>
      <div className="flex flex-wrap gap-1">
        {actors
          .filter((a) => a.is_active)
          .map((a) => {
            const active = set.has(a.id);
            return (
              <button
                key={a.id}
                type="button"
                onClick={() => onToggle(a.id)}
                className={
                  "rounded-full border px-2 py-0.5 text-[11px] transition-colors " +
                  (active
                    ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-inverse)]"
                    : "border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]")
                }
              >
                {a.name}
              </button>
            );
          })}
      </div>
    </div>
  );
}
