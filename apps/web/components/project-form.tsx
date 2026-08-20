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
import {
  listPortfolios,
  listPrograms,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import { MONEDAS } from "@/lib/moneda";
import { useMonedaPreferida } from "@/lib/moneda-tenant";
import {
  PHASE_LABEL,
  TYPE_LABEL,
  createProject,
  updateProject,
  type Project,
  type ProjectCreateBody,
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
  const [type, setType] = useState<ProjectType>((initial?.type as ProjectType) ?? "transformacion");
  const [priority, setPriority] = useState(String(initial?.priority ?? 3));
  const [phase, setPhase] = useState<ProjectPhase>(initial?.phase ?? "preparacion");
  // US-205 — la organización sigue siendo un **campo** del proyecto y no un
  // filtro: decide dónde vive, así que el select se queda. Lo que cambia es el
  // valor con el que arranca al crear — la del header, no «Selecciona…» —, que
  // era el paso que se repetía en cada alta.
  const { organizaciones: orgs, efectiva: orgDelHeader } = useOrganizacionActiva();
  const [organizationId, setOrganizationId] = useState(initial?.organization_id ?? "");
  // US-200 — el portafolio del proyecto. Con programa se autocompleta con el
  // suyo; sin programa, se elige directo (un proyecto puede colgar del
  // portafolio sin que nadie lo coordine).
  const [portfolioId, setPortfolioId] = useState<string>(initial?.portfolio_id ?? "");
  const [programId, setProgramId] = useState<string>(initial?.program_id ?? "");
  const [pmId, setPmId] = useState<string>(initial?.pm_id ?? "");
  const [sponsor, setSponsor] = useState(initial?.sponsor ?? "");
  const [startDate, setStartDate] = useState(initial?.start_date ?? "");
  const [endDate, setEndDate] = useState(initial?.end_date ?? "");
  const [budget, setBudget] = useState(initial?.budget ?? "");
  // BUG-092 — la moneda del proyecto. Vacío = la preferida del inquilino.
  const [currency, setCurrency] = useState(initial?.currency ?? "");
  const monedaPreferida = useMonedaPreferida();
  const moneda = currency || monedaPreferida;
  // ENH-132: salud y presupuesto real editables (solo modo edición).
  const [actualBudget, setActualBudget] = useState(initial?.actual_budget ?? "");

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [pms, setPms] = useState<AdminUser[]>([]);

  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    listUsers({ is_active: true, limit: 100 })
      .then((r) => setPms(r.items))
      .catch(() => {});
  }, []);

  // El header carga sus organizaciones de forma asíncrona, así que al montar
  // todavía no hay ninguna. Se siembra cuando llega, y **solo** si el campo
  // sigue vacío: si la persona ya eligió otra, esto no se la cambia debajo.
  useEffect(() => {
    if (mode === "edit" || !orgDelHeader) return;
    setOrganizationId((actual) => actual || orgDelHeader);
  }, [mode, orgDelHeader]);

  useEffect(() => {
    if (!organizationId) {
      setPortfolios([]);
      setPrograms([]);
      return;
    }
    let cancelado = false;
    Promise.all([
      listPortfolios(organizationId, { is_active: true }),
      listPrograms({ organization_id: organizationId, is_active: true }),
    ])
      .then(([pfs, progs]) => {
        if (cancelado) return;
        setPortfolios(pfs);
        setPrograms(progs);
      })
      .catch(() => {
        if (cancelado) return;
        setPortfolios([]);
        setPrograms([]);
      });
    return () => {
      cancelado = true;
    };
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
          portfolio_id: portfolioId || null,
          phase,
          pm_id: pmId,
          sponsor: sponsor.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          budget: budget ? Number(budget) : null,
          currency: currency || null,
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
          portfolio_id: portfolioId || null,
          pm_id: pmId,
          sponsor: sponsor.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          budget: budget ? Number(budget) : null,
          currency: currency || null,
          actual_budget: actualBudget ? Number(actualBudget) : null,
          // US-181: la salud ya no se edita desde el form — se declara en
          // la tarjeta de Salud del detalle (razón obligatoria en 🟡/🔴).
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
              // Portafolio y programa pertenecen a la organización: al
              // cambiarla, los dos dejan de ser válidos.
              setPortfolioId("");
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
        <Field label="Portafolio (opcional)">
          <Select
            value={portfolioId}
            onChange={(e) => {
              setPortfolioId(e.target.value);
              // Cambiar de portafolio invalida el programa: un programa
              // pertenece a un portafolio y solo a uno.
              setProgramId("");
            }}
            disabled={!organizationId}
          >
            <option value="">Sin clasificar</option>
            {portfolios.map((pf) => (
              <option key={pf.id} value={pf.id}>
                {pf.code ? `${pf.code} — ${pf.name}` : pf.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Programa (opcional)">
          <Select
            value={programId}
            onChange={(e) => {
              const v = e.target.value;
              setProgramId(v);
              // Elegir programa completa su portafolio: es lo que el servidor
              // va a guardar de todos modos (regla de consistencia), así que la
              // pantalla lo muestra en vez de dejarlo en blanco.
              const prog = programs.find((pr) => pr.id === v);
              if (prog) setPortfolioId(prog.portfolio_id);
            }}
            disabled={!organizationId}
          >
            <option value="">Sin programa</option>
            {programs
              .filter((pr) => !portfolioId || pr.portfolio_id === portfolioId)
              .map((pr) => (
                <option key={pr.id} value={pr.id}>
                  {pr.name}
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
        <Field label={`Presupuesto (${moneda})`}>
          <Input
            type="number"
            min={0}
            step="0.01"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
        </Field>
        {/* BUG-092 — la moneda la elige el proyecto. Vacío hereda la del
            inquilino, así que cambiar la preferida arrastra a los que no
            eligieron, que es lo que espera quien la cambia. */}
        <Field label="Moneda">
          <select
            className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-sm"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          >
            <option value="">Usar la del inquilino ({monedaPreferida})</option>
            {MONEDAS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
        {mode === "edit" ? (
          <>
            <Field label={`Presupuesto real / consumido (${moneda})`}>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={actualBudget}
                onChange={(e) => setActualBudget(e.target.value)}
              />
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
