"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Check, ExternalLink, Pencil, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  approveMinuteRaidSuggestions,
  updateMinute,
  type MeetingMinute,
  type MinuteRaidSuggestion,
  type MinuteRaidSuggestions,
  type RaidApproveItem,
} from "@/lib/api/modules";

/**
 * US-108 — editor de sugerencias RAID detectadas por la IA en la minuta.
 *
 * El PM revisa cada sugerencia y puede:
 * - editar `short_desc`, prioridad o owner sugerido
 * - descartar la sugerencia (×) — persiste como `discarded` para auditoría (CA6)
 * - aprobar (✓) — al confirmar bulk, se crean los tickets reales en
 *   los módulos correspondientes (CA4) y aparecen como links en la
 *   misma fila (CA5).
 *
 * Usa `MeetingMinute.raid_suggestions` como single source of truth y
 * persiste los cambios vía PATCH (descartes/edits) o POST
 * `/approve-raid-suggestions` (creación bulk).
 */

type BucketKey = "actions" | "risks" | "decisions" | "issues" | "lessons" | "changes";

type SectionMeta = {
  key: BucketKey;
  label: string;
  ticketBase: string;
  emptyHint: string;
};

// BUG-063: 4 buckets canónicos A/R/D/I + 2 legacy (lessons/changes)
// para retro-compat con minutas pre-refactor.
const SECTION_META: SectionMeta[] = [
  {
    key: "actions",
    label: "Acciones",
    ticketBase: "raid",
    emptyHint: "Sin acciones detectadas.",
  },
  {
    key: "risks",
    label: "Riesgos",
    ticketBase: "raid",
    emptyHint: "Sin riesgos detectados.",
  },
  {
    key: "decisions",
    label: "Decisiones",
    ticketBase: "raid",
    emptyHint: "Sin decisiones detectadas.",
  },
  {
    key: "issues",
    label: "Issues",
    ticketBase: "raid",
    emptyHint: "Sin issues detectados.",
  },
  {
    key: "lessons",
    label: "Lecciones (legacy)",
    ticketBase: "lessons",
    emptyHint: "Sin lecciones.",
  },
  {
    key: "changes",
    label: "Cambios (legacy)",
    ticketBase: "changes",
    emptyHint: "Sin cambios.",
  },
];

type ResolvedSuggestions = Required<
  Pick<MinuteRaidSuggestions, "actions" | "risks" | "decisions" | "issues">
> & {
  lessons: MinuteRaidSuggestion[];
  changes: MinuteRaidSuggestion[];
};

function emptySuggestions(): ResolvedSuggestions {
  return { actions: [], risks: [], decisions: [], issues: [], lessons: [], changes: [] };
}

function sanitizeSuggestions(
  src: Partial<MinuteRaidSuggestions> | undefined,
): ResolvedSuggestions {
  const base = emptySuggestions();
  if (!src) return base;
  for (const meta of SECTION_META) {
    const items = (src as Record<string, MinuteRaidSuggestion[] | undefined>)[meta.key] ?? [];
    base[meta.key] = items.map((s) => ({
      short_desc: s.short_desc ?? "",
      suggested_owner_name: s.suggested_owner_name ?? null,
      suggested_priority: s.suggested_priority ?? null,
      suggested_due_date: s.suggested_due_date ?? null,
      raw_quote: s.raw_quote ?? null,
      status: s.status ?? "pending",
      ticket_id: s.ticket_id ?? null,
      ticket_type: s.ticket_type ?? null,
    }));
  }
  return base;
}

function ticketHref(
  meta: SectionMeta,
  projectId: string,
  s: MinuteRaidSuggestion,
): string | null {
  if (!s.ticket_id) return null;
  // BUG-063: Risk vive en `?type=risk`; Acción/Decisión/Issue son todos
  // sub-tipos de `issues` con `type` en el ticket — uso `?type=incident`
  // como fallback (la pantalla detail discrimina por ticket.type).
  if (meta.key === "risks") {
    return `/pmo/projects/${projectId}/raid/${s.ticket_id}?type=risk`;
  }
  if (meta.key === "actions" || meta.key === "decisions" || meta.key === "issues") {
    return `/pmo/projects/${projectId}/raid/${s.ticket_id}?type=incident`;
  }
  if (meta.key === "lessons") {
    return `/pmo/projects/${projectId}/lessons/${s.ticket_id}`;
  }
  return `/pmo/projects/${projectId}/changes/${s.ticket_id}`;
}

