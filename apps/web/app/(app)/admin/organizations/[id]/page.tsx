"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Building2,
  FolderKanban,
  Mail,
  Network,
  Pencil,
  Users,
  Workflow,
} from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
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
  icon,
  count,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
        {icon}
        {title}
        {typeof count === "number" ? (
          <span className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-xs font-medium text-[var(--color-tertiary)]">
            {count}
          </span>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function healthBadge(health: string | null) {
  if (!health) return null;
  // ENH-110: salud = solo el color (círculo), sin la palabra.
  const color =
    health === "green"
      ? "bg-[var(--color-success-fg)]"
      : health === "yellow"
        ? "bg-[var(--color-warning-fg)]"
        : "bg-[var(--color-danger-fg)]";
  const label =
    health === "green" ? "Verde" : health === "yellow" ? "Amarillo" : health === "red" ? "Rojo" : health;
  return (
    <span
      title={label}
      aria-label={label}
      role="img"
      className={`inline-block h-2.5 w-2.5 rounded-full ${color}`}
    />
  );
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
          <div className="flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
            {data.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={data.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <Building2 className="h-6 w-6" aria-hidden />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              {data.name}
            </h1>
            {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
            <div className="mt-1 flex items-center gap-2 text-xs text-[var(--color-tertiary)]">
              {[data.industry, data.country].filter(Boolean).join(" · ") ||
                "Sin datos"}
              {!data.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
            </div>
            {data.contact_email ? (
              <a
                href={`mailto:${data.contact_email}`}
                className="mt-1 inline-flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
              >
                <Mail className="h-3 w-3" aria-hidden /> {data.contact_email}
              </a>
            ) : null}
          </div>
        </div>
        {canEdit ? (
          <Link href={`/admin/organizations/${data.id}/edit`}>
            <Button variant="secondary">
              <Pencil className="h-4 w-4" aria-hidden /> Editar
            </Button>
          </Link>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4">
          <div className="text-xs text-[var(--color-tertiary)]">Portafolios</div>
          <div className="text-2xl font-semibold tabular-nums">
            {data.portfolios.length}
          </div>
        </div>
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4">
          <div className="text-xs text-[var(--color-tertiary)]">Programas</div>
          <div className="text-2xl font-semibold tabular-nums">{totalProgramas}</div>
        </div>
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4">
          <div className="text-xs text-[var(--color-tertiary)]">Proyectos</div>
          <div className="text-2xl font-semibold tabular-nums">
            {data.projects.length}
          </div>
        </div>
      </div>

      <SectionCard
        title="Portafolios"
        icon={<Workflow className="h-4 w-4" aria-hidden />}
        count={data.portfolios.length}
      >
        {data.portfolios.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Sin portafolios configurados.
          </p>
        ) : (
          <ul className="space-y-3">
            {data.portfolios.map((pf) => (
              <li
                key={pf.id}
                className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-[var(--color-primary)]">
                    {pf.name}
                  </span>
                  {pf.code ? <Badge variant="neutral">{pf.code}</Badge> : null}
                  <span className="text-xs text-[var(--color-tertiary)]">
                    {pf.active_project_count} proyecto
                    {pf.active_project_count === 1 ? "" : "s"} activo
                    {pf.active_project_count === 1 ? "" : "s"}
                  </span>
                </div>
                {pf.description ? (
                  <p className="mt-1 text-xs text-[var(--color-tertiary)]">
                    {pf.description}
                  </p>
                ) : null}
                {pf.programs.length > 0 ? (
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {pf.programs.map((prog) => (
                      <li
                        key={prog.id}
                        className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-xs text-[var(--color-secondary)]"
                      >
                        {prog.name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-xs italic text-[var(--color-tertiary)]">
                    Sin programas — sus proyectos cuelgan directo del portafolio.
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard
        title="Programas"
        icon={<Network className="h-4 w-4" aria-hidden />}
        count={data.programs.length}
      >
        {data.programs.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Sin programas.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="py-2">Programa</th>
                <th className="py-2">Estado</th>
                <th className="py-2 text-right">Proyectos activos</th>
              </tr>
            </thead>
            <tbody>
              {data.programs.map((p) => (
                <tr
                  key={p.id}
                  className="border-t border-[var(--border-subtle)]"
                >
                  <td className="py-2">
                    <Link
                      href={`/pmo/programs/${p.id}?ctx=admin`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      {p.name}
                    </Link>
                    {p.description ? (
                      <div className="text-xs text-[var(--color-tertiary)]">
                        {p.description}
                      </div>
                    ) : null}
                  </td>
                  <td className="py-2">
                    {p.is_active ? (
                      <Badge variant="success">activo</Badge>
                    ) : (
                      <Badge variant="danger">inactivo</Badge>
                    )}
                  </td>
                  <td className="py-2 text-right tabular-nums">
                    {p.active_project_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>

      <SectionCard
        title="Proyectos"
        icon={<FolderKanban className="h-4 w-4" aria-hidden />}
        count={data.projects.length}
      >
        {data.projects.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Sin proyectos todavía.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="py-2">Folio</th>
                <th className="py-2">Nombre</th>
                <th className="py-2">Fase</th>
                <th className="py-2">Salud</th>
                <th className="py-2">PM</th>
              </tr>
            </thead>
            <tbody>
              {data.projects.map((p) => (
                <tr
                  key={p.id}
                  className="border-t border-[var(--border-subtle)]"
                >
                  <td className="py-2 font-mono text-xs">{p.folio ?? "—"}</td>
                  <td className="py-2">
                    <Link
                      href={`/pmo/projects/${p.id}?ctx=admin`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      {p.name}
                    </Link>
                  </td>
                  <td className="py-2">{p.phase ?? "—"}</td>
                  <td className="py-2">{healthBadge(p.health_status)}</td>
                  <td className="py-2">{p.pm_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>

      <SectionCard
        title="Usuarios con rol en la organización"
        icon={<Users className="h-4 w-4" aria-hidden />}
        count={data.users.length}
      >
        {data.users.length === 0 ? (
          <p className="text-sm text-[var(--color-tertiary)]">
            Nadie asignado a proyectos de esta organización todavía.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {data.users.map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <div className="font-medium text-[var(--color-primary)]">
                    {u.full_name ?? u.email ?? u.id}
                  </div>
                  {u.email ? (
                    <div className="text-xs text-[var(--color-tertiary)]">
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
