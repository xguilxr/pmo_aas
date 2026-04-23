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
      className="h-9 min-w-[180px]"
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
      className="h-9 min-w-[180px]"
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
      className="h-9 min-w-[220px]"
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

  return (
    <div className="flex flex-wrap items-center gap-2">
      {leading}
      {selects}
      {extras}
    </div>
  );
}
