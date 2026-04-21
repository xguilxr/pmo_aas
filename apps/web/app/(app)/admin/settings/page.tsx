"use client";

import { Cog } from "lucide-react";

import { TenantSettingsForm } from "@/components/tenant-settings-form";

/**
 * Ruta legacy — se mantiene para compatibilidad con links existentes.
 * El sidebar ahora la sirve integrada como tab "Configuración" bajo
 * `/admin/tenant?tab=config` (US-036).
 */
export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="flex items-center gap-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--text-secondary)]">
          <Cog className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Configuración del tenant
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Preferencias globales de la organización: idioma, moneda, timezone, color corporativo
            y proveedor de IA.
          </p>
        </div>
      </header>
      <TenantSettingsForm />
    </div>
  );
}
