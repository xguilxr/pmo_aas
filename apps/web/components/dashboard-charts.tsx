"use client";

import { useMemo } from "react";

type Datum = { label: string; value: number; color: string };

const TAU = Math.PI * 2;

export function Pie({
  data,
  size = 180,
  thickness = 22,
  ariaLabel,
}: {
  data: Datum[];
  size?: number;
  thickness?: number;
  ariaLabel: string;
}) {
  const total = useMemo(() => data.reduce((a, d) => a + d.value, 0), [data]);
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - thickness / 2 - 2;

  if (total <= 0) {
    return (
      <EmptyCanvas size={size} label="Sin datos" />
    );
  }

  let acc = 0;
  return (
    <svg width={size} height={size} role="img" aria-label={ariaLabel}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--color-subtle)" strokeWidth={thickness} />
      {data.map((d, i) => {
        if (d.value <= 0) return null;
        const start = (acc / total) * TAU - Math.PI / 2;
        acc += d.value;
        const end = (acc / total) * TAU - Math.PI / 2;
        const large = end - start > Math.PI ? 1 : 0;
        const x1 = cx + r * Math.cos(start);
        const y1 = cy + r * Math.sin(start);
        const x2 = cx + r * Math.cos(end);
        const y2 = cy + r * Math.sin(end);
        const path = `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
        return (
          <path
            key={i}
            d={path}
            fill="none"
            stroke={d.color}
            strokeWidth={thickness}
            strokeLinecap="butt"
          >
            <title>{`${d.label}: ${d.value}`}</title>
          </path>
        );
      })}
      <text
        x={cx}
        y={cy - 4}
        textAnchor="middle"
        fontSize="22"
        fontWeight="600"
        fill="var(--color-primary)"
      >
        {total}
      </text>
      <text
        x={cx}
        y={cy + 14}
        textAnchor="middle"
        fontSize="11"
        fill="var(--color-tertiary)"
      >
        total
      </text>
    </svg>
  );
}

export function Bars({
  data,
  height = 180,
  ariaLabel,
  valueFormat,
}: {
  data: Datum[];
  height?: number;
  ariaLabel: string;
  valueFormat?: (n: number) => string;
}) {
  const max = useMemo(() => Math.max(1, ...data.map((d) => d.value)), [data]);

  if (data.length === 0) {
    return <EmptyCanvas size={height} label="Sin datos" />;
  }

  const barArea = height - 40;
  const barWidth = 100 / Math.max(1, data.length);

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel}
    >
      <line
        x1={0}
        y1={barArea}
        x2={100}
        y2={barArea}
        stroke="var(--border-default)"
        strokeWidth={0.5}
      />
      {data.map((d, i) => {
        const h = (d.value / max) * (barArea - 8);
        const x = i * barWidth + barWidth * 0.15;
        const w = barWidth * 0.7;
        const y = barArea - h;
        return (
          <g key={i}>
            <rect x={x} y={y} width={w} height={h} fill={d.color} rx={1}>
              <title>{`${d.label}: ${valueFormat ? valueFormat(d.value) : d.value}`}</title>
            </rect>
            <text
              x={x + w / 2}
              y={barArea + 10}
              textAnchor="middle"
              fontSize="4"
              fill="var(--color-tertiary)"
            >
              {d.label}
            </text>
            <text
              x={x + w / 2}
              y={y - 2}
              textAnchor="middle"
              fontSize="4"
              fill="var(--color-secondary)"
            >
              {valueFormat ? valueFormat(d.value) : d.value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function Legend({ data }: { data: Datum[] }) {
  const total = data.reduce((a, d) => a + d.value, 0);
  return (
    <ul className="space-y-1.5 text-xs">
      {data.map((d, i) => {
        const pct = total > 0 ? Math.round((d.value / total) * 100) : 0;
        return (
          <li key={i} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-[2px]"
                style={{ backgroundColor: d.color }}
              />
              <span className="text-[var(--color-secondary)]">{d.label}</span>
            </span>
            <span className="text-[var(--color-tertiary)]">
              {d.value}
              {total > 0 ? ` · ${pct}%` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function EmptyCanvas({ size, label }: { size: number; label: string }) {
  return (
    <div
      className="flex items-center justify-center rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] text-xs text-[var(--color-tertiary)]"
      style={{ height: size }}
    >
      {label}
    </div>
  );
}

export const PALETTE = {
  accent: "var(--color-accent)",
  primary: "var(--color-primary)",
  secondary: "var(--color-secondary)",
  success: "var(--color-success-fg)",
  warning: "var(--color-warning-fg)",
  danger: "var(--color-danger-fg)",
  info: "var(--color-info-fg)",
  neutral: "var(--color-muted)",
};
