"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { KpiBand, KpiCard } from "@/components/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import {
  HEALTH_LABEL,
  PHASE_BADGE_TONE,
  PHASE_LABEL,
  type ProjectHealth,
  type ProjectPhase,
} from "@/lib/api/projects";
import {
  getOrganizationPanel,
  type OrganizationPanelDetail,
} from "@/lib/api/organizations";

const ADMIN_ROLES = new Set(["Administrador", "PMO Manager"]);

function userCanEdit(): boolean {
  const u = getStoredUser();
  if (!u) return false;
  if (u.is_superadmin) return true;
  return (u.roles ?? []).some((r) => ADMIN_ROLES.has(r));
}

function SectionCard({
  title,
  iconName,
  count,
  children,
}: {
  title: string;
  iconName: string;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <div className="flex items-center gap-2 border-b border-[var(--border-default)] px-4 py-3 shadow-[var(--linea-surco)]">
        <Icono nombre={iconName} size={15} className="text-[var(--text-tertiary)]" />
        <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">{title}</h2>
        {typeof count === "number" ? <Badge variant="neutral">{count}</Badge> : null}
      </div>
      {children}
    </section>
  );
}

const HEALTH_DOT_BG: Record<ProjectHealth, string> = {
  green: "bg-[var(--color-success-fg)]",
  yellow: "bg-[var(--color-warning-fg)]",
  red: "bg-[var(--color-danger-fg)]",
};

function healthBadge(health: string | null) {
  // ENH-110: salud = solo el color (círculo), sin la palabra.
  if (!health || !(health in HEALTH_DOT_BG)) {
    return <span className="text-[13px] text-[var(--text-faint)]">—</span>;
  }
  const key = health as ProjectHealth;
  return (
    <span
      title={HEALTH_LABEL[key]}
      aria-label={HEALTH_LABEL[key]}
      role="img"
      className={`inline-block h-2.5 w-2.5 rounded-full ${HEALTH_DOT_BG[key]}`}
    />
  );
}

function phaseBadge(phase: string | null) {
  if (!phase) return <span className="text-[13px] text-[var(--text-faint)]">—</span>;
  const key = phase as ProjectPhase;
  const label = PHASE_LABEL[key] ?? phase;
  const tone = PHASE_BADGE_TONE[key] ?? "neutral";
  return <Badge variant={tone}>{label}</Badge>;
}

