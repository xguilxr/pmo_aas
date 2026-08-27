"use client";

// US-174: tablero Kanban genérico para RAID (Riesgos/Acciones/Incidentes/
// Decisiones). Drag & drop nativo (sin librería) para avanzar/retroceder de
// fase. Las columnas son los estados del tipo; soltar una tarjeta en otra
// columna dispara `onMove(id, nuevoEstado)`.
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Icono } from "@/components/ui/icono";
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
      {columns.map((col, ci) => {
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
            <header className="mb-2 flex h-8.5 items-center justify-between px-1 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--color-secondary)]">
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
                    "cursor-grab rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-2 shadow-[var(--relieve-isla)] active:cursor-grabbing",
                    busyId === it.id && "opacity-50",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10.5px] tracking-[0.01em] text-[var(--color-tertiary)]">
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
                  {/* Fase 3 (a11y): mover de fase con teclado/click, sin drag. */}
                  <div className="mt-2 flex items-center justify-between">
                    <button
                      type="button"
                      disabled={ci === 0 || busyId === it.id}
                      onClick={() => onMove(it.id, columns[ci - 1].id)}
                      title={ci > 0 ? `Mover a ${columns[ci - 1].label}` : undefined}
                      aria-label={
                        ci > 0
                          ? `Mover "${it.title}" a ${columns[ci - 1].label}`
                          : "Sin fase anterior"
                      }
                      className="inline-flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)] disabled:opacity-30 disabled:hover:bg-transparent"
                    >
                      <Icono nombre="chevron-left" size={14} />
                    </button>
                    <button
                      type="button"
                      disabled={ci === columns.length - 1 || busyId === it.id}
                      onClick={() => onMove(it.id, columns[ci + 1].id)}
                      title={
                        ci < columns.length - 1
                          ? `Mover a ${columns[ci + 1].label}`
                          : undefined
                      }
                      aria-label={
                        ci < columns.length - 1
                          ? `Mover "${it.title}" a ${columns[ci + 1].label}`
                          : "Sin fase siguiente"
                      }
                      className="inline-flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)] disabled:opacity-30 disabled:hover:bg-transparent"
                    >
                      <Icono nombre="chevron-right" size={14} />
                    </button>
                  </div>
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