export function MinuteRaidSuggestionsEditor({
  minute,
  onMinuteChanged,
}: {
  minute: MeetingMinute;
  onMinuteChanged?: (next: MeetingMinute) => void;
}) {
  const [suggestions, setSuggestions] = useState<ResolvedSuggestions>(() =>
    sanitizeSuggestions(minute.raid_suggestions),
  );
  const [draft, setDraft] = useState<{
    type: BucketKey;
    index: number;
    short_desc: string;
    priority: string;
    owner: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<"discard" | "edit" | "approve" | null>(
    null,
  );

  const counts = useMemo(() => {
    const totals = { pending: 0, approved: 0, discarded: 0 };
    for (const meta of SECTION_META) {
      for (const s of suggestions[meta.key]) {
        totals[s.status]++;
      }
    }
    return totals;
  }, [suggestions]);

  function updateLocal(next: ResolvedSuggestions) {
    setSuggestions(next);
  }

  async function persist(next: ResolvedSuggestions) {
    try {
      const updated = await updateMinute(minute.id, { raid_suggestions: next });
      onMinuteChanged?.(updated);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo guardar el cambio en la minuta",
      );
      // Revert local state to last known server value
      setSuggestions(sanitizeSuggestions(minute.raid_suggestions));
    }
  }

  async function handleDiscard(
    type: BucketKey,
    index: number,
  ) {
    const next = sanitizeSuggestions(suggestions);
    next[type][index] = { ...next[type][index], status: "discarded" };
    updateLocal(next);
    setSaving("discard");
    setError(null);
    await persist(next);
    setSaving(null);
  }

  function startEdit(
    type: BucketKey,
    index: number,
    s: MinuteRaidSuggestion,
  ) {
    setDraft({
      type,
      index,
      short_desc: s.short_desc,
      priority: s.suggested_priority != null ? String(s.suggested_priority) : "",
      owner: s.suggested_owner_name ?? "",
    });
  }

  async function commitEdit() {
    if (!draft) return;
    if (!draft.short_desc.trim()) {
      setError("`short_desc` no puede quedar vacío.");
      return;
    }
    setSaving("edit");
    setError(null);
    const next = sanitizeSuggestions(suggestions);
    const item = { ...next[draft.type][draft.index] };
    item.short_desc = draft.short_desc.trim();
    item.suggested_owner_name = draft.owner.trim() || null;
    const p = parseInt(draft.priority, 10);
    item.suggested_priority = Number.isFinite(p) && p >= 1 && p <= 5 ? p : null;
    next[draft.type][draft.index] = item;
    updateLocal(next);
    await persist(next);
    setDraft(null);
    setSaving(null);
  }

  async function approveAll() {
    const items: RaidApproveItem[] = [];
    for (const meta of SECTION_META) {
      suggestions[meta.key].forEach((s, idx) => {
        if (s.status === "pending") {
          items.push({
            type: meta.key,
            index: idx,
            short_desc: s.short_desc,
            priority: s.suggested_priority ?? undefined,
          });
        }
      });
    }
    if (items.length === 0) {
      setError("No hay sugerencias pendientes para aprobar.");
      return;
    }
    setSaving("approve");
    setError(null);
    try {
      const updated = await approveMinuteRaidSuggestions(minute.id, items);
      setSuggestions(sanitizeSuggestions(updated.raid_suggestions));
      onMinuteChanged?.(updated);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudieron crear los tickets",
      );
    } finally {
      setSaving(null);
    }
  }

  async function approveOne(
    type: BucketKey,
    index: number,
  ) {
    setSaving("approve");
    setError(null);
    try {
      const updated = await approveMinuteRaidSuggestions(minute.id, [
        {
          type,
          index,
          short_desc: suggestions[type][index].short_desc,
          priority: suggestions[type][index].suggested_priority ?? undefined,
        },
      ]);
      setSuggestions(sanitizeSuggestions(updated.raid_suggestions));
      onMinuteChanged?.(updated);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo crear el ticket",
      );
    } finally {
      setSaving(null);
    }
  }

  const total =
    suggestions.actions.length +
    suggestions.risks.length +
    suggestions.decisions.length +
    suggestions.issues.length +
    suggestions.lessons.length +
    suggestions.changes.length;

  if (total === 0) {
    return (
      <section className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-4">
        <h3 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Sugerencias RAID detectadas
        </h3>
        <p className="mt-2 text-[12px] italic text-[var(--text-tertiary)]">
          La IA no detectó items RAID en esta minuta.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-3 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Sugerencias RAID detectadas
          </h3>
          <p className="text-[11px] text-[var(--text-tertiary)]">
            {counts.pending} pendientes · {counts.approved} aprobadas ·{" "}
            {counts.discarded} descartadas
          </p>
        </div>
        <Button
          size="sm"
          onClick={approveAll}
          disabled={counts.pending === 0}
          loading={saving === "approve"}
        >
          Crear items RAID pendientes ({counts.pending})
        </Button>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <div className="space-y-3">
        {SECTION_META.map((meta) => {
          const items = suggestions[meta.key];
          if (items.length === 0) return null;
          return (
            <details
              key={meta.key}
              open
              className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)]/40 p-3"
            >
              <summary className="flex cursor-pointer items-center justify-between text-[12px] font-medium text-[var(--text-primary)]">
                <span>{meta.label}</span>
                <Badge variant="info">{items.length}</Badge>
              </summary>
              <ul className="mt-2 space-y-2">
                {items.map((s, idx) => {
                  const isEditing =
                    draft !== null &&
                    draft.type === meta.key &&
                    draft.index === idx;
                  const href = ticketHref(meta, minute.project_id, s);
                  return (
                    <li
                      key={idx}
                      className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--color-surface)] px-3 py-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1 space-y-1">
                          {isEditing && draft ? (
                            <>
                              <Input
                                value={draft.short_desc}
                                onChange={(e) =>
                                  setDraft({ ...draft, short_desc: e.target.value })
                                }
                                placeholder="Descripción corta"
                              />
                              <div className="flex items-center gap-2 text-[11px]">
                                <label className="flex items-center gap-1 text-[var(--text-tertiary)]">
                                  Owner
                                  <Input
                                    value={draft.owner}
                                    onChange={(e) =>
                                      setDraft({ ...draft, owner: e.target.value })
                                    }
                                    placeholder="—"
                                    className="h-7 w-32 text-[11px]"
                                  />
                                </label>
                                <label className="flex items-center gap-1 text-[var(--text-tertiary)]">
                                  P
                                  <Input
                                    type="number"
                                    min={1}
                                    max={5}
                                    value={draft.priority}
                                    onChange={(e) =>
                                      setDraft({ ...draft, priority: e.target.value })
                                    }
                                    className="h-7 w-14 text-[11px]"
                                  />
                                </label>
                              </div>
                            </>
                          ) : (
                            <>
                              <p className="text-[13px] font-medium text-[var(--text-primary)]">
                                {s.short_desc || (
                                  <span className="italic text-[var(--text-tertiary)]">
                                    sin descripción
                                  </span>
                                )}
                              </p>
                              <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                                {s.suggested_owner_name ? (
                                  <span>👤 {s.suggested_owner_name}</span>
                                ) : null}
                                {s.suggested_priority ? (
                                  <span>⚑ P{s.suggested_priority}</span>
                                ) : null}
                                {/* ENH-119: "approved" = item RAID real ya
                                    creado y linkeado. Label "Creado" para
                                    diferenciar del concepto de "aprobación"
                                    legacy. */}
                                {s.status === "approved" ? (
                                  <Badge variant="success">✓ Creado</Badge>
                                ) : s.status === "discarded" ? (
                                  <Badge variant="neutral">Descartado</Badge>
                                ) : (
                                  <Badge variant="info">Pendiente</Badge>
                                )}
                                {href ? (
                                  <Link
                                    href={href}
                                    className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline"
                                  >
                                    <ExternalLink className="h-3 w-3" aria-hidden />
                                    Abrir {s.ticket_type ?? "ticket"}
                                  </Link>
                                ) : null}
                              </div>
                              {s.raw_quote ? (
                                <p className="line-clamp-2 italic text-[11px] text-[var(--text-tertiary)]">
                                  “{s.raw_quote}”
                                </p>
                              ) : null}
                            </>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          {isEditing ? (
                            <>
                              <Button
                                size="sm"
                                variant="primary"
                                onClick={commitEdit}
                                loading={saving === "edit"}
                              >
                                Guardar
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setDraft(null)}
                              >
                                Cancelar
                              </Button>
                            </>
                          ) : s.status === "pending" ? (
                            <>
                              <button
                                type="button"
                                onClick={() => startEdit(meta.key, idx, s)}
                                aria-label="Editar"
                                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
                              >
                                <Pencil className="h-3.5 w-3.5" aria-hidden />
                              </button>
                              <button
                                type="button"
                                onClick={() => approveOne(meta.key, idx)}
                                aria-label="Crear item RAID"
                                title="Crear item RAID a partir de esta sugerencia"
                                disabled={saving !== null}
                                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-success-fg)] hover:bg-[var(--color-success-bg)] disabled:opacity-50"
                              >
                                <Check className="h-3.5 w-3.5" aria-hidden />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDiscard(meta.key, idx)}
                                aria-label="Descartar"
                                disabled={saving !== null}
                                className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-danger-fg)] hover:bg-[var(--color-danger-bg)] disabled:opacity-50"
                              >
                                <X className="h-3.5 w-3.5" aria-hidden />
                              </button>
                            </>
                          ) : null}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </details>
          );
        })}
      </div>
    </section>
  );
}

export function hasRaidSuggestions(
  src: Partial<MinuteRaidSuggestions> | undefined,
): boolean {
  if (!src) return false;
  return (
    (src.actions?.length ?? 0) +
      (src.risks?.length ?? 0) +
      (src.decisions?.length ?? 0) +
      (src.issues?.length ?? 0) +
      (src.lessons?.length ?? 0) +
      (src.changes?.length ?? 0) >
    0
  );
}
