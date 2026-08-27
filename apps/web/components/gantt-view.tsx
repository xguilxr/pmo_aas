"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { GanttData } from "@/lib/api/tasks";

type Zoom = "day" | "week" | "month" | "quarter";

const ZOOM_PX: Record<Zoom, number> = {
  day: 28,
  week: 14,
  month: 6,
  quarter: 2.5,
};

const ROW_HEIGHT = 30;
const LEFT_COL = 220;
const HEADER_HEIGHT = 32;

function daysBetween(a: Date, b: Date): number {
  const ms = 24 * 60 * 60 * 1000;
  return Math.round((b.getTime() - a.getTime()) / ms);
}

function addDays(d: Date, days: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + days);
  return out;
}

function parseDate(iso: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return d;
}

function formatDay(d: Date, zoom: Zoom): string {
  if (zoom === "quarter") {
    return `Q${Math.floor(d.getMonth() / 3) + 1} ${d.getFullYear()}`;
  }
  if (zoom === "month") {
    return d.toLocaleDateString("es-MX", { month: "short", year: "2-digit" });
  }
  if (zoom === "week") {
    return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
  }
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
}

export function GanttView({ data }: { data: GanttData }) {
  const [zoom, setZoom] = useState<Zoom>("week");

  // El Gantt no aprovechaba el ancho disponible: el ancho se derivaba
  // sólo del rango de fechas (totalDays × pxPerDay fijo por zoom), así
  // que con rangos cortos quedaba un gran espacio vacío a la derecha.
  // Medimos el viewport del contenedor scrollable y estiramos pxPerDay
  // para llenar el espacio a cualquier nivel de zoom. Si el rango es
  // más ancho que el viewport se respeta el zoom y aparece scroll.
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [viewportWidth, setViewportWidth] = useState(0);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const measure = () => setViewportWidth(el.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [data.tasks.length]);

  const tasksWithDates = useMemo(() => {
    return data.tasks.map((t) => ({
      ...t,
      startDate: parseDate(t.start),
      endDate: parseDate(t.end),
    }));
  }, [data.tasks]);

  const { minDate, maxDate, totalDays } = useMemo(() => {
    const dates = tasksWithDates.flatMap((t) =>
      [t.startDate, t.endDate].filter((d): d is Date => d !== null),
    );
    if (dates.length === 0) {
      const now = new Date();
      return { minDate: now, maxDate: addDays(now, 30), totalDays: 30 };
    }
    const min = new Date(Math.min(...dates.map((d) => d.getTime())));
    const max = new Date(Math.max(...dates.map((d) => d.getTime())));
    const padded_min = addDays(min, -3);
    const padded_max = addDays(max, 3);
    return {
      minDate: padded_min,
      maxDate: padded_max,
      totalDays: Math.max(1, daysBetween(padded_min, padded_max)),
    };
  }, [tasksWithDates]);

  // Estira el ancho por día para llenar el viewport cuando el rango de
  // fechas es más angosto que el contenedor; nunca por debajo del zoom.
  const fitPxPerDay =
    viewportWidth > LEFT_COL && totalDays > 0
      ? (viewportWidth - LEFT_COL) / totalDays
      : 0;
  const pxPerDay = Math.max(ZOOM_PX[zoom], fitPxPerDay);

  const taskById = useMemo(
    () => Object.fromEntries(tasksWithDates.map((t) => [t.id, t])),
    [tasksWithDates],
  );

  const timelineWidth = totalDays * pxPerDay;

  const tickStep = zoom === "day" ? 1 : zoom === "week" ? 7 : zoom === "month" ? 30 : 90;
  const ticks: { x: number; label: string }[] = [];
  for (let d = 0; d <= totalDays; d += tickStep) {
    ticks.push({ x: d * pxPerDay, label: formatDay(addDays(minDate, d), zoom) });
  }

  const today = new Date();
  const todayOffset = daysBetween(minDate, today);
  const todayX = todayOffset >= 0 && todayOffset <= totalDays ? todayOffset * pxPerDay : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-[18px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
          Diagrama de Gantt
        </h2>
        <div className="inline-flex h-7 items-center gap-0.5 rounded-[9px] border border-[var(--border-default)] bg-[var(--color-subtle)] p-0.5 shadow-[var(--hundido)]">
          {(["day", "week", "month", "quarter"] as Zoom[]).map((z) => (
            <button
              key={z}
              type="button"
              onClick={() => setZoom(z)}
              aria-pressed={zoom === z}
              className={`inline-flex h-5.5 items-center rounded-[7px] px-2.5 text-[11.5px] font-medium ${
                zoom === z
                  ? "bg-[var(--color-surface)] text-[var(--text-primary)] shadow-[var(--shadow-optical-sm)]"
                  : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {z === "day" ? "Día" : z === "week" ? "Semana" : z === "month" ? "Mes" : "Trim"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] shadow-[var(--relieve-isla)]">
        {data.tasks.length === 0 ? (
          <div className="p-10 text-center text-[13px] text-[var(--text-tertiary)]">
            No hay tareas para graficar. Crea tareas o importa desde MS Project.
          </div>
        ) : (
          <div ref={scrollRef} className="overflow-auto">
            <div
              className="relative"
              style={{
                width: LEFT_COL + timelineWidth,
                minHeight: HEADER_HEIGHT + tasksWithDates.length * ROW_HEIGHT,
              }}
            >
              <div
                className="sticky top-0 z-10 flex border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-[10.5px] font-semibold text-[var(--text-tertiary)] shadow-[var(--linea-surco)]"
                style={{ height: HEADER_HEIGHT }}
              >
                <div
                  className="flex items-center px-3"
                  style={{ width: LEFT_COL, minWidth: LEFT_COL }}
                >
                  Tarea
                </div>
                <div className="relative flex-1 border-l border-[var(--border-default)]">
                  {ticks.map((t, i) => (
                    <div
                      key={i}
                      className="absolute top-0 flex h-full items-center border-l border-[var(--border-subtle)] px-1.5 uppercase"
                      style={{ left: t.x }}
                    >
                      {t.label}
                    </div>
                  ))}
                </div>
              </div>

              <div
                className="pointer-events-none absolute top-0"
                style={{
                  left: LEFT_COL,
                  top: HEADER_HEIGHT,
                  width: timelineWidth,
                  height: tasksWithDates.length * ROW_HEIGHT,
                }}
              >
                {ticks.map((t, i) => (
                  <div
                    key={i}
                    className="absolute top-0 h-full border-l border-[var(--border-subtle)]"
                    style={{ left: t.x }}
                  />
                ))}
              </div>

              {tasksWithDates.map((t, idx) => {
                const y = idx * ROW_HEIGHT;
                const startX = t.startDate ? daysBetween(minDate, t.startDate) * pxPerDay : null;
                const endX = t.endDate ? daysBetween(minDate, t.endDate) * pxPerDay : null;
                const width =
                  startX !== null && endX !== null ? Math.max(pxPerDay, endX - startX) : null;
                const progressWidth = width ? (width * t.progress) / 100 : 0;
                const statusColor =
                  t.status === "completed"
                    ? "var(--color-success-fg)"
                    : t.status === "in_progress"
                      ? "var(--color-accent)"
                      : t.status === "on_hold"
                        ? "var(--color-warning-fg)"
                        : "var(--text-primary)";
                const showRing = t.status === "in_progress" || t.status === "on_hold";
                const depth = t.wbs_code ? Math.max(0, t.wbs_code.split(".").length - 1) : 0;
                const isParentRow = depth === 0;
                const isLastRow = idx === tasksWithDates.length - 1;
                return (
                  <div
                    key={t.id}
                    className={`absolute left-0 flex ${
                      isLastRow ? "" : "border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]"
                    }`}
                    style={{ top: HEADER_HEIGHT + y, height: ROW_HEIGHT, width: LEFT_COL + timelineWidth }}
                  >
                    <div
                      className="flex items-center border-r border-[var(--border-subtle)] text-[12px]"
                      style={{ width: LEFT_COL, minWidth: LEFT_COL, paddingLeft: 12 + depth * 12, paddingRight: 12 }}
                    >
                      <span
                        className={`truncate ${
                          isParentRow
                            ? "font-semibold text-[var(--text-primary)]"
                            : "text-[var(--text-secondary)]"
                        }`}
                        title={`${t.name} (${t.progress}%)`}
                      >
                        {t.wbs_code ? `${t.wbs_code} ${t.name}` : t.name}
                      </span>
                    </div>
                    <div className="relative flex-1">
                      {t.is_milestone && startX !== null ? (
                        <div
                          className="absolute top-1/2 h-[11px] w-[11px] -translate-y-1/2 rotate-45 shadow-[var(--relieve-hito)]"
                          style={{ left: startX - 5.5, backgroundColor: "var(--color-warning-fg)" }}
                          title={`Hito: ${t.name}`}
                        />
                      ) : startX !== null && width !== null ? (
                        <div
                          className="absolute top-1/2 h-3 -translate-y-1/2 rounded-[3px]"
                          style={{
                            left: startX,
                            width,
                            backgroundColor: "var(--color-muted)",
                            boxShadow: showRing ? `0 0 0 1px ${statusColor}` : undefined,
                          }}
                          title={`${t.name}: ${t.start} → ${t.end}`}
                        >
                          <div
                            className="absolute top-0 left-0 h-full rounded-[3px]"
                            style={{ width: progressWidth, backgroundColor: statusColor }}
                          />
                        </div>
                      ) : (
                        <div className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[var(--text-tertiary)]">
                          sin fechas
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {todayX !== null ? (
                <div
                  className="absolute top-0 border-l-2 border-dashed border-[var(--color-danger-fg)]"
                  style={{ left: LEFT_COL + todayX, height: HEADER_HEIGHT + tasksWithDates.length * ROW_HEIGHT }}
                >
                  <span className="absolute top-0.5 left-0.5 rounded-[3px] bg-[var(--color-danger-fg)] px-1.25 py-px text-[9px] font-semibold text-[var(--color-inverse)]">
                    Hoy
                  </span>
                </div>
              ) : null}

              <svg
                className="pointer-events-none absolute left-0 top-0"
                width={LEFT_COL + timelineWidth}
                height={HEADER_HEIGHT + tasksWithDates.length * ROW_HEIGHT}
              >
                {data.dependencies.map((d, i) => {
                  const pre = taskById[d.predecessor_id];
                  const suc = taskById[d.successor_id];
                  if (!pre || !suc) return null;
                  const preIdx = tasksWithDates.findIndex((x) => x.id === d.predecessor_id);
                  const sucIdx = tasksWithDates.findIndex((x) => x.id === d.successor_id);
                  if (preIdx < 0 || sucIdx < 0) return null;
                  const preEnd = pre.endDate ?? pre.startDate;
                  const sucStart = suc.startDate ?? suc.endDate;
                  if (!preEnd || !sucStart) return null;
                  const x1 = LEFT_COL + daysBetween(minDate, preEnd) * pxPerDay;
                  const y1 = HEADER_HEIGHT + preIdx * ROW_HEIGHT + ROW_HEIGHT / 2;
                  const x2 = LEFT_COL + daysBetween(minDate, sucStart) * pxPerDay;
                  const y2 = HEADER_HEIGHT + sucIdx * ROW_HEIGHT + ROW_HEIGHT / 2;
                  return (
                    <path
                      key={i}
                      d={`M ${x1} ${y1} L ${x1 + 8} ${y1} L ${x1 + 8} ${y2} L ${x2} ${y2}`}
                      fill="none"
                      stroke="var(--text-tertiary)"
                      strokeWidth={1}
                    />
                  );
                })}
              </svg>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
