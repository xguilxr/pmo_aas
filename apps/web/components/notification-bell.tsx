"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Icono } from "@/components/ui/icono";
import { cn } from "@/lib/cn";
import {
  NOTIFICATION_TYPE_LABEL,
  getUnreadCount,
  listNotifications,
  markAllRead,
  markRead,
  type NotificationItem,
} from "@/lib/api/notifications";

const POLL_MS = 30_000;

function timeAgo(iso: string): string {
  const ts = new Date(iso).getTime();
  const secs = Math.max(0, Math.round((Date.now() - ts) / 1000));
  if (secs < 60) return `hace ${secs}s`;
  const mins = Math.round(secs / 60);
  if (mins < 60) return `hace ${mins}m`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `hace ${days}d`;
  return new Date(iso).toLocaleDateString("es-MX");
}

export function NotificationBell() {
  const [count, setCount] = useState(0);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  // Polling de unread count (cada 30s).
  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const r = await getUnreadCount();
        if (!cancelled) setCount(r.count);
      } catch {
        /* silencioso: no romper el topbar si la auth aún no está lista */
      }
    }
    void tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // Carga las últimas 20 al abrir.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    listNotifications({ limit: 20 })
      .then((r) => {
        if (!cancelled) setItems(r);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Click fuera cierra.
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  async function handleRead(n: NotificationItem) {
    if (n.is_read) return;
    try {
      await markRead(n.id);
      setItems((prev) =>
        prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)),
      );
      setCount((c) => Math.max(0, c - 1));
    } catch {
      /* ignorar */
    }
  }

  async function handleMarkAll() {
    try {
      await markAllRead();
      setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
      setCount(0);
    } catch {
      /* ignorar */
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Notificaciones"
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex h-[34px] w-[34px] items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
      >
        <Icono nombre="bell" size={15} />
        {count > 0 ? (
          <span
            className="absolute right-1 top-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-danger-fg)] px-1 text-[10px] font-semibold text-[var(--color-inverse)]"
            aria-label={`${count} notificaciones sin leer`}
          >
            {count > 99 ? "99+" : count}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-[360px] overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-lg)]"
        >
          <header className="flex items-center justify-between border-b border-[var(--border-default)] px-4 py-3">
            <h3 className="text-sm font-semibold text-[var(--color-primary)]">
              Notificaciones
            </h3>
            <button
              type="button"
              onClick={handleMarkAll}
              disabled={count === 0}
              className="inline-flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline disabled:cursor-not-allowed disabled:text-[var(--color-tertiary)] disabled:no-underline"
            >
              <Icono nombre="check" size={13} /> Marcar todas
            </button>
          </header>

          <div className="max-h-[420px] overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-4 py-10 text-center text-xs text-[var(--color-tertiary)]">
                Sin notificaciones.
              </div>
            ) : (
              <ul className="divide-y divide-[var(--border-subtle)]">
                {items.map((n) => {
                  const content = (
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "h-1.5 w-1.5 shrink-0 rounded-full",
                            n.is_read
                              ? "bg-transparent"
                              : "bg-[var(--color-accent)]",
                          )}
                          aria-hidden
                        />
                        <span className="text-xs font-medium text-[var(--color-primary)]">
                          {n.title}
                        </span>
                      </div>
                      {n.body ? (
                        <p className="line-clamp-2 pl-3.5 text-[11px] text-[var(--color-tertiary)]">
                          {n.body}
                        </p>
                      ) : null}
                      <div className="flex items-center justify-between pl-3.5 pt-0.5">
                        <span className="text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
                          {NOTIFICATION_TYPE_LABEL[n.type] ?? n.type}
                        </span>
                        <span className="text-[10px] text-[var(--color-tertiary)]">
                          {timeAgo(n.created_at)}
                        </span>
                      </div>
                    </div>
                  );
                  return (
                    <li key={n.id} className="hover:bg-[var(--color-subtle)]">
                      {n.link ? (
                        <Link
                          href={n.link}
                          onClick={() => {
                            void handleRead(n);
                            setOpen(false);
                          }}
                          className="block px-4 py-3"
                        >
                          {content}
                        </Link>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleRead(n)}
                          className="block w-full px-4 py-3 text-left"
                        >
                          {content}
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <footer className="border-t border-[var(--border-default)] bg-[var(--color-subtle)]/30">
            <Link
              href="/notifications"
              onClick={() => setOpen(false)}
              className="block px-4 py-2 text-center text-xs font-medium text-[var(--color-accent)] hover:underline"
            >
              Ver todas
            </Link>
          </footer>
        </div>
      ) : null}
    </div>
  );
}
