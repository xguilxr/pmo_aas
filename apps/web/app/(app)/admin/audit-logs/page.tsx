"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import { auditLogsCsvUrl, listAuditLogs, type AuditLogEntry } from "@/lib/api/admin-panel";

const ENTITY_TYPES = [
  "user",
  "role",
  "organization",
  "program",
  "project",
  "project_request",
  "risk",
  "issue",
  "change_request",
  "document",
  "lesson",
  "minute",
  "tenant",
];

export default function AuditLogsPage() {
  const [rows, setRows] = useState<AuditLogEntry[]>([]);
  const { sortedRows, ctrl: auditCtrl } = useSortableRows<AuditLogEntry>(rows);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [userId, setUserId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listAuditLogs({
      action: action || undefined,
      entity_type: entityType || undefined,
      user_id: userId || undefined,
      date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
      date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
      page,
      limit: 100,
    })
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudieron cargar los logs");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [action, entityType, userId, dateFrom, dateTo, page]);

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
  const csvHref = useMemo(() => auditLogsCsvUrl(apiBase), [apiBase]);

  return (
    <div className="space-y-5">
      <Breadcrumb
        items={[
          { href: "/admin", label: "Admin" },
          { label: "Auditoría" },
        ]}
      />
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2.25">
            <Icono nombre="file-text" size={20} className="text-[var(--text-primary)]" />
            <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
              Auditoría
            </h1>
          </div>
          <p className="max-w-[620px] text-[13.5px] leading-[1.6] text-[var(--text-secondary)]">
            Eventos registrados por el sistema, aislados por tenant. Útil para forensía y
            compliance.
          </p>
        </div>
        <a
          href={csvHref}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex h-8 items-center gap-1.75 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-[13px] font-medium text-[var(--text-primary)] shadow-[var(--relieve-control)] hover:bg-[var(--color-subtle)]"
        >
          <Icono nombre="download" size={15} /> Exportar CSV
        </a>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 md:grid-cols-5">
          <Input
            placeholder="Acción (ej: user.create)"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
          <Select value={entityType} onChange={(e) => setEntityType(e.target.value)}>
            <option value="">Todas las entidades</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
          <Input
            placeholder="User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
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
          <table className="w-full table-fixed text-[13px]">
            <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
              <tr>
                <SortableTh<AuditLogEntry> sortKey="when" getter={(r) => (r as any).created_at ?? ""} ctrl={auditCtrl} className="h-8.5 w-40 px-4">Cuándo</SortableTh>
                <SortableTh<AuditLogEntry> sortKey="action" getter={(r) => (r as any).action ?? ""} ctrl={auditCtrl} className="h-8.5 w-36 px-4">Acción</SortableTh>
                <SortableTh<AuditLogEntry> sortKey="module" getter={(r) => (r as any).module ?? ""} ctrl={auditCtrl} className="h-8.5 w-28 px-4">Módulo</SortableTh>
                <SortableTh<AuditLogEntry> sortKey="entity" getter={(r) => (r as any).entity_type ?? ""} ctrl={auditCtrl} className="h-8.5 w-36 px-4">Entidad</SortableTh>
                <SortableTh<AuditLogEntry> sortKey="user" getter={(r) => (r as any).user_email ?? ""} ctrl={auditCtrl} className="h-8.5 w-24 px-4">Usuario</SortableTh>
                <SortableTh<AuditLogEntry> sortKey="ip" getter={(r) => (r as any).ip ?? ""} ctrl={auditCtrl} className="h-8.5 w-28 px-4">IP</SortableTh>
                <th className="h-8.5 px-4 font-medium">Detalles</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="h-11 border-b border-[var(--border-subtle)]">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4">
                        <Skeleton className="h-4 w-20" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : rows.length ? (
                sortedRows.map((r) => (
                  <tr key={r.id} className="h-11 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60">
                    <td className="px-4 font-mono text-[11px] text-[var(--text-secondary)]">
                      {r.occurred_at ? new Date(r.occurred_at).toLocaleString("es-MX") : "—"}
                    </td>
                    <td className="px-4">
                      <Badge>{r.action}</Badge>
                    </td>
                    <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 text-[var(--text-secondary)]">
                      {r.module ?? "—"}
                    </td>
                    <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 text-[var(--text-secondary)]">
                      {r.entity_type ? (
                        <span>
                          {r.entity_type}
                          {r.entity_id ? (
                            <span className="ml-1 font-mono text-[11px] text-[var(--text-tertiary)]">
                              · {r.entity_id.slice(0, 8)}
                            </span>
                          ) : null}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 font-mono text-[11px] text-[var(--text-tertiary)]">
                      {r.user_id ? r.user_id.slice(0, 8) : "—"}
                    </td>
                    <td className="overflow-hidden text-ellipsis whitespace-nowrap px-4 text-[var(--text-tertiary)]">
                      {r.ip_address ?? "—"}
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
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-[var(--text-tertiary)]">
                    No hay eventos que coincidan con los filtros.
                  </td>
                </tr>
              )}
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
              disabled={rows.length < 100 || loading}
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
