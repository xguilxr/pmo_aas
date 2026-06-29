"use client";

import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { createIssue, createRisk, type IssueType } from "@/lib/api/modules";
import { listProjectAreas, type ProjectArea } from "@/lib/api/project-areas";

/**
 * ENH-026: modal unificado para crear un ítem RAID (riesgo, acción,
 * incidente o decisión) desde la vista consolidada `/pmo/projects/
 * [id]/raid`. Reemplaza los 2 formularios separados que vivían en
 * `/risks` y `/issues` (Gestión avanzada, borradas en el mismo ENH).
 */
export type RaidKind = "risks" | "actions" | "incidents" | "decisions";

/** BUG-084: fecha de HOY en zona local como "YYYY-MM-DD" (no UTC). */
function localToday(): string {
  const d = new Date();
  const off = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - off).toISOString().slice(0, 10);
}

const KIND_TITLE: Record<RaidKind, string> = {
  risks: "Registrar riesgo",
  actions: "Registrar acción",
  incidents: "Registrar incidente",
  decisions: "Registrar decisión",
};

const KIND_NEW_LABEL: Record<RaidKind, string> = {
  risks: "Nuevo riesgo",
  actions: "Nueva acción",
  incidents: "Nuevo incidente",
  decisions: "Nueva decisión",
};

/** Mapeo de kind UI → tipo backend (`action | issue | decision`). */
const KIND_TO_ISSUE_TYPE: Record<
  Exclude<RaidKind, "risks">,
  IssueType
> = {
  actions: "action",
  incidents: "issue",
  decisions: "decision",
};

type Props = {
  projectId: string;
  kind: RaidKind;
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
};

export function RaidCreateModal({
  projectId,
  kind,
  open,
  onClose,
  onCreated,
}: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  // Riesgos: P/I/mitigación/fecha compromiso.
  const [probability, setProbability] = useState(3);
  const [impact, setImpact] = useState(3);
  const [mitigation, setMitigation] = useState("");
  const [dueDate, setDueDate] = useState("");
  // Issues (A/I/D): prioridad + fecha compromiso.
  const [priority, setPriority] = useState(3);
  const [committedDate, setCommittedDate] = useState("");
  // US-064: área obligatoria + fecha de creación editable.
  const [areas, setAreas] = useState<ProjectArea[]>([]);
  const [areaId, setAreaId] = useState<string>("");
  // BUG-084: default = HOY local (no UTC) para no adelantar un día en husos
  // detrás de UTC.
  const [identifiedAt, setIdentifiedAt] = useState<string>(localToday);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Carga las áreas del proyecto cuando abre el modal. Si hay sólo 1,
  // la selecciona automáticamente para no obligar un click extra.
  useEffect(() => {
    if (!open) return;
    listProjectAreas(projectId, { is_active: true })
      .then((rows) => {
        setAreas(rows);
        if (rows.length === 1) setAreaId(rows[0].id);
      })
      .catch(() => setAreas([]));
  }, [open, projectId]);

  function reset() {
    setTitle("");
    setDescription("");
    setProbability(3);
    setImpact(3);
    setMitigation("");
    setDueDate("");
    setPriority(3);
    setCommittedDate("");
    setAreaId("");
    setIdentifiedAt(localToday());
    setError(null);
  }

  async function submit() {
    if (!areaId) {
      setError("Área responsable es obligatoria");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      if (kind === "risks") {
        await createRisk(projectId, {
          title: title.trim(),
          description: description.trim() || null,
          probability,
          impact,
          mitigation_strategy: mitigation.trim() || null,
          area_id: areaId,
          identified_at: identifiedAt || null,
          due_date: dueDate || null,
        });
      } else {
        await createIssue(projectId, {
          title: title.trim(),
          description: description.trim() || null,
          type: KIND_TO_ISSUE_TYPE[kind],
          priority,
          area_id: areaId,
          committed_date: committedDate || null,
          // BUG-084: respeta la fecha de creación elegida (antes se perdía
          // y el server usaba la fecha actual → aparecía "hoy").
          reported_at: identifiedAt
            ? new Date(`${identifiedAt}T00:00:00Z`).toISOString()
            : null,
        });
      }
      reset();
      onCreated();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo crear el ítem",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    if (submitting) return;
    reset();
    onClose();
  }

  const canSubmit = title.trim().length > 0 && areaId.length > 0 && !submitting;

  return (
    <Modal open={open} onClose={handleClose} title={KIND_TITLE[kind]} size="lg">
      <div className="space-y-3">
        {error ? <Banner variant="danger">{error}</Banner> : null}
        {areas.length === 0 ? (
          <Banner variant="warning">
            Este proyecto aún no tiene áreas. Crea un área primero en la
            pestaña <strong>Áreas</strong> antes de registrar un ítem RAID.
          </Banner>
        ) : null}
        <Field label="Título">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </Field>
        <Field label="Descripción">
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Área responsable *">
            <Select
              value={areaId}
              onChange={(e) => setAreaId(e.target.value)}
              disabled={areas.length === 0}
            >
              <option value="">— Selecciona un área —</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Fecha de creación">
            <Input
              type="date"
              value={identifiedAt}
              onChange={(e) => setIdentifiedAt(e.target.value)}
            />
          </Field>
        </div>

        {kind === "risks" ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Probabilidad (1-5)">
                <Select
                  value={String(probability)}
                  onChange={(e) => setProbability(Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Impacto (1-5)">
                <Select
                  value={String(impact)}
                  onChange={(e) => setImpact(Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="Estrategia de mitigación">
              <Textarea
                rows={3}
                value={mitigation}
                onChange={(e) => setMitigation(e.target.value)}
              />
            </Field>
            <Field label="Fecha compromiso">
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </Field>
          </>
        ) : (
          <>
            <Field label="Prioridad (1-5)">
              <Select
                value={String(priority)}
                onChange={(e) => setPriority(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Fecha compromiso">
              <Input
                type="date"
                value={committedDate}
                onChange={(e) => setCommittedDate(e.target.value)}
              />
            </Field>
          </>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={handleClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={submitting} disabled={!canSubmit}>
            Crear
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export { KIND_NEW_LABEL };

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
