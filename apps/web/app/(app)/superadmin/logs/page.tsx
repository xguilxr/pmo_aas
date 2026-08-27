"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getPlatformLogs,
  type PlatformLogRow,
} from "@/lib/api/superadmin-panel";

export default function PlatformLogsPage() {
  const [rows, setRows] = useState<PlatformLogRow[]>([]);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(rows);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [streaming, setStreaming] = useState(false);

  useEffect(() => {
    let cancelled = false;
    function fetchOnce() {
      setLoading(true);
      setError(null);
      getPlatformLogs({
        q: q || undefined,
        action: action || undefined,
        tenant_id: tenantId || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
        page,
        limit: 200,
      })
        .then((r) => {
          if (!cancelled) setRows(r);
        })
        .catch((err) => {
          if (!cancelled)
            setError(err instanceof ApiError ? err.message : "No se pudieron cargar los logs");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }
    fetchOnce();
    if (streaming) {
      const t = setInterval(fetchOnce, 5_000);
      return () => {
        cancelled = true;
        clearInterval(t);
      };
    }
    return () => {
      cancelled = true;
    };
  }, [q, action, tenantId, dateFrom, dateTo, page, streaming]);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex items-center gap-2.25">
          <Icono nombre="file-text" size={20} className="text-[var(--text-primary)]" />
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
              Logs platform-wide
            </h1>
            {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
            <p className="text-[13px] text-[var(--text-tertiary)]">
              Eventos de todos los tenants + plataforma. Con tenant_id vacío ves todos los tenants.
            </p>
          </div>
        </div>
        <label className="inline-flex h-8 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-[12.5px] text-[var(--text-secondary)] shadow-[var(--relieve-control)]">
          <Icono
            nombre="circle-activity"
            size={14}
            className={streaming ? "text-[var(--color-accent)]" : "text-[var(--text-tertiary)]"}
          />
          <input
            type="checkbox"
            checked={streaming}
            onChange={(e) => setStreaming(e.target.checked)}
          />
          Stream (refresh 5 s)
        </label>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 md:grid-cols-5">
          <Input
            placeholder="Acción (q fuzzy)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <Input
            placeholder="Acción exacta"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
          <Input
            placeholder="Tenant ID"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
          />
          <Input
            type="datetime-local"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            aria-label="Desde"
          />
          <Input
            type="datetime-local"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            aria-label="Hasta"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
              <tr>
                <th className="h-8.5 px-4 font-medium">Cuándo</th>
                <th className="h-8.5 px-4 font-medium">Acción</th>
                <th className="h-8.5 px-4 font-medium">Módulo</th>
                <th className="h-8.5 px-4 font-medium">Tenant</th>
                <th className="h-8.5 px-4 font-medium">Entidad</th>
                <th className="h-8.5 px-4 font-medium">Detalles</th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="h-11 border-b border-[var(--border-subtle)]">
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-4">
                          <Skeleton className="h-3 w-16" />
                        </td>
                      ))}
                    </tr>
                  ))
                : rows.map((r) => (
                    <tr
                      key={r.id}
                      className="h-11 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
                    >
                      <td className="px-4 font-mono text-[11px] text-[var(--text-secondary)]">
                        {r.occurred_at ? new Date(r.occurred_at).toLocaleString("es-MX") : "—"}
                      </td>
                      <td className="px-4">
                        <Badge>{r.action}</Badge>
                      </td>
                      <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 text-[var(--text-secondary)]">
                        {r.module ?? "—"}
                      </td>
                      <td className="px-4 font-mono text-[11px] text-[var(--text-tertiary)]">
                        {r.tenant_id ? r.tenant_id.slice(0, 8) : "—"}
                      </td>
                      <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 text-[var(--text-secondary)]">
                        {r.entity_type ?? "—"}
                        {r.entity_id ? (
                          <span className="ml-1 font-mono text-[11px] text-[var(--text-tertiary)]">
                            · {r.entity_id.slice(0, 8)}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 text-[var(--text-tertiary)]">
                        {r.details ? (
                          <span className="block overflow-hidden text-ellipsis whitespace-nowrap font-mono text-[11px]">
                            {JSON.stringify(r.details)}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
              {!loading && rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-[var(--text-tertiary)]">
                    Sin eventos.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <footer className="flex items-center justify-between gap-3 border-t border-[var(--border-subtle)] px-4 py-3 text-[12px] text-[var(--text-secondary)]">
          <span>
            Página <span className="font-semibold text-[var(--text-primary)]">{page}</span> ·{" "}
            {rows.length} eventos
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={rows.length < 200 || loading}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        </footer>
      </section>
    </div>
  );
}
