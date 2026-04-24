"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Building2, FolderKanban, Network } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getOrganizationPanel,
  type OrganizationPanelDetail,
  type OrgPanelProgram,
  type OrgPanelProject,
} from "@/lib/api/organizations";

/**
 * US-068 — Página PMO de organización.
 *
 * Vista informativa del portafolio de una organización: panel de
 * programas (cards) + lista de proyectos. Separada de
 * `/admin/organizations/[id]` (gestión CRUD). El sidebar del PMO
 * lleva aquí al click en el panel de la organización.
 */
export default function PmoOrganizationPage() {
  const { id } = useParams<{ id: string }>();
  const [panel, setPanel] = useState<OrganizationPanelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getOrganizationPanel(id)
      .then((p) => {
        if (!cancelled) setPanel(p);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.status === 404
                ? "Esta organización no existe o no tienes permiso para verla."
                : err.message
              : "No se pudo cargar la organización",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const projectCountByProgram = useMemo(() => {
    const map: Record<string, number> = {};
    if (!panel) return map;
    for (const pj of panel.projects) {
      const key = pj.program_id ?? "__sin_programa__";
      map[key] = (map[key] ?? 0) + 1;
    }
    return map;
  }, [panel]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-6">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-6">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }
  if (!panel) return null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <nav className="text-[11px] text-[var(--text-tertiary)]">
        <Link href="/pmo" className="hover:underline">
          PMO
        </Link>
        <span className="mx-1">/</span>
        <span>{panel.name}</span>
      </nav>

      <header className="flex items-start gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
        <div className="flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
          {panel.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={panel.logo_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <Building2 className="h-6 w-6" aria-hidden />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">
            {panel.name}
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            {[panel.industry, panel.country].filter(Boolean).join(" · ") ||
              "Sin datos de industria"}
          </p>
        </div>
        <Link
          href={`/admin/organizations/${panel.id}`}
          className="text-[12px] text-[var(--color-accent)] hover:underline"
        >
          Administrar →
        </Link>
      </header>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Programas
          </h2>
          <Badge variant="neutral">{panel.programs.length}</Badge>
        </div>
        {panel.programs.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-tertiary)]">
            Esta organización no tiene programas registrados.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {panel.programs.map((program) => (
              <ProgramCard
                key={program.id}
                program={program}
                projectCount={
                  projectCountByProgram[program.id] ?? program.active_project_count
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <FolderKanban
            className="h-4 w-4 text-[var(--color-tertiary)]"
            aria-hidden
          />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Proyectos
          </h2>
          <Badge variant="neutral">{panel.projects.length}</Badge>
        </div>
        {panel.projects.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-tertiary)]">
            Sin proyectos registrados en esta organización.
          </div>
        ) : (
          <div className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <tr>
                  <th className="px-3 py-2 font-medium">Folio</th>
                  <th className="px-3 py-2 font-medium">Nombre</th>
                  <th className="px-3 py-2 font-medium">Programa</th>
                  <th className="px-3 py-2 font-medium">Fase</th>
                  <th className="px-3 py-2 font-medium">Salud</th>
                  <th className="px-3 py-2 font-medium">PM</th>
                </tr>
              </thead>
              <tbody>
                {panel.projects.map((pj) => {
                  const program = panel.programs.find(
                    (pg) => pg.id === pj.program_id,
                  );
                  return (
                    <ProjectRow key={pj.id} project={pj} programName={program?.name ?? "—"} />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function ProgramCard({
  program,
  projectCount,
}: {
  program: OrgPanelProgram;
  projectCount: number;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 truncate text-sm font-semibold text-[var(--color-primary)]">
          {program.name}
        </h3>
        {!program.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
      </div>
      {program.description ? (
        <p className="line-clamp-2 text-[12px] text-[var(--color-secondary)]">
          {program.description}
        </p>
      ) : null}
      <div className="flex gap-3 text-[11px] text-[var(--color-tertiary)]">
        <span>
          <strong className="text-[var(--color-secondary)]">{projectCount}</strong>{" "}
          proyectos
        </span>
      </div>
    </div>
  );
}

function ProjectRow({
  project,
  programName,
}: {
  project: OrgPanelProject;
  programName: string;
}) {
  const healthColor =
    project.health_status === "green"
      ? "var(--color-success-fg)"
      : project.health_status === "yellow"
        ? "var(--color-warning-fg)"
        : project.health_status === "red"
          ? "var(--color-danger-fg)"
          : "var(--color-tertiary)";
  return (
    <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
      <td className="px-3 py-2 font-mono text-xs text-[var(--color-tertiary)]">
        <Link
          href={`/admin/projects/${project.id}`}
          className="hover:text-[var(--color-accent)] hover:underline"
        >
          {project.folio ?? "—"}
        </Link>
      </td>
      <td className="px-3 py-2">
        <Link
          href={`/admin/projects/${project.id}`}
          className="text-[var(--color-primary)] hover:text-[var(--color-accent)] hover:underline"
        >
          {project.name}
        </Link>
      </td>
      <td className="px-3 py-2 text-[var(--color-secondary)]">{programName}</td>
      <td className="px-3 py-2 text-[var(--color-secondary)]">
        {project.phase ?? "—"}
      </td>
      <td className="px-3 py-2">
        <span
          className="inline-flex h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: healthColor }}
          aria-label={project.health_status ?? ""}
        />
      </td>
      <td className="px-3 py-2 text-[var(--color-secondary)]">
        {project.pm_name ?? "—"}
      </td>
    </tr>
  );
}
