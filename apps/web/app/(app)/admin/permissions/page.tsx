"use client";

/**
 * US-078 + DEC-024 — página informativa de permisos del tenant.
 *
 * Read-only por diseño: post-DEC-024 los permisos son estáticos en
 * código (5 capabilities admin). Si un tenant necesita una excepción
 * puntual, el superadmin la crea desde
 * `/superadmin/tenants/[id]/permissions` (DEC-021 / US-073).
 */

import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Icono } from "@/components/ui/icono";

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
    <Icono
      nombre="check"
      size={16}
      className="mx-auto text-[var(--color-success-fg)]"
    />
  ) : (
    <span className="text-[16px] text-[var(--text-faint)]" aria-label="No">
      —
    </span>
  );
}

export default function PermissionsPage() {
  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin", label: "Admin" },
          { label: "Permisos" },
        ]}
      />
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2.25">
          <Icono nombre="lock" size={20} className="text-[var(--text-primary)]" />
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Permisos del tenant
          </h1>
        </div>
        <p className="max-w-[780px] text-[13.5px] leading-[1.6] text-[var(--text-secondary)]">
          PMO·aaS usa un modelo de{" "}
          <strong className="text-[var(--text-primary)]">capabilities fijas</strong>: el rol{" "}
          <code className="rounded-[4px] bg-[var(--color-muted)] px-1.25 py-0.25 font-mono text-[12.5px]">
            admin
          </code>{" "}
          tiene 5 capabilities adicionales sobre el rol{" "}
          <code className="rounded-[4px] bg-[var(--color-muted)] px-1.25 py-0.25 font-mono text-[12.5px]">
            user
          </code>
          . Todo lo demás está disponible para cualquier usuario autenticado
          del tenant.
        </p>
      </div>

      <div className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <table className="w-full">
          <thead>
            <tr className="h-9 border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-[12px] font-semibold text-[var(--text-secondary)] shadow-[var(--linea-surco)]">
              <th className="px-4.5 text-left">Capability</th>
              <th className="w-22.5 px-4.5 text-center">Admin</th>
              <th className="w-22.5 px-4.5 text-center">User</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row, i) => (
              <tr
                key={row.capability}
                className={
                  i < ROWS.length - 1
                    ? "border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]"
                    : undefined
                }
              >
                <td className="px-4.5 py-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[13px] font-medium text-[var(--text-primary)]">
                      {row.label}
                    </span>
                    <span className="text-[12px] text-[var(--text-tertiary)]">
                      {row.description}
                    </span>
                    {row.capability !== "_default_" && (
                      <span className="font-mono text-[11px] text-[var(--text-faint)]">
                        {row.capability}
                      </span>
                    )}
                  </div>
                </td>
                <td className="w-22.5 px-4.5 py-3 text-center">
                  <YesNo ok={row.admin} />
                </td>
                <td className="w-22.5 px-4.5 py-3 text-center">
                  <YesNo ok={row.user} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-start gap-2.5 rounded-[var(--radius-xl)] border border-[var(--border-default)] px-4 py-3.5 text-[13px] leading-[1.55] text-[var(--text-secondary)] shadow-[var(--linea-surco-arriba)]">
        <Icono
          nombre="info"
          size={16}
          className="mt-px flex-none text-[var(--text-tertiary)]"
        />
        <p>
          <strong className="text-[var(--text-primary)]">
            ¿Necesitas una excepción puntual?
          </strong>{" "}
          Las capabilities son fijas a nivel de plataforma (DEC-024). Si tu
          tenant necesita un override (ej. dar a un user específico la
          capability <code className="font-mono">organizations.delete</code>),
          debes contactar al superadmin de la plataforma para que registre el
          override en{" "}
          <code className="font-mono">tenant_role_permission_overrides</code>{" "}
          (DEC-021).
        </p>
      </div>
    </div>
  );
}
