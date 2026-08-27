"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { KpiBand } from "@/components/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getPlatformLogs, type PlatformLogRow } from "@/lib/api/superadmin-panel";
import { getStoredUser } from "@/lib/auth-storage";
import { SIN_DATO } from "@/lib/sin-dato";

/**
 * Superadmin · Seguridad — pantalla nueva (mockup 6e, diseño aspiracional).
 *
 * Grounding real hoy:
 * - Auditoría: `getPlatformLogs`, el mismo endpoint que alimenta
 *   /superadmin/logs — se muestran los eventos más recientes de la
 *   plataforma (no hay un filtro `actor=superadmin` en el backend, así que
 *   no se rotula como tal).
 * - Cuentas bloqueadas: el desbloqueo por tenant ya existe
 *   (`unlockUser` → `POST /admin/users/{id}/unlock`, admin_users.py), pero
 *   no hay endpoint que agregue el listado a nivel plataforma — se marca
 *   pendiente en vez de inventar filas o una cifra.
 * - Intentos fallidos agregados (24h) y sesiones activas de superadmin: sin
 *   ningún respaldo en backend hoy.
 */
export default function SuperadminSecurityPage() {
  const user = getStoredUser();
  const [logs, setLogs] = useState<PlatformLogRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const leido = useLectura(logs);

  useEffect(() => {
    let cancelled = false;
    getPlatformLogs({ limit: 8 })
      .then((rows) => {
        if (!cancelled) setLogs(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar la auditoría");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
          Seguridad
        </h1>
        {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Cuentas bloqueadas y auditoría de acciones sensibles, agregado a nivel plataforma.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <KpiBand className="grid-cols-1 sm:grid-cols-3">
        <PendingKpi label="Intentos fallidos (24h)" icon="triangle-alert" />
        <PendingKpi
          label="Cuentas bloqueadas"
          icon="lock"
          hint="pendiente de backend — el unlock por tenant ya existe en Admin → Usuarios"
        />
        <PendingKpi label="Sesiones de superadmin" icon="circle-user" />
      </KpiBand>

      <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <header className="flex h-9.5 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Cuentas bloqueadas
          </h2>
          <span className="text-[11px] text-[var(--text-tertiary)]">
            bloqueo temporal por intentos fallidos
          </span>
        </header>
        <div
          className="grid h-8 shrink-0 items-center gap-2 border-b border-[var(--border-default)] bg-[var(--color-subtle)] px-4 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]"
          style={{ gridTemplateColumns: "minmax(200px,1fr) 140px 90px 150px" }}
        >
          <span>Usuario</span>
          <span>Tenant</span>
          <span className="text-right pr-3.5">Intentos</span>
          <span>Bloqueada desde</span>
        </div>
        <p className="px-4 py-5 text-center text-[12.5px] text-[var(--text-tertiary)]">
          Sin listado agregado todavía.
          <span className="mt-1 block text-[11px] italic text-[var(--text-faint)]">
            pendiente de backend — el unlock existe por tenant (Admin → Usuarios), falta el
            endpoint que lo agregue a nivel plataforma
          </span>
        </p>
      </article>

      <article className="flex flex-1 flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <header className="flex h-9.5 items-center justify-between border-b border-[var(--border-default)] px-4 shadow-[var(--linea-surco)]">
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Auditoría de superadmin
          </h2>
          <Link
            href="/superadmin/logs"
            className="text-[11.5px] font-medium text-[var(--color-accent)] hover:underline"
          >
            Ver todo →
          </Link>
        </header>
        <div
          className="grid h-8 shrink-0 items-center gap-2 border-b border-[var(--border-default)] bg-[var(--color-subtle)] px-4 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]"
          style={{ gridTemplateColumns: "150px 190px minmax(200px,1fr)" }}
        >
          <span>Cuándo</span>
          <span>Acción</span>
          <span>Detalle</span>
        </div>
        <ul className="flex flex-col divide-y divide-[var(--border-subtle)]">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <li key={i} className="px-4 py-2.5">
                  <Skeleton className="h-4 w-full" />
                </li>
              ))
            : logs?.map((r) => (
                <li
                  key={r.id}
                  className="grid h-9.5 items-center gap-2 px-4"
                  style={{ gridTemplateColumns: "150px 190px minmax(200px,1fr)" }}
                >
                  <span className="font-mono text-[11.5px] text-[var(--text-tertiary)]">
                    {r.occurred_at ? new Date(r.occurred_at).toLocaleString("es-MX") : SIN_DATO}
                  </span>
                  <Badge className="w-fit">{r.action}</Badge>
                  <span className="overflow-hidden text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-secondary)]">
                    {r.module ?? "—"}
                    {r.tenant_id ? ` · tenant ${r.tenant_id.slice(0, 8)}` : ""}
                    {r.entity_type
                      ? ` · ${r.entity_type}${r.entity_id ? ` ${r.entity_id.slice(0, 8)}` : ""}`
                      : ""}
                  </span>
                </li>
              ))}
          {!loading && !logs?.length ? (
            <li className="px-4 py-8 text-center text-[13px] text-[var(--text-tertiary)]">
              Sin eventos.
            </li>
          ) : null}
        </ul>
      </article>
    </div>
  );
}

/** KPI sin endpoint real: SIN_DATO + leyenda, nunca una cifra inventada
 *  (mismo patrón que `PendingKpi` en /superadmin — no se comparte porque
 *  ahí no está exportado y cada uso tiene su propio texto de leyenda). */
function PendingKpi({
  label,
  icon,
  hint = "pendiente de backend",
}: {
  label: string;
  icon: string;
  hint?: string;
}) {
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
      <span className="text-[11px] italic text-[var(--text-faint)]">{hint}</span>
    </div>
  );
}
