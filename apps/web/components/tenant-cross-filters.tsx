"use client";

import { useEffect, useState } from "react";

import { Select } from "@/components/ui/select";
import {
  type Organization,
  type Program,
  listOrganizations,
  listPrograms,
} from "@/lib/api/organizations";
import { type Project, listProjects } from "@/lib/api/projects";

export type TenantCrossFilterValue = {
  organization_id?: string;
  program_id?: string;
  project_id?: string;
};

type Props = {
  value: TenantCrossFilterValue;
  onChange: (next: TenantCrossFilterValue) => void;
  /** Controles adicionales al final (p. ej. estado/tipo específico). */
  extras?: React.ReactNode;
  /**
   * Controles adicionales al inicio (ENH-017). Útil cuando el control
   * principal (tipo/kind) debe ir a la izquierda antes que Proyecto /
   * Programa / Organización.
   */
  leading?: React.ReactNode;
  /**
   * Invierte el orden visual de los tres selects a Proyecto → Programa
   * → Organización (ENH-017). No cambia la cascada lógica (org sigue
   * filtrando programas y proyectos cuando se selecciona).
   */
  reverse?: boolean;
};

/**
 * Filtros de organización / programa / proyecto para vistas cross-tenant
 * (US-052). Los selects se encadenan: elegir org filtra programas;
 * programa + org filtran proyectos.
 */
export function TenantCrossFilters({
  value,
  onChange,
  extras,
  leading,
  reverse = false,
}: Props) {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    listOrganizations({ is_active: true })
      .then(setOrgs)
      .catch(() => setOrgs([]));
  }, []);

  useEffect(() => {
    if (!value.organization_id) {
      setPrograms([]);
      return;
    }
    listPrograms({ organization_id: value.organization_id, is_active: true })
      .then(setPrograms)
      .catch(() => setPrograms([]));
  }, [value.organization_id]);

  useEffect(() => {
    listProjects({
      organization_id: value.organization_id,
      program_id: value.program_id,
    })
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [value.organization_id, value.program_id]);

  const organizationSelect = (
    <Select
      key="organization"
      aria-label="Organización"
      className="h-9 w-full min-w-0"
      value={value.organization_id ?? ""}
      onChange={(e) =>
        onChange({
          organization_id: e.target.value || undefined,
          program_id: undefined,
          project_id: undefined,
        })
      }
    >
      <option value="">Todas las organizaciones</option>
      {orgs.map((o) => (
        <option key={o.id} value={o.id}>
          {o.name}
        </option>
      ))}
    </Select>
  );
  const programSelect = (
    <Select
      key="program"
      aria-label="Programa"
      className="h-9 w-full min-w-0"
      value={value.program_id ?? ""}
      onChange={(e) =>
        onChange({
          ...value,
          program_id: e.target.value || undefined,
          project_id: undefined,
        })
      }
      disabled={!value.organization_id}
    >
      <option value="">Todos los programas</option>
      {programs.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </Select>
  );
  const projectSelect = (
    <Select
      key="project"
      aria-label="Proyecto"
      className="h-9 w-full min-w-0"
      value={value.project_id ?? ""}
      onChange={(e) =>
        onChange({ ...value, project_id: e.target.value || undefined })
      }
    >
      <option value="">Todos los proyectos</option>
      {projects.map((p) => (
        <option key={p.id} value={p.id}>
          {p.folio} — {p.name}
        </option>
      ))}
    </Select>
  );

  const selects = reverse
    ? [projectSelect, programSelect, organizationSelect]
    : [organizationSelect, programSelect, projectSelect];

  // ENH-025 rework definitivo: mobile stackea verticalmente (cada select
  // en su fila), tablet hace grid 2×2, desktop (lg+) fuerza una sola
  // fila horizontal con `flex-nowrap`. `min-w-0 flex-1` en cada select
  // permite que se compriman sin forzar overflow ni wrap.
  //
  // `leading` y `extras` vienen del caller con classes propias; los
  // envolvemos en un wrapper que aplica el layout responsivo para que
  // no haga falta coordinar classes desde fuera.
  const cell = "w-full min-w-0 lg:flex-1";
  return (
    <div className="flex flex-col gap-2 sm:grid sm:grid-cols-2 sm:gap-2 lg:flex lg:flex-row lg:flex-nowrap lg:items-center lg:gap-2">
      {leading ? <div className={cell}>{leading}</div> : null}
      {selects.map((s, i) => (
        <div key={i} className={cell}>
          {s}
        </div>
      ))}
      {extras ? <div className={cell}>{extras}</div> : null}
    </div>
  );
}
