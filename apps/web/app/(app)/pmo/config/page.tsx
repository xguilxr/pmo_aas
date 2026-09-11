"use client";

/**
 * FASE-4 (revamp v2, US-E) — `/pmo/config`: alta, edición y reasignación de
 * portafolios y programas de la organización activa. Diseño: wireframe W3.
 *
 * "Estilo carpetas": un portafolio se despliega en sus programas, y cada
 * programa en sus proyectos. Mover un proyecto es un `Select` de programa en
 * su fila — el backend valida que el programa pertenezca al portafolio
 * elegido (US-199, `resolver_portafolio`).
 *
 * El borrado de aquí es el suave (`deletePortfolio`/`deleteProgram`); el
 * permanente es de Admin (fase 7).
 */
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { ProgramModal } from "@/components/program-modal";
import { PortfolioForm } from "@/components/portfolio-form";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import { ApiError } from "@/lib/api";
import {
  deletePortfolio,
  deleteProgram,
  listPortfolios,
  listPrograms,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import { listProjects, updateProject, type Project } from "@/lib/api/projects";

export default function PmoConfigPage() {
  const { efectiva: orgId, activaObj, cargando: cargandoOrg, vacio } = useOrganizacionActiva();

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());
  const [pfForm, setPfForm] = useState<{ abierto: boolean; editar: Portfolio | null }>({
    abierto: false,
    editar: null,
  });
  const [pgForm, setPgForm] = useState<{ abierto: boolean; editar: Program | null }>({
    abierto: false,
    editar: null,
  });

  const cargar = useCallback(async () => {
    if (!orgId) {
      setPortfolios([]);
      setPrograms([]);
      setProjects([]);
      setCargando(false);
      return;
    }
    setCargando(true);
    setError(null);
    try {
      const [pfs, pgs, prjs] = await Promise.all([
        listPortfolios(orgId, {}),
        listPrograms({ organization_id: orgId }),
        listProjects({ organization_id: orgId }),
      ]);
      setPortfolios(pfs);
      setPrograms(pgs);
      setProjects(prjs);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cargar la configuración.");
    } finally {
      setCargando(false);
    }
  }, [orgId]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const programasPorPortafolio = useMemo(() => {
    const m = new Map<string, Program[]>();
    for (const pg of programs) {
      const arr = m.get(pg.portfolio_id) ?? [];
      arr.push(pg);
      m.set(pg.portfolio_id, arr);
    }
    return m;
  }, [programs]);

  const proyectosPorPrograma = useMemo(() => {
    const m = new Map<string, Project[]>();
    for (const p of projects) {
      if (!p.program_id) continue;
      const arr = m.get(p.program_id) ?? [];
      arr.push(p);
      m.set(p.program_id, arr);
    }
    return m;
  }, [projects]);

  function toggle(id: string) {
    setExpandidos((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function borrarPortafolio(pf: Portfolio) {
    if (!confirm(`¿Borrar el portafolio "${pf.name}"?`)) return;
    try {
      await deletePortfolio(pf.id);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo borrar el portafolio.");
    }
  }

  async function borrarPrograma(pg: Program) {
    if (!confirm(`¿Borrar el programa "${pg.name}"?`)) return;
    try {
      await deleteProgram(pg.id);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo borrar el programa.");
    }
  }

  async function moverProyecto(project: Project, programId: string) {
    const destino = programs.find((pg) => pg.id === programId);
    try {
      await updateProject(project.id, {
        program_id: programId,
        portfolio_id: destino?.portfolio_id ?? null,
      });
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo mover el proyecto.");
    }
  }

  if (cargandoOrg || cargando) {
    return (
      <div className="space-y-3 p-6">
        <span aria-hidden className="block h-8 w-64 animate-pulse rounded bg-[var(--color-muted)]" />
        <span aria-hidden className="block h-40 animate-pulse rounded bg-[var(--color-muted)]" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4.5 p-6">
      <Breadcrumb items={[{ href: "/pmo", label: "PMO" }, { label: "Config" }]} />
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Portafolios y programas
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            De {activaObj?.name ?? "—"}. Se cambia de organización en el
            selector del header.
          </p>
        </div>
        <Button type="button" onClick={() => setPfForm({ abierto: true, editar: null })}>
          <Icono nombre="plus" size={14} />
          Nuevo portafolio
        </Button>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {vacio ? (
        <Banner variant="info">
          Este inquilino todavía no tiene organizaciones. Crea una primero en
          Admin › Organizaciones.
        </Banner>
      ) : portfolios.length === 0 ? (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--text-tertiary)]">
          Esta organización todavía no tiene portafolios.
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {portfolios.map((pf) => {
            const abierto = expandidos.has(pf.id);
            const susProgramas = programasPorPortafolio.get(pf.id) ?? [];
            return (
              <section
                key={pf.id}
                className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]"
              >
                <div className="flex items-center gap-2 px-4 py-3">
                  <button
                    type="button"
                    onClick={() => toggle(pf.id)}
                    className="flex flex-1 items-center gap-2 text-left"
                  >
                    <Icono nombre={abierto ? "chevron-down" : "chevron-right"} size={14} />
                    <span className="font-medium text-[var(--text-primary)]">{pf.name}</span>
                    {pf.code ? (
                      <span className="font-mono text-[11px] text-[var(--text-tertiary)]">
                        {pf.code}
                      </span>
                    ) : null}
                    {!pf.is_active ? (
                      <span className="text-[11px] text-[var(--text-faint)]">inactivo</span>
                    ) : null}
                    <span className="ml-auto text-[11px] text-[var(--text-tertiary)]">
                      {susProgramas.length} programa(s)
                    </span>
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setPgForm({ abierto: true, editar: null })}
                    title="Nuevo programa en este portafolio"
                  >
                    <Icono nombre="plus" size={13} />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setPfForm({ abierto: true, editar: pf })}
                    title="Editar portafolio"
                  >
                    <Icono nombre="pen" size={13} />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => void borrarPortafolio(pf)}
                    title="Borrar portafolio"
                  >
                    <Icono nombre="x" size={13} />
                  </Button>
                </div>

                {abierto ? (
                  <div className="border-t border-[var(--border-subtle)] px-4 py-2">
                    {susProgramas.length === 0 ? (
                      <p className="py-3 text-[12px] text-[var(--text-tertiary)]">
                        Sin programas todavía.
                      </p>
                    ) : (
                      susProgramas.map((pg) => {
                        const susProyectos = proyectosPorPrograma.get(pg.id) ?? [];
                        return (
                          <div key={pg.id} className="border-b border-[var(--border-subtle)] py-2.5 last:border-0">
                            <div className="flex items-center gap-2">
                              <span className="text-[13px] font-medium text-[var(--text-primary)]">
                                {pg.name}
                              </span>
                              <span className="text-[11px] text-[var(--text-tertiary)]">
                                {susProyectos.length} proyecto(s)
                              </span>
                              <div className="ml-auto flex gap-1">
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setPgForm({ abierto: true, editar: pg })}
                                  title="Editar programa"
                                >
                                  <Icono nombre="pen" size={12} />
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => void borrarPrograma(pg)}
                                  title="Borrar programa"
                                >
                                  <Icono nombre="x" size={12} />
                                </Button>
                              </div>
                            </div>
                            {susProyectos.length > 0 ? (
                              <ul className="mt-1.5 space-y-1 pl-4">
                                {susProyectos.map((p) => (
                                  <li key={p.id} className="flex items-center gap-2 text-[12.5px]">
                                    <Link
                                      href={`/pmo/projects/${p.id}`}
                                      className="min-w-0 flex-1 truncate text-[var(--text-secondary)] hover:text-[var(--color-accent)]"
                                    >
                                      {p.name}
                                    </Link>
                                    <Select
                                      aria-label={`Mover ${p.name}`}
                                      value={p.program_id ?? ""}
                                      onChange={(e) => void moverProyecto(p, e.target.value)}
                                      className="h-7 w-[200px] text-[12px]"
                                    >
                                      {programs.map((pg2) => (
                                        <option key={pg2.id} value={pg2.id}>
                                          {pg2.name}
                                        </option>
                                      ))}
                                    </Select>
                                  </li>
                                ))}
                              </ul>
                            ) : null}
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      )}

      <PortfolioForm
        open={pfForm.abierto}
        organizationId={orgId ?? ""}
        portafolio={pfForm.editar}
        onClose={() => setPfForm({ abierto: false, editar: null })}
        onSaved={() => {
          setPfForm({ abierto: false, editar: null });
          void cargar();
        }}
      />
      <ProgramModal
        open={pgForm.abierto}
        initialOrgId={orgId ?? undefined}
        programa={pgForm.editar}
        onClose={() => setPgForm({ abierto: false, editar: null })}
        onSaved={() => {
          setPgForm({ abierto: false, editar: null });
          void cargar();
        }}
      />
    </div>
  );
}
