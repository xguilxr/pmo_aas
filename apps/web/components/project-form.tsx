"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { listUsers, type AdminUser } from "@/lib/api/admin";
import { listOrganizations, listPrograms, type Organization, type Program } from "@/lib/api/organizations";
import {
  HEALTH_LABEL,
  PHASE_LABEL,
  TYPE_LABEL,
  createProject,
  updateProject,
  type Project,
  type ProjectCreateBody,
  type ProjectHealth,
  type ProjectPhase,
  type ProjectType,
} from "@/lib/api/projects";

type Props = {
  mode: "create" | "edit";
  initial?: Project;
};

type Notice = { kind: "success" | "danger"; message: string } | null;

export function ProjectForm({ mode, initial }: Props) {
  const router = useRouter();

  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [type, setType] = useState<ProjectType>((initial?.type as ProjectType) ?? "transformation");
  const [priority, setPriority] = useState(String(initial?.priority ?? 3));
  const [phase, setPhase] = useState<ProjectPhase>(initial?.phase ?? "planning");
  const [organizationId, setOrganizationId] = useState(initial?.organization_id ?? "");
  const [programId, setProgramId] = useState<string>(initial?.program_id ?? "");
  const [pmId, setPmId] = useState<string>(initial?.pm_id ?? "");
  const [sponsor, setSponsor] = useState(initial?.sponsor ?? "");
  const [startDate, setStartDate] = useState(initial?.start_date ?? "");
  const [endDate, setEndDate] = useState(initial?.end_date ?? "");
  const [budget, setBudget] = useState(initial?.budget ?? "");
  // ENH-132: salud y presupuesto real editables (solo modo edición).
  const [health, setHealth] = useState<ProjectHealth>(initial?.health_status ?? "green");
  const [actualBudget, setActualBudget] = useState(initial?.actual_budget ?? "");

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [pms, setPms] = useState<AdminUser[]>([]);

  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    listOrganizations({ is_active: true })
      .then(setOrgs)
      .catch(() => {});
    listUsers({ is_active: true, limit: 100 })
      .then((r) => setPms(r.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!organizationId) {
      setPrograms([]);
      return;
    }
    listPrograms({ organization_id: organizationId, is_active: true })
      .then(setPrograms)
      .catch(() => setPrograms([]));
  }, [organizationId]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      if (mode === "create") {
        const body: ProjectCreateBody = {
          name: name.trim(),
          description: description.trim(),
          type,
          priority: Number(priority) || 3,
          organization_id: organizationId,
          program_id: programId || null,
          phase,
          pm_id: pmId,
          sponsor: sponsor.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          budget: budget ? Number(budget) : null,
        };
        const p = await createProject(body);
        // BUG-018: el nuevo proyecto ya tiene charter; mandamos al form
        // de charter para que el usuario complemente la información que
        // el form básico no pide (stakeholders extra, alcance, beneficios,
        // restricciones, riesgos).
        router.replace(`/pmo/projects/${p.id}/charter?created=1`);
      } else if (initial) {
        const updated = await updateProject(initial.id, {
          name: name.trim(),
          description: description.trim(),
          type,
          priority: Number(priority) || 3,
          program_id: programId || null,
          pm_id: pmId,
          sponsor: sponsor.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          budget: budget ? Number(budget) : null,
          actual_budget: actualBudget ? Number(actualBudget) : null,
          health_status: health,
        });
        setNotice({ kind: "success", message: "Proyecto actualizado" });
        router.refresh();
        void updated;
      }
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo guardar",
      });
    } finally {
      setSaving(false);
    }
  }

  const canSubmit =
    name.trim().length >= 2 &&
    description.trim().length > 0 &&
    organizationId &&
    pmId &&
    priority;

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6"
    >
      {notice ? <Banner variant={notice.kind}>{notice.message}</Banner> : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nombre" full>
          <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
        </Field>
        <Field label="Descripción" full>
          <Textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </Field>
        <Field label="Tipo">
          <Select value={type} onChange={(e) => setType(e.target.value as ProjectType)}>
            {(Object.keys(TYPE_LABEL) as ProjectType[]).map((k) => (
              <option key={k} value={k}>
                {TYPE_LABEL[k]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Prioridad (1-5)">
          <Select value={priority} onChange={(e) => setPriority(e.target.value)}>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Organización">
          <Select
            value={organizationId}
            onChange={(e) => {
              setOrganizationId(e.target.value);
              setProgramId("");
            }}
            disabled={mode === "edit"}
            required
          >
            <option value="">Selecciona…</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Programa (opcional)">
          <Select value={programId} onChange={(e) => setProgramId(e.target.value)}>
            <option value="">Sin programa</option>
            {programs.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Fase">
          <Select
            value={phase}
            onChange={(e) => setPhase(e.target.value as ProjectPhase)}
            disabled={mode === "edit"}
          >
            {(Object.keys(PHASE_LABEL) as ProjectPhase[]).map((k) => (
              <option key={k} value={k}>
                {PHASE_LABEL[k]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Project Manager">
          <Select value={pmId} onChange={(e) => setPmId(e.target.value)} required>
            <option value="">Selecciona…</option>
            {pms.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name} · {u.email}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Sponsor">
          <Input value={sponsor} onChange={(e) => setSponsor(e.target.value)} />
        </Field>
        <Field label="Presupuesto (MXN)">
          <Input
            type="number"
            min={0}
            step="0.01"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
        </Field>
        {mode === "edit" ? (
          <>
            <Field label="Presupuesto real / consumido (MXN)">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={actualBudget}
                onChange={(e) => setActualBudget(e.target.value)}
              />
            </Field>
            <Field label="Salud">
              <Select
                value={health}
                onChange={(e) => setHealth(e.target.value as ProjectHealth)}
              >
                {(Object.keys(HEALTH_LABEL) as ProjectHealth[]).map((k) => (
                  <option key={k} value={k}>
                    {HEALTH_LABEL[k]}
                  </option>
                ))}
              </Select>
            </Field>
          </>
        ) : null}
        <Field label="Inicio planeado">
          <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </Field>
        <Field label="Fin planeado">
          <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </Field>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
        <Button
          type="button"
          variant="secondary"
          onClick={() =>
            router.push(
              mode === "edit" && initial
                ? `/pmo/projects/${initial.id}`
                : "/pmo/projects",
            )
          }
          disabled={saving}
        >
          Cancelar
        </Button>
        <Button type="submit" loading={saving} disabled={!canSubmit}>
          {mode === "create" ? "Crear proyecto" : "Guardar cambios"}
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  children,
  full,
}: {
  label: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <label className={full ? "sm:col-span-2" : undefined}>
      <span className="mb-1.5 block text-[12px] font-medium text-[var(--text-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
