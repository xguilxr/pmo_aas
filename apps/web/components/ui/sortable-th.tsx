"use client";

// ENH-088 — header de columna ordenable. Usar con useSortableRows.
// Ejemplo:
//   const { sortedRows, ctrl } = useSortableRows(rows);
//   ...
//   <SortableTh sortKey="name" getter={(r) => r.name} ctrl={ctrl}>Nombre</SortableTh>

import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";

import type { SortableCtrl } from "@/lib/hooks/use-sortable-rows";
import { cn } from "@/lib/cn";

type Props<T> = {
  sortKey: string;
  getter: (r: T) => unknown;
  ctrl: SortableCtrl<T>;
  children: React.ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
};

export function SortableTh<T>({
  sortKey,
  getter,
  ctrl,
  children,
  className,
  align = "left",
}: Props<T>) {
  const active = ctrl.sortKey === sortKey;
  const Icon = active
    ? ctrl.sortDir === "asc"
      ? ChevronUp
      : ChevronDown
    : ChevronsUpDown;
  return (
    <th className={cn("px-3 py-2 font-medium", className)}>
      <button
        type="button"
        onClick={() => ctrl.toggle(sortKey, getter)}
        className={cn(
          "inline-flex w-full items-center gap-1 hover:text-[var(--color-primary)]",
          align === "right" && "justify-end",
          align === "center" && "justify-center",
          active && "text-[var(--color-primary)]",
        )}
      >
        <span>{children}</span>
        <Icon className="h-3 w-3 opacity-60" />
      </button>
    </th>
  );
}
