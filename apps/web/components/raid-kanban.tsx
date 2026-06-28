"use client";

// US-174: tablero Kanban genérico para RAID (Riesgos/Acciones/Incidentes/
// Decisiones). Drag & drop nativo (sin librería) para avanzar/retroceder de
// fase. Las columnas son los estados del tipo; soltar una tarjeta en otra
// columna dispara `onMove(id, nuevoEstado)`.
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type KanbanColumn = { id: string; label: string };

export type KanbanItem = {
  id: string;
  status: string;
  folio: string;
  title: string;
  accent?: ReactNode;
  href?: string;
};

export function RaidKanban({
  columns,
  items,
  onMove,
  busyId,
}: {
  columns: KanbanColumn[];
  items: KanbanItem[];
  onMove: (id: string, toStatus: string) => void;
  busyId?: string | null;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [overCol, setOverCol] = useState<string | null>(null);

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {columns.map((col) => {
        const colItems = items.filter((i) => i.status === col.id);
        return (
          <div
            key={col.id}
            onDragOver={(e) => {
              e.preventDefault();
              setOverCol(col.id);
            }}
            onDragLeave={() => setOverCol((c) => (c === col.id ? null : c))}
            onDrop={() => {
              if (dragId) {
                const cur = items.find((i) => i.id === dragId);
                if (cur && cur.status !== col.id) onMove(dragId, col.id);
              }
              setDragId(null);
              setOverCol(null);
            }}
            className={cn(
              "flex min-w-[14rem] flex-1 flex-col rounded-[var(--radius-md)] border bg-[var(--color-subtle)] p-2",
              overCol === col.id
                ? "border-[var(--color-primary)]"
                : "border-[var(--border-default)]",
            )}
          >
            <header className="mb-2 flex items-center justify-between px-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-secondary)]">
              <span>{col.label}</span>
              <span className="tabular-nums text-[var(--color-tertiary)]">
                {colItems.length}
              </span>
            </header>
            <div className="flex flex-col gap-2">
              {colItems.map((it) => (
                <div
                  key={it.id}
                  draggable
                  onDragStart={() => setDragId(it.id)}
                  onDragEnd={() => {
                    setDragId(null);
                    setOverCol(null);
                  }}
                  className={cn(
                    "cursor-grab rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2 shadow-[var(--shadow-sm)] active:cursor-grabbing",
                    busyId === it.id && "opacity-50",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-[var(--color-tertiary)]">
                      {it.folio}
                    </span>
                    {it.accent}
                  </div>
                  {it.href ? (
                    <Link
                      href={it.href}
                      className="mt-1 block text-xs text-[var(--color-primary)] hover:text-[var(--color-accent)] hover:underline"
                    >
                      {it.title}
                    </Link>
                  ) : (
                    <span className="mt-1 block text-xs text-[var(--color-primary)]">
                      {it.title}
                    </span>
                  )}
                </div>
              ))}
              {colItems.length === 0 ? (
                <p className="px-1 py-2 text-[11px] italic text-[var(--color-tertiary)]">
                  —
                </p>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
