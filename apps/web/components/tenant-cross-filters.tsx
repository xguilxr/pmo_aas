"use client";

import { useEffect, useState } from "react";

import { Select } from "@/components/ui/select";
import {
  type Organization,
  type Portfolio,
  type Program,
  listOrganizations,
  listPortfolios,
  listPrograms,
} from "@/lib/api/organizations";
import { type Project, listProjects } from "@/lib/api/projects";

export type TenantCrossFilterValue = {
  organization_id?: string;
  /** US-201 — el nivel nuevo de la cascada, entre organización y programa. */
  portfolio_id?: string;
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
   * Invierte el orden visual de los selects (ENH-017). No cambia la cascada
   * lógica (org sigue filtrando portafolios, programas y proyectos).
   */
  reverse?: boolean;
};

/**
 * Filtros de organización / portafolio / programa / proyecto para vistas
 * cross-tenant (US-052, ampliado en US-201). Los selects se encadenan: elegir
 * organización filtra portafolios; portafolio filtra programas; y los tres
 * filtran proyectos.
 *
 * Cada nivel **limpia los de abajo** al cambiar. No es cosmética: dejar un
 * programa de otro portafolio seleccionado produce una consulta que cruza dos
 * filtros incompatibles y devuelve vacío, que se lee como «no hay datos» y no
 * como «el filtro no tiene sentido».
 */
export function TenantCrossFilters({
  value,
  onChange,
  extras,
  leading,
  reverse = false,
}: Props) {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    listOrganizations({ is_active: true })
      .then(setOrgs)
      .catch(() => setOrgs([]));
  }, []);

  useEffect(() => {
    if (!value.organization_id) {
      setPortfolios([]);
      return;
    }
    listPortfolios(value.organization_id, { is_active: true })
      .then(setPortfolios)
      .catch(() => setPortfolios([]));
  }, [value.organization_id]);

  useEffect(() => {
    if (!value.organization_id) {
      setPrograms([]);
      return;
    }
    listPrograms({
      organization_id: value.organization_id,
      portfolio_id: value.portfolio_id,
      is_active: true,
    })
      .then(setPrograms)
      .catch(() => setPrograms([]));
  }, [value.organization_id, value.portfolio_id]);

  useEffect(() => {
    listProjects({
      organization_id: value.organization_id,
      portfolio_id: value.portfolio_id,
      program_id: value.program_id,
    })
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [value.organization_id, value.portfolio_id, value.program_id]);

  const organizationSelect = (
    <Select
      key="organization"
      aria-label="Organización"
      className="h-9 w-full min-w-0"
      value={value.organization_id ?? ""}
      onChange={(e) =>
        onChange({
          organization_id: e.target.value || undefined,
          portfolio_id: undefined,
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
  const portfolioSelect = (
    <Select
      key="portfolio"
      aria-label="Portafolio"
      className="h-9 w-full min-w-0"
      value={value.portfolio_id ?? ""}
      onChange={(e) =>
        onChange({
          ...value,
          portfolio_id: e.target.value || undefined,
          program_id: undefined,
          project_id: undefined,
        })
      }
      disabled={!value.organization_id}
    >
      <option value="">
        {value.organization_id ? "Todos los portafolios" : "Elige una organización"}
      </option>
      {/* DIS-03 — «elige una organización» y «esta organización no tiene
          portafolios» son dos vacíos distintos. Sin distinguirlos, un
          desplegable con una sola opción se lee como que algo falló. */}
      {value.organization_id && portfolios.length === 0 ? (
        <option value="" disabled>
          (esta organización no tiene portafolios)
        </option>
      ) : null}
      {portfolios.map((pf) => (
        <option key={pf.id} value={pf.id}>
          {pf.code ? `${pf.code} — ${pf.name}` : pf.name}
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
      <option value="">
        {value.organization_id ? "Todos los programas" : "Elige una organización"}
      </option>
      {/* Con portafolio elegido la lista viene recortada a los suyos, así que el
          vacío tiene dos causas y hay que decir cuál. */}
      {value.organization_id && programs.length === 0 ? (
        <option value="" disabled>
          {value.portfolio_id
            ? "(este portafolio no tiene programas)"
            : "(esta organización no tiene programas)"}
        </option>
      ) : null}
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
    ? [projectSelect, programSelect, portfolioSelect, organizationSelect]
    : [organizationSelect, portfolioSelect, programSelect, projectSelect];

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