export default function OrganizationPanelPage() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<OrganizationPanelDetail | null>(null);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(data);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canEdit = userCanEdit();
  // ENH-190: label configurable por tenant para "Organización(es)".

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getOrganizationPanel(params.id)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el panel");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error && !data) {
    return (
      <div>
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  // US-200 — el conteo de programas se deriva del árbol de portafolios, que es
  // donde viven anidados; la lista plana `data.programs` trae los mismos.
  const totalProgramas = data.programs.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <BackLink fallbackHref="/admin/organizations" />
        <Breadcrumb
          items={[
            { href: "/admin/organizations", label: "Organizaciones" },
            { label: data.name },
          ]}
        />
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--text-tertiary)]">
            {data.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={data.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <Icono nombre="building" size={22} />
            )}
          </div>
          <div>
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
              {data.name}
            </h1>
            {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
            <div className="mt-1 flex items-center gap-2 text-[12px] text-[var(--text-tertiary)]">
              {[data.industry, data.country].filter(Boolean).join(" · ") ||
                "Sin datos"}
              {!data.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
            </div>
            {data.contact_email ? (
              <a
                href={`mailto:${data.contact_email}`}
                className="mt-1 inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
              >
                <Icono nombre="mail" size={13} /> {data.contact_email}
              </a>
            ) : null}
          </div>
        </div>
        {canEdit ? (
          <Link href={`/admin/organizations/${data.id}/edit`}>
            <Button variant="secondary">
              <Icono nombre="pen" size={15} /> Editar
            </Button>
          </Link>
        ) : null}
      </div>

      <KpiBand className="grid-cols-2 sm:grid-cols-3">
        <KpiCard
          label="Portafolios"
          value={data.portfolios.length}
          icon={<Icono nombre="folders" size={14} />}
        />
        <KpiCard
          label="Programas"
          value={totalProgramas}
          icon={<Icono nombre="git-branch" size={14} />}
        />
        <KpiCard
          label="Proyectos"
          value={data.projects.length}
          icon={<Icono nombre="folder" size={14} />}
        />
      </KpiBand>

      <SectionCard title="Portafolios" iconName="folders" count={data.portfolios.length}>
        {data.portfolios.length === 0 ? (
          <p className="px-4 py-6 text-center text-[13px] text-[var(--text-tertiary)]">
            Sin portafolios configurados.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {data.portfolios.map((pf) => (
              <li key={pf.id} className="flex flex-col gap-1.5 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Icono nombre="folder" size={14} className="flex-none text-[var(--text-tertiary)]" />
                  <span className="text-[13px] font-medium text-[var(--text-primary)]">
                    {pf.name}
                  </span>
                  {pf.code ? <Badge variant="neutral">{pf.code}</Badge> : null}
                  <span className="text-[12px] text-[var(--text-tertiary)]">
                    {pf.active_project_count} proyecto
                    {pf.active_project_count === 1 ? "" : "s"} activo
                    {pf.active_project_count === 1 ? "" : "s"}
                  </span>
                </div>
                {pf.description ? (
                  <p className="text-[12px] text-[var(--text-tertiary)]">
                    {pf.description}
                  </p>
                ) : null}
                {pf.programs.length > 0 ? (
                  <ul className="flex flex-wrap gap-1.5">
                    {pf.programs.map((prog) => (
                      <li
                        key={prog.id}
                        className="rounded-full bg-[var(--color-muted)] px-2 py-0.5 text-[11.5px] text-[var(--text-secondary)]"
                      >
                        {prog.name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[12px] italic text-[var(--text-faint)]">
                    Sin programas — sus proyectos cuelgan directo del portafolio.
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Programas" iconName="git-branch" count={data.programs.length}>
        {data.programs.length === 0 ? (
          <p className="px-4 py-6 text-center text-[13px] text-[var(--text-tertiary)]">
            Sin programas.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-[13px]">
              <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
                <tr>
                  <th className="h-8.5 px-4">Programa</th>
                  <th className="h-8.5 w-28 px-4">Estado</th>
                  <th className="h-8.5 w-40 pl-4 pr-3.5 text-right">Proyectos activos</th>
                </tr>
              </thead>
              <tbody>
                {data.programs.map((p) => (
                  <tr
                    key={p.id}
                    className="h-11 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
                  >
                    <td className="min-w-0 px-4">
                      <Link
                        href={`/pmo/programs/${p.id}?ctx=admin`}
                        className="block overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--color-accent)] hover:underline"
                      >
                        {p.name}
                      </Link>
                      {p.description ? (
                        <div className="overflow-hidden text-ellipsis whitespace-nowrap text-[12px] text-[var(--text-tertiary)]">
                          {p.description}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4">
                      {p.is_active ? (
                        <Badge variant="success">Activo</Badge>
                      ) : (
                        <Badge variant="danger">Inactivo</Badge>
                      )}
                    </td>
                    <td className="pl-4 pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                      {p.active_project_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Proyectos" iconName="folder" count={data.projects.length}>
        {data.projects.length === 0 ? (
          <p className="px-4 py-6 text-center text-[13px] text-[var(--text-tertiary)]">
            Sin proyectos todavía.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-[13px]">
              <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
                <tr>
                  <th className="h-8.5 px-4">Proyecto</th>
                  <th className="h-8.5 w-32 px-4">Fase</th>
                  <th className="h-8.5 w-16 px-4 text-center">Salud</th>
                  <th className="h-8.5 w-40 px-4">PM</th>
                </tr>
              </thead>
              <tbody>
                {data.projects.map((p) => (
                  <tr
                    key={p.id}
                    className="h-11 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
                  >
                    <td className="min-w-0 px-4">
                      <div className="flex min-w-0 flex-col">
                        <Link
                          href={`/pmo/projects/${p.id}?ctx=admin`}
                          className="block overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)] hover:text-[var(--color-accent)] hover:underline"
                        >
                          {p.name}
                        </Link>
                        <span className="text-[12px] tracking-[0.01em] text-[var(--text-tertiary)]">
                          {p.folio ?? "—"}
                        </span>
                      </div>
                    </td>
                    <td className="px-4">{phaseBadge(p.phase)}</td>
                    <td className="px-4">
                      <div className="flex justify-center">{healthBadge(p.health_status)}</div>
                    </td>
                    <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 text-[12.5px] text-[var(--text-secondary)]">
                      {p.pm_name ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Usuarios con rol en la organización"
        iconName="users"
        count={data.users.length}
      >
        {data.users.length === 0 ? (
          <p className="px-4 py-6 text-center text-[13px] text-[var(--text-tertiary)]">
            Nadie asignado a proyectos de esta organización todavía.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {data.users.map((u) => (
              <li
                key={u.id}
                className="flex min-h-11 items-center justify-between gap-2 px-4 py-2"
              >
                <div className="min-w-0">
                  <div className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                    {u.full_name ?? u.email ?? u.id}
                  </div>
                  {u.email ? (
                    <div className="truncate text-[12px] text-[var(--text-tertiary)]">
                      {u.email}
                    </div>
                  ) : null}
                </div>
                <Badge variant="neutral">{u.role}</Badge>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
