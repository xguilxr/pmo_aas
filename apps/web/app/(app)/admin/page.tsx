"use client";

import Link from "next/link";
import {
  Bot,
  Building2,
  ClipboardList,
  Network,
  Settings2,
  ShieldCheck,
  Users,
} from "lucide-react";

/**
 * US-094 — Landing /admin con grid de paneles a las 6 secciones admin.
 *
 * Sustituye al "redirect implícito" anterior (no había page.tsx en
 * `/admin`, los usuarios sólo entraban vía sidebar). El layout es
 * análogo al landing PMO (`/pmo/page.tsx`).
 *
 * ENH-062: las labels prescinden del prefijo "Gestión de" — la página
 * admin ya implica gestión.
 */
const PANELS = [
  {
    href: "/admin/tenant",
    label: "Tenant",
    description:
      "Datos generales del tenant, branding, dominio y políticas globales.",
    icon: Settings2,
  },
  {
    href: "/admin/ai",
    label: "IA",
    description:
      "Proveedor de IA, API key y configuración de prompts del tenant.",
    icon: Bot,
  },
  {
    href: "/admin/organizations",
    label: "Organizaciones",
    description:
      "Alta, edición y jerarquía de las organizaciones del tenant.",
    icon: Building2,
  },
  {
    href: "/admin/users",
    label: "Usuarios",
    description:
      "Usuarios del tenant: alta, roles, contraseñas y exclusiones.",
    icon: Users,
  },
  {
    href: "/admin/areas",
    label: "Áreas",
    description:
      "Catálogo Áreas → Equipos → Actores reutilizable a través de proyectos.",
    icon: Network,
  },
  {
    href: "/admin/permissions",
    label: "Permisos",
    description:
      "Matriz de permisos por rol y módulo. Control de acceso granular.",
    icon: ShieldCheck,
  },
  {
    href: "/admin/audit-logs",
    label: "Auditoría",
    description:
      "Histórico de acciones por usuario, módulo y entidad.",
    icon: ClipboardList,
  },
] as const;

export default function AdminLanding() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Admin
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Configuración del tenant: organizaciones, usuarios, permisos y
          observabilidad. Selecciona una sección para empezar.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {PANELS.map((p) => {
          const Icon = p.icon;
          return (
            <Link
              key={p.href}
              href={p.href}
              className="group flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--color-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 flex-none items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)] group-hover:text-[var(--color-accent)]">
                  <Icon className="h-5 w-5" aria-hidden />
                </div>
                <span className="text-sm font-semibold text-[var(--color-primary)] group-hover:text-[var(--color-accent)]">
                  {p.label}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-[var(--color-tertiary)]">
                {p.description}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
