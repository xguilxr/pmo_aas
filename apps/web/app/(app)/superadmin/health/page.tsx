"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
import { KpiBand } from "@/components/kpi-card";
import { getStoredUser } from "@/lib/auth-storage";
import { SIN_DATO } from "@/lib/sin-dato";

/**
 * Superadmin · Sistema — pantalla nueva (mockup 6f, diseño aspiracional).
 *
 * US-026 consolidó el health check de plataforma en /superadmin (Visión
 * general → `SuperadminHealthSection`, que sigue viviendo ahí). Esta ruta
 * era desde entonces un redirect permanente para no romper bookmarks; se
 * repropone aquí como la vista de sistema que pide el mockup —versión
 * desplegada, migraciones, colas de jobs e incidentes— en vez de duplicar
 * el grid de servicios que ya muestra la Visión general.
 *
 * Ningún dato de esta pantalla tiene endpoint real todavía (ni versión
 * desplegada, ni head de Alembic, ni colas de Celery, ni incidentes): se
 * marca cada uno `SIN_DATO` + leyenda en vez de inventar una cifra o fila.
 */
export default function SuperadminSystemPage() {
  const user = getStoredUser();

  if (user && !user.is_superadmin) {
    return (
      <div>
        <Banner variant="danger">Solo Super Admin puede acceder a este panel.</Banner>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Sistema
        </h1>
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Versión desplegada, migraciones, cola de jobs asíncronos e historial de incidentes.
        </p>
      </header>

      <KpiBand className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <PendingKpi label="Versión desplegada" icon="tag" />
        <PendingKpi label="Última migración" icon="git-branch" />
        <PendingKpi label="Jobs pendientes" icon="clock" />
        <PendingKpi label="Jobs fallidos (24h)" icon="circle-x" />
      </KpiBand>

      <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <header className="flex h-9.5 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Colas (Celery)
          </h2>
          <span className="text-[10.5px] italic text-[var(--text-faint)]">
            pendiente de backend — extiende el health card «Worker» de Visión general
          </span>
        </header>
        <div
          className="grid h-8 shrink-0 items-center gap-2 border-b border-[var(--border-default)] bg-[var(--color-subtle)] px-4 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]"
          style={{ gridTemplateColumns: "minmax(160px,1fr) 120px 120px 200px" }}
        >
          <span>Cola</span>
          <span className="text-right pr-3.5">Pendientes</span>
          <span className="text-right pr-3.5">Fallidos</span>
          <span>Job más antiguo</span>
        </div>
        <ul className="flex flex-col divide-y divide-[var(--border-subtle)]">
          {/* Nombres de módulo reales (app/workers/tasks/*.py); los valores
              son SIN_DATO porque no hay instrumentación de colas hoy. */}
          {["notifications", "ai", "scheduled_reports"].map((cola) => (
            <li
              key={cola}
              className="grid h-9.5 items-center gap-2 px-4"
              style={{ gridTemplateColumns: "minmax(160px,1fr) 120px 120px 200px" }}
            >
              <span className="overflow-hidden text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-primary)]">
                {cola}
              </span>
              <span className="text-right pr-3.5 font-mono text-[12.5px] text-[var(--text-faint)]">
                {SIN_DATO}
              </span>
              <span className="text-right pr-3.5 font-mono text-[12.5px] text-[var(--text-faint)]">
                {SIN_DATO}
              </span>
              <span className="text-[12px] text-[var(--text-faint)]">{SIN_DATO}</span>
            </li>
          ))}
        </ul>
      </article>

      <article className="flex flex-1 flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <header className="flex h-9.5 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Historial de incidentes
          </h2>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled
            title="Pendiente de backend: todavía no hay tabla de incidentes"
          >
            Declarar incidente
          </Button>
        </header>
        <div
          className="grid h-8 shrink-0 items-center gap-2 border-b border-[var(--border-default)] bg-[var(--color-subtle)] px-4 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]"
          style={{ gridTemplateColumns: "150px 100px minmax(260px,1fr) 130px 110px" }}
        >
          <span>Cuándo</span>
          <span>Severidad</span>
          <span>Descripción</span>
          <span>Duración</span>
          <span>Estado</span>
        </div>
        <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
          <Icono nombre="octagon-alert" size={17} className="text-[var(--text-faint)]" />
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Sin tabla de incidentes todavía.
          </p>
          <Badge variant="neutral">pendiente de backend</Badge>
        </div>
        <p className="border-t border-[var(--border-subtle)] px-4 py-2 text-[10.5px] italic text-[var(--text-faint)] shadow-[var(--linea-surco-arriba)]">
          pendiente de backend — hoy no hay tabla de incidentes, se reconstruye de logs y memoria
          del equipo
        </p>
      </article>
    </div>
  );
}

/** KPI sin endpoint real: SIN_DATO + leyenda, nunca una cifra inventada. */
function PendingKpi({ label, icon }: { label: string; icon: string }) {
  return (
    <div className="flex h-full flex-col gap-2 p-4">
      <div className="flex items-center justify-between">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
          {label}
        </span>
        <span className="text-[var(--text-tertiary)]">
          <Icono nombre={icon} size={13} />
        </span>
      </div>
      <span className="font-mono text-[26px] font-medium tabular-nums text-[var(--text-faint)]">
        {SIN_DATO}
      </span>
      <span className="text-[11px] italic text-[var(--text-faint)]">pendiente de backend</span>
    </div>
  );
}
