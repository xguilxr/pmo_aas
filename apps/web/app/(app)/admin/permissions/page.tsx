"use client";

/**
 * US-078 + DEC-024 — página informativa de permisos del tenant.
 *
 * Read-only por diseño: post-DEC-024 los permisos son estáticos en
 * código (5 capabilities admin). Si un tenant necesita una excepción
 * puntual, el superadmin la crea desde
 * `/superadmin/tenants/[id]/permissions` (DEC-021 / US-073).
 */

import { Check, Minus, ShieldCheck } from "lucide-react";

import { Breadcrumb } from "@/components/ui/breadcrumb";

type CapabilityRow = {
  capability: string;
  label: string;
  description: string;
  admin: boolean;
  user: boolean;
};

const ROWS: CapabilityRow[] = [
  {
    capability: "tenant.manage",
    label: "Tenant",
    description:
      "Editar branding, settings, y configuración general del tenant.",
    admin: true,
    user: false,
  },
  {
    capability: "ai.configure",
    label: "Configuración de IA",
    description:
      "Configurar proveedores y modos de IA (Groq / BYO / disabled).",
    admin: true,
    user: false,
  },
  {
    capability: "users.manage",
    label: "Usuarios",
    description:
      "Alta, edición, desactivación, reset de password, asignación de rol y de organizaciones.",
    admin: true,
    user: false,
  },
  {
    capability: "organizations.delete",
    label: "Borrar organizaciones",
    description:
      "Eliminar organizaciones del tenant. Crear y editar lo puede cualquier user.",
    admin: true,
    user: false,
  },
  {
    capability: "audit.read",
    label: "Auditoría",
    description: "Ver el log completo de auditoría del tenant.",
    admin: true,
    user: false,
  },
  {
    capability: "_default_",
    label: "Todo lo demás",
    description:
      "Proyectos, tareas, riesgos, issues, change requests, documentos, minutas, lecciones, áreas, dashboard, IA generación, requests, charters, reports, importación de planes, organizaciones (crear/editar). Cualquier user del tenant.",
    admin: true,
    user: true,
  },
];

function YesNo({ ok }: { ok: boolean }) {
  return ok ? (
    <Check className="mx-auto h-5 w-5 text-emerald-600" aria-label="Sí" />
  ) : (
    <Minus className="mx-auto h-5 w-5 text-[var(--color-tertiary)]" aria-label="No" />
  );
}

export default function PermissionsPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin", label: "Admin" },
          { label: "Permisos" },
        ]}
      />
      <div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-[var(--color-primary)]" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Permisos del tenant
          </h1>
        </div>
        <p className="mt-2 text-sm text-[var(--color-secondary)]">
          PMO·aaS usa un modelo de <strong>capabilities fijas</strong>: el rol{" "}
          <code className="rounded bg-[var(--color-bg-muted)] px-1">admin</code>{" "}
          tiene 5 capabilities adicionales sobre el rol{" "}
          <code className="rounded bg-[var(--color-bg-muted)] px-1">user</code>.
          Todo lo demás está disponible para cualquier usuario autenticado del
          tenant.
        </p>
      </div>

      <div className="rounded-lg border border-[var(--border-default)] bg-[var(--color-bg-surface)] shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-default)] bg-[var(--color-bg-muted)]">
              <th className="px-4 py-3 text-left font-medium text-[var(--color-secondary)]">
                Capability
              </th>
              <th className="px-4 py-3 text-center font-medium text-[var(--color-secondary)]">
                Admin
              </th>
              <th className="px-4 py-3 text-center font-medium text-[var(--color-secondary)]">
                User
              </th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr
                key={row.capability}
                className="border-b border-[var(--border-default)] last:border-0"
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--color-primary)]">
                    {row.label}
                  </div>
                  <div className="mt-0.5 text-xs text-[var(--color-secondary)]">
                    {row.description}
                  </div>
                  {row.capability !== "_default_" && (
                    <code className="mt-1 inline-block text-xs text-[var(--color-tertiary)]">
                      {row.capability}
                    </code>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <YesNo ok={row.admin} />
                </td>
                <td className="px-4 py-3 text-center">
                  <YesNo ok={row.user} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-lg border border-[var(--border-default)] bg-[var(--color-bg-muted)] p-4 text-sm text-[var(--color-secondary)]">
        <p>
          <strong>¿Necesitas una excepción puntual?</strong> Las capabilities son
          fijas a nivel de plataforma (DEC-024). Si tu tenant necesita un
          override (ej. dar a un user específico la capability{" "}
          <code>organizations.delete</code>), debes contactar al superadmin de la
          plataforma para que registre el override en{" "}
          <code>tenant_role_permission_overrides</code> (DEC-021).
        </p>
      </div>
    </div>
  );
}
