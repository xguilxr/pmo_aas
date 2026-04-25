"use client";

import { useEffect, useState } from "react";
import { Pencil, X } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import { listUsers } from "@/lib/api/admin";
import {
  type Issue,
  type Risk,
  updateIssue,
  updateRisk,
} from "@/lib/api/modules";
import { listProjectAreas, type ProjectArea } from "@/lib/api/project-areas";

/**
 * ENH-036 — formulario inline de edición completa para items RAID en
 * la página detail (`/pmo/projects/[id]/raid/[item_id]` y similares).
 *
 * Antes la página solo permitía cambiar status + agregar comentarios
 * (vía RaidDetailBody). Owner pidió editar área, responsable y otros
 * campos directamente desde la página detalle.
 *
 * Modo lectura por default (sólo botón "Editar"). Modo edición expone
 * inputs para title, description, area_id, owner_id, due/committed
 * date, mitigation_strategy/resolution + Probability/Impact (risks)
 * o Priority (issues).
 *
 * Permisos: requiere `raid:update` o `raid:write` (capability gate).
 */

type RaidUserOption = { id: string; full_name: string; email: string };

type SaveResult<T> = (next: T) => void;

export function RaidEditFields(props:
  | {
      kind: "risk";
      item: Risk;
      onSaved: SaveResult<Risk>;
    }
  | {
      kind: "issue";
      item: Issue;
      onSaved: SaveResult<Issue>;
    },
) {
  const { kind, item, onSaved } = props;
  const { has } = useMyPermissions();
  const canEdit = has("raid:update") || has("raid:write");

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [areas, setAreas] = useState<ProjectArea[]>([]);
  const [users, setUsers] = useState<RaidUserOption[]>([]);
  const [optsLoading, setOptsLoading] = useState(false);

  // Local form state — initialized from `item` when entering edit mode.
  const [title, setTitle] = useState(item.title);
  const [description, setDescription] = useState(item.description ?? "");
  const [areaId, setAreaId] = useState(item.area_id ?? "");
  const [ownerId, setOwnerId] = useState(item.owner_id ?? "");
  const [riskProb, setRiskProb] = useState<number>(
    kind === "risk" ? item.probability ?? 1 : 1,
  );
  const [riskImpact, setRiskImpact] = useState<number>(
    kind === "risk" ? item.impact ?? 1 : 1,
  );
  const [riskMitigation, setRiskMitigation] = useState(
    kind === "risk" ? item.mitigation_strategy ?? "" : "",
  );
  const [riskDue, setRiskDue] = useState(
    kind === "risk" ? item.due_date ?? "" : "",
  );
  const [riskIdentified, setRiskIdentified] = useState(
    kind === "risk" ? item.identified_at ?? "" : "",
  );
  const [issuePriority, setIssuePriority] = useState<number | "">(
    kind === "issue" ? item.priority ?? "" : "",
  );
  const [issueCommitted, setIssueCommitted] = useState(
    kind === "issue" ? item.committed_date ?? "" : "",
  );
  const [issueResolution, setIssueResolution] = useState(
    kind === "issue" ? item.resolution ?? "" : "",
  );

  useEffect(() => {
    if (!editing) return;
    let cancelled = false;
    setOptsLoading(true);
    Promise.all([
      listProjectAreas(item.project_id, { is_active: true }),
      listUsers({ is_active: true, page: 1, limit: 200 }).catch(() => ({
        items: [] as { id: string; full_name?: string | null; email: string }[],
      })),
    ])
      .then(([areaRows, usersResp]) => {
        if (cancelled) return;
        setAreas(areaRows);
        const userRows = (usersResp as { items: { id: string; full_name?: string | null; email: string }[] }).items;
        setUsers(
          userRows.map((u) => ({
            id: u.id,
            full_name: u.full_name ?? "",
            email: u.email,
          })),
        );
      })
      .catch(() => {
        /* non-fatal — selects quedan vacíos */
      })
      .finally(() => {
        if (!cancelled) setOptsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [editing, item.project_id]);

  function reset() {
    setTitle(item.title);
    setDescription(item.description ?? "");
    setAreaId(item.area_id ?? "");
    setOwnerId(item.owner_id ?? "");
    if (kind === "risk") {
      setRiskProb(item.probability ?? 1);
      setRiskImpact(item.impact ?? 1);
      setRiskMitigation(item.mitigation_strategy ?? "");
      setRiskDue(item.due_date ?? "");
      setRiskIdentified(item.identified_at ?? "");
    } else {
      setIssuePriority(item.priority ?? "");
      setIssueCommitted(item.committed_date ?? "");
      setIssueResolution(item.resolution ?? "");
    }
    setError(null);
  }

  async function save() {
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      if (kind === "risk") {
        const body: Parameters<typeof updateRisk>[1] = {
          title: title.trim(),
          description: description.trim() || null,
          area_id: areaId || undefined,
          owner_id: ownerId || null,
          probability: riskProb,
          impact: riskImpact,
          mitigation_strategy: riskMitigation.trim() || null,
          identified_at: riskIdentified || null,
          due_date: riskDue || null,
        };
        const updated = await updateRisk(item.id, body);
        onSaved(updated);
      } else {
        const body: Parameters<typeof updateIssue>[1] = {
          title: title.trim(),
          description: description.trim() || null,
          area_id: areaId || undefined,
          owner_id: ownerId || null,
          priority: issuePriority === "" ? null : Number(issuePriority),
          committed_date: issueCommitted || null,
          resolution: issueResolution.trim() || null,
        };
        const updated = await updateIssue(item.id, body);
        onSaved(updated);
      }
      setEditing(false);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo guardar los cambios",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    if (!canEdit) return null;
    return (
      <div className="flex justify-end">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            reset();
            setEditing(true);
          }}
        >
          <Pencil className="mr-1 h-3.5 w-3.5" aria-hidden />
          Editar campos
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
          Modo edición
        </p>
        <button
          type="button"
          onClick={() => {
            reset();
            setEditing(false);
          }}
          className="text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
          aria-label="Cancelar edición"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <Field label="Título">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          minLength={2}
          required
        />
      </Field>

      <Field label="Descripción">
        <Textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Área responsable">
          <Select
            value={areaId}
            onChange={(e) => setAreaId(e.target.value)}
            disabled={optsLoading}
          >
            <option value="">— sin área —</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Responsable">
          <Select
            value={ownerId}
            onChange={(e) => setOwnerId(e.target.value)}
            disabled={optsLoading}
          >
            <option value="">— sin responsable —</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name?.trim() || u.email}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {kind === "risk" ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Fecha identificado">
              <Input
                type="date"
                value={riskIdentified}
                onChange={(e) => setRiskIdentified(e.target.value)}
              />
            </Field>
            <Field label="Fecha compromiso">
              <Input
                type="date"
                value={riskDue}
                onChange={(e) => setRiskDue(e.target.value)}
              />
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Probabilidad (1-5)">
              <Input
                type="number"
                min={1}
                max={5}
                value={riskProb}
                onChange={(e) => setRiskProb(Number(e.target.value))}
              />
            </Field>
            <Field label="Impacto (1-5)">
              <Input
                type="number"
                min={1}
                max={5}
                value={riskImpact}
                onChange={(e) => setRiskImpact(Number(e.target.value))}
              />
            </Field>
          </div>
          <Field label="Estrategia de mitigación">
            <Textarea
              value={riskMitigation}
              onChange={(e) => setRiskMitigation(e.target.value)}
              rows={2}
            />
          </Field>
        </>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Prioridad (1-5)">
              <Input
                type="number"
                min={1}
                max={5}
                value={issuePriority}
                onChange={(e) =>
                  setIssuePriority(
                    e.target.value === "" ? "" : Number(e.target.value),
                  )
                }
              />
            </Field>
            <Field label="Fecha compromiso">
              <Input
                type="date"
                value={issueCommitted}
                onChange={(e) => setIssueCommitted(e.target.value)}
              />
            </Field>
          </div>
          <Field label="Resolución">
            <Textarea
              value={issueResolution}
              onChange={(e) => setIssueResolution(e.target.value)}
              rows={2}
            />
          </Field>
        </>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            reset();
            setEditing(false);
          }}
          disabled={saving}
        >
          Cancelar
        </Button>
        <Button type="button" size="sm" onClick={save} loading={saving}>
          Guardar
        </Button>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
        {label}
      </label>
      {children}
    </div>
  );
}
