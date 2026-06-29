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
import {
  RAID_STATUS_LABEL,
  type Issue,
  type IssueType,
  type RaidStatus,
  type Risk,
  updateIssue,
  updateRisk,
} from "@/lib/api/modules";
import { listProjectAreas, type ProjectArea } from "@/lib/api/project-areas";
import { ProjectAreaPicker } from "@/components/directory/ProjectAreaPicker";
import { PersonPicker } from "@/components/directory/PersonPicker";

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

type SaveResult<T> = (next: T) => void;

export function RaidEditFields(props:
  | {
      kind: "risk";
      item: Risk;
      onSaved: SaveResult<Risk>;
      /** US-178: arranca en modo edición (para uso en modal). */
      defaultEditing?: boolean;
      /** US-178: si se pasa, cancelar/guardar lo invoca (cierra el modal). */
      onClose?: () => void;
    }
  | {
      kind: "issue";
      item: Issue;
      onSaved: SaveResult<Issue>;
      defaultEditing?: boolean;
      onClose?: () => void;
    },
) {
  const { kind, item, onSaved } = props;
  const onClose = props.onClose;
  const { has } = useMyPermissions();
  const canEdit = has("raid:update") || has("raid:write");

  const [editing, setEditing] = useState(Boolean(props.defaultEditing));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [areas, setAreas] = useState<ProjectArea[]>([]);
  const [optsLoading, setOptsLoading] = useState(false);

  // Local form state — initialized from `item` when entering edit mode.
  const [title, setTitle] = useState(item.title);
  const [description, setDescription] = useState(item.description ?? "");
  const [areaId, setAreaId] = useState(item.area_id ?? "");
  const [ownerActorId, setOwnerActorId] = useState<string>(
    (item as { owner_actor_id?: string | null }).owner_actor_id ?? "",
  );
  // US-179: estado (4) + detención.
  const [status, setStatus] = useState<RaidStatus>(item.status);
  const [onHoldReason, setOnHoldReason] = useState(item.on_hold_reason ?? "");
  const [onHoldAreaId, setOnHoldAreaId] = useState(item.on_hold_area_id ?? "");
  const [onHoldActorId, setOnHoldActorId] = useState(
    item.on_hold_actor_id ?? "",
  );
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
  // ENH-054: campos faltantes — category + closure_note para Risk.
  const [riskCategory, setRiskCategory] = useState(
    kind === "risk" ? item.category ?? "" : "",
  );
  const [riskClosureNote, setRiskClosureNote] = useState(
    kind === "risk" ? item.closure_note ?? "" : "",
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
  // ENH-054: type + reported_at para Issue.
  const [issueType, setIssueType] = useState<IssueType>(
    kind === "issue" ? item.type : "action",
  );
  const [issueReported, setIssueReported] = useState(
    kind === "issue" && item.reported_at
      ? new Date(item.reported_at).toISOString().slice(0, 10)
      : "",
  );

  useEffect(() => {
    if (!editing) return;
    let cancelled = false;
    setOptsLoading(true);
    listProjectAreas(item.project_id, { is_active: true })
      .then((areaRows) => {
        if (!cancelled) setAreas(areaRows);
      })
      .catch(() => {
        /* non-fatal — areas quedan vacías */
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
    setOwnerActorId(
      (item as { owner_actor_id?: string | null }).owner_actor_id ?? "",
    );
    setStatus(item.status);
    setOnHoldReason(item.on_hold_reason ?? "");
    setOnHoldAreaId(item.on_hold_area_id ?? "");
    setOnHoldActorId(item.on_hold_actor_id ?? "");
    if (kind === "risk") {
      setRiskProb(item.probability ?? 1);
      setRiskImpact(item.impact ?? 1);
      setRiskMitigation(item.mitigation_strategy ?? "");
      setRiskDue(item.due_date ?? "");
      setRiskIdentified(item.identified_at ?? "");
      setRiskCategory(item.category ?? "");
      setRiskClosureNote(item.closure_note ?? "");
    } else {
      setIssuePriority(item.priority ?? "");
      setIssueCommitted(item.committed_date ?? "");
      setIssueResolution(item.resolution ?? "");
      setIssueType(item.type);
      setIssueReported(
        item.reported_at
          ? new Date(item.reported_at).toISOString().slice(0, 10)
          : "",
      );
    }
    setError(null);
  }

  async function save() {
    if (saving) return;
    if (title.trim().length < 2) {
      setError("El título es obligatorio (mín. 2 caracteres).");
      return;
    }
    // US-179: si pasa a On Hold, la razón es obligatoria.
    if (status === "on_hold" && !onHoldReason.trim()) {
      setError("Razón de detención obligatoria para poner el ítem On Hold.");
      return;
    }
    setSaving(true);
    setError(null);
    const onHold = {
      on_hold_reason: status === "on_hold" ? onHoldReason.trim() || null : null,
      on_hold_area_id: status === "on_hold" ? onHoldAreaId || null : null,
      on_hold_actor_id: status === "on_hold" ? onHoldActorId || null : null,
    };
    try {
      if (kind === "risk") {
        const body: Parameters<typeof updateRisk>[1] = {
          title: title.trim(),
          description: description.trim() || null,
          category: riskCategory.trim() || null,
          area_id: areaId || undefined,
          owner_actor_id: ownerActorId || null,
          status,
          probability: riskProb,
          impact: riskImpact,
          mitigation_strategy: riskMitigation.trim() || null,
          identified_at: riskIdentified || null,
          due_date: riskDue || null,
          closure_note: riskClosureNote.trim() || null,
          ...onHold,
        };
        const updated = await updateRisk(item.id, body);
        onSaved(updated);
      } else {
        const body: Parameters<typeof updateIssue>[1] = {
          title: title.trim(),
          description: description.trim() || null,
          type: issueType,
          area_id: areaId || undefined,
          owner_actor_id: ownerActorId || null,
          status,
          priority: issuePriority === "" ? null : Number(issuePriority),
          // ENH-054: reported_at viaja como ISO string si tiene fecha.
          reported_at: issueReported
            ? new Date(`${issueReported}T00:00:00Z`).toISOString()
            : null,
          committed_date: issueCommitted || null,
          resolution: issueResolution.trim() || null,
          ...onHold,
        };
        const updated = await updateIssue(item.id, body);
        onSaved(updated);
      }
      if (onClose) onClose();
      else setEditing(false);
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
      <div className="flex flex-col items-stretch gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-[var(--color-tertiary)]">
          Todos los campos del ítem son editables — título, descripción, área,
          responsable, fechas, P×I/prioridad, mitigación/resolución y nota de
          cierre.
        </p>
        <Button
          type="button"
          onClick={() => {
            reset();
            setEditing(true);
          }}
        >
          <Pencil className="mr-1 h-4 w-4" aria-hidden />
          Editar este ítem
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
            if (onClose) onClose();
            else setEditing(false);
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
          <ProjectAreaPicker
            projectId={item.project_id}
            value={areaId || null}
            onChange={(v) => setAreaId(v ?? "")}
            disabled={optsLoading}
            placeholder="— sin área —"
          />
        </Field>
        <Field label="Responsable">
          <PersonPicker
            projectId={item.project_id}
            value={ownerActorId || null}
            onChange={(v) => setOwnerActorId(v ?? "")}
            disabled={optsLoading}
            placeholder="— sin responsable —"
          />
        </Field>
      </div>

      {/* US-179: estado (4) + detención. */}
      <Field label="Estado">
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value as RaidStatus)}
        >
          {(Object.keys(RAID_STATUS_LABEL) as RaidStatus[]).map((s) => (
            <option key={s} value={s}>
              {RAID_STATUS_LABEL[s]}
            </option>
          ))}
        </Select>
      </Field>

      {status === "on_hold" ? (
        <div className="space-y-3 rounded-[var(--radius-md)] border border-[var(--color-warning-border,var(--border-default))] bg-[var(--color-warning-bg)]/40 p-3">
          <p className="text-xs font-medium text-[var(--color-warning-fg)]">
            Detención — indica por qué está detenido y de quién depende.
          </p>
          <Field label="Razón de detención *">
            <Textarea
              value={onHoldReason}
              onChange={(e) => setOnHoldReason(e.target.value)}
              rows={2}
              placeholder="Ej.: Espera aprobación de presupuesto"
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Área de la que depende">
              <ProjectAreaPicker
                projectId={item.project_id}
                value={onHoldAreaId || null}
                onChange={(v) => setOnHoldAreaId(v ?? "")}
                disabled={optsLoading}
                placeholder="— sin dependencia —"
              />
            </Field>
            <Field label="Responsable del que depende">
              <PersonPicker
                projectId={item.project_id}
                value={onHoldActorId || null}
                onChange={(v) => setOnHoldActorId(v ?? "")}
                disabled={optsLoading}
                placeholder="— sin dependencia —"
              />
            </Field>
          </div>
          {item.on_hold_since ? (
            <p className="text-xs text-[var(--color-tertiary)]">
              Detenido desde {item.on_hold_since}.
            </p>
          ) : null}
        </div>
      ) : null}

      {kind === "risk" ? (
        <>
          {/* ENH-054: categoría editable. */}
          <Field label="Categoría">
            <Input
              value={riskCategory}
              onChange={(e) => setRiskCategory(e.target.value)}
              placeholder="Tecnología / Negocio / Operación / …"
            />
          </Field>
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
          {/* ENH-054: nota de cierre editable inline. */}
          <Field label="Nota de cierre (opcional)">
            <Textarea
              value={riskClosureNote}
              onChange={(e) => setRiskClosureNote(e.target.value)}
              rows={2}
              placeholder="Solo aplica si el estado pasa a Cerrado o Materializado"
            />
          </Field>
        </>
      ) : (
        <>
          {/* ENH-054: tipo (Action/Issue/Decision) editable post-creación. */}
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Tipo">
              <Select
                value={issueType}
                onChange={(e) => setIssueType(e.target.value as IssueType)}
              >
                <option value="action">Acción</option>
                <option value="issue">Incidencia</option>
                <option value="decision">Decisión</option>
              </Select>
            </Field>
            <Field label="Fecha reportada">
              <Input
                type="date"
                value={issueReported}
                onChange={(e) => setIssueReported(e.target.value)}
              />
            </Field>
          </div>
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
          <Field label="Nota de cierre">
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
            if (onClose) onClose();
            else setEditing(false);
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
