"use client";

// ENH-088 — hook compartido para tablas ordenables en cliente.
// Devuelve filas ordenadas + handlers para alternar dir (asc/desc/null).

import { useMemo, useState } from "react";

export type SortDir = "asc" | "desc";

export type SortableCtrl<T> = {
  sortKey: string | null;
  sortDir: SortDir;
  toggle: (key: string, getter: (r: T) => unknown) => void;
  getterByKey: (key: string) => ((r: T) => unknown) | null;
};

export function useSortableRows<T>(rows: readonly T[]): {
  sortedRows: T[];
  ctrl: SortableCtrl<T>;
} {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [getters, setGetters] = useState<Record<string, (r: T) => unknown>>({});

  const sortedRows = useMemo(() => {
    if (!sortKey) return [...rows];
    const getter = getters[sortKey];
    if (!getter) return [...rows];
    const mult = sortDir === "asc" ? 1 : -1;
    const copy = [...rows];
    copy.sort((a, b) => {
      const va = getter(a);
      const vb = getter(b);
      // null/undefined al final independientemente de dir
      const aEmpty = va === null || va === undefined || va === "";
      const bEmpty = vb === null || vb === undefined || vb === "";
      if (aEmpty && bEmpty) return 0;
      if (aEmpty) return 1;
      if (bEmpty) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return (va - vb) * mult;
      }
      // boolean: false < true
      if (typeof va === "boolean" && typeof vb === "boolean") {
        return (Number(va) - Number(vb)) * mult;
      }
      // Date
      if (va instanceof Date && vb instanceof Date) {
        return (va.getTime() - vb.getTime()) * mult;
      }
      // string fallback (locale-aware, case-insensitive)
      const sa = String(va).toLowerCase();
      const sb = String(vb).toLowerCase();
      return sa.localeCompare(sb) * mult;
    });
    return copy;
  }, [rows, sortKey, sortDir, getters]);

  function toggle(key: string, getter: (r: T) => unknown) {
    setGetters((prev) => (prev[key] ? prev : { ...prev, [key]: getter }));
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("asc");
      return;
    }
    // asc → desc → null
    if (sortDir === "asc") {
      setSortDir("desc");
      return;
    }
    setSortKey(null);
    setSortDir("asc");
  }

  function getterByKey(key: string) {
    return getters[key] ?? null;
  }

  return {
    sortedRows,
    ctrl: { sortKey, sortDir, toggle, getterByKey },
  };
}
