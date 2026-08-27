"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  NOTIFICATION_TYPE_LABEL,
  listNotifications,
  markAllRead,
  markRead,
  type NotificationItem,
} from "@/lib/api/notifications";

type Filter = "all" | "unread" | "read";

export default function NotificationsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [rows, setRows] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const is_read =
        filter === "unread" ? false : filter === "read" ? true : undefined;
      const r = await listNotifications({ is_read, limit: 100 });
      setRows(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function handleRead(n: NotificationItem) {
    if (n.is_read) return;
    await markRead(n.id);
    setRows((prev) =>
      prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)),
    );
  }

  async function handleMarkAll() {
    await markAllRead();
    setRows((prev) => prev.map((x) => ({ ...x, is_read: true })));
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.25">
          <Icono nombre="bell" size={20} className="text-[var(--text-primary)]" />
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Notificaciones
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Select
            aria-label="Filtro"
            value={filter}
            onChange={(e) => setFilter(e.target.value as Filter)}
          >
            <option value="all">Todas</option>
            <option value="unread">No leídas</option>
            <option value="read">Leídas</option>
          </Select>
          <Button variant="secondary" size="sm" onClick={handleMarkAll}>
            <Icono nombre="check" size={14} /> Marcar todas
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-16 text-center text-[13px] text-[var(--text-tertiary)]">
            Sin notificaciones para el filtro actual.
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {rows.map((n) => {
              const inner = (
                <div className="flex items-start gap-3 px-5 py-4">
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      n.is_read ? "bg-transparent" : "bg-[var(--color-accent)]"
                    }`}
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] font-medium text-[var(--text-primary)]">
                        {n.title}
                      </span>
                      <Badge variant="neutral">
                        {NOTIFICATION_TYPE_LABEL[n.type] ?? n.type}
                      </Badge>
                    </div>
                    {n.body ? (
                      <p className="mt-0.5 text-[13px] text-[var(--text-tertiary)]">
                        {n.body}
                      </p>
                    ) : null}
                    <div className="mt-1 text-[11px] text-[var(--text-faint)]">
                      {new Date(n.created_at).toLocaleString("es-MX")}
                    </div>
                  </div>
                </div>
              );
              return (
                <li key={n.id} className="hover:bg-[var(--color-subtle)]">
                  {n.link ? (
                    <Link
                      href={n.link}
                      onClick={() => void handleRead(n)}
                      className="block"
                    >
                      {inner}
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={() => void handleRead(n)}
                      className="block w-full text-left"
                    >
                      {inner}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
