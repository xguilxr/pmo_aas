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
  const circ = TAU * r;

  if (total <= 0) {
    return (
      <EmptyCanvas size={size} label="Sin datos" />
    );
  }

  // BUG-069: cada segmento es un círculo completo con stroke-dasharray
  // (misma técnica que Gauge/Donut), no un <path> de arco. El arco
  // colapsaba cuando un único segmento valía el 100% (start == end ⇒
  // path degenerado ⇒ la dona quedaba sin color). Con dasharray, un
  // segmento al 100% pinta `${circ} 0` y llena el anillo correctamente.
  const segments = data.filter((d) => d.value > 0);
  let offset = 0;
  return (
    <svg width={size} height={size} role="img" aria-label={ariaLabel}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--color-subtle)" strokeWidth={thickness} />
      <g transform={`rotate(-90 ${cx} ${cy})`}>
        {segments.map((d, i) => {
          const len = (d.value / total) * circ;
          const dashoffset = -offset;
          offset += len;
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={d.color}
              strokeWidth={thickness}
              strokeDasharray={`${len} ${circ - len}`}
              strokeDashoffset={dashoffset}
            >
              <title>{`${d.label}: ${d.value}`}</title>
            </circle>
          );
        })}
      </g>
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
  /** Altura objetivo en px para fallback; el contenedor usa aspect-ratio
   *  para evitar distorsión (BUG-002). */
  height?: number;
  ariaLabel: string;
  valueFormat?: (n: number) => string;
}) {
  const max = useMemo(() => Math.max(1, ...data.map((d) => d.value)), [data]);

  if (data.length === 0) {
    return <EmptyCanvas size={height} label="Sin datos" />;
  }

  // Coordenadas internas: usamos un viewBox con proporción fija 3:1
  // y preserveAspectRatio "xMidYMid meet" — así las barras no se estiran
  // horizontalmente cuando cambia el ancho del contenedor.
  const VB_W = 300;
  const VB_H = 100;
  const axisY = VB_H - 16;
  const barArea = axisY - 4;
  const barWidth = VB_W / Math.max(1, data.length);

  // Ticks (horizontales) para el eje Y — 4 niveles.
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    frac: f,
    value: max * f,
    y: axisY - f * (barArea - 4),
  }));

  return (
    <div
      className="w-full"
      style={{ aspectRatio: `${VB_W} / ${VB_H}`, minHeight: height / 2 }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={ariaLabel}
      >
        {/* Grid horizontal */}
        {ticks.map((t) => (
          <line
            key={t.frac}
            x1={24}
            y1={t.y}
            x2={VB_W}
            y2={t.y}
            stroke="var(--border-subtle)"
            strokeWidth={0.4}
            strokeDasharray={t.frac === 0 ? undefined : "2,2"}
          />
        ))}
        {/* Etiquetas eje Y */}
        {ticks.map((t) => (
          <text
            key={`lbl-${t.frac}`}
            x={20}
            y={t.y + 1.2}
            textAnchor="end"
            fontSize="3"
            fill="var(--color-tertiary)"
          >
            {valueFormat ? valueFormat(t.value) : Math.round(t.value)}
          </text>
        ))}

        {data.map((d, i) => {
          const h = (d.value / max) * (barArea - 4);
          const gap = barWidth * 0.2;
          const x = 24 + i * ((VB_W - 24) / data.length) + gap / 2;
          const w = (VB_W - 24) / data.length - gap;
          const y = axisY - h;
          return (
            <g key={i}>
              <rect x={x} y={y} width={w} height={h} fill={d.color} rx={1}>
                <title>{`${d.label}: ${valueFormat ? valueFormat(d.value) : d.value}`}</title>
              </rect>
              <text
                x={x + w / 2}
                y={axisY + 6}
                textAnchor="middle"
                fontSize="3.2"
                fill="var(--color-tertiary)"
              >
                {truncateLabel(d.label, Math.max(6, Math.floor(w / 1.8)))}
              </text>
              <text
                x={x + w / 2}
                y={Math.max(y - 1, 4)}
                textAnchor="middle"
                fontSize="3.2"
                fontWeight={600}
                fill="var(--color-secondary)"
              >
                {valueFormat ? valueFormat(d.value) : d.value}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function truncateLabel(s: string, max: number): string {
  if (s.length <= max) return s;
  return s.slice(0, Math.max(1, max - 1)) + "…";
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
            <span className="font-medium tabular-nums text-[var(--color-secondary)]">
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

/**
 * ADR-023 — colores de serie. Espejo de `app/core/paleta.py` vía tokens.
 *
 * Este mapa ofrecía `success`, `warning` y `danger` como colores de SERIE, así
 * que una serie cualquiera podía salir verde, amarilla o roja sin querer decir
 * nada — al lado de un semáforo donde esos mismos colores sí significan algo.
 * Ya no están: la salud tiene `HEALTH_FILL` y nadie más los usa.
 *
 * El orden de `series` es el mecanismo de seguridad para daltonismo. Se asignan
 * en secuencia con `serieColor()` y no se reciclan.
 */
export const PALETTE = {
  accent: "var(--color-accent)",
  primary: "var(--color-primary)",
  secondary: "var(--color-secondary)",
  neutral: "var(--chart-neutral)",
  neutralSoft: "var(--chart-neutral-soft)",
  series: [
    "var(--chart-cat-1)",
    "var(--chart-cat-2)",
    "var(--chart-cat-3)",
    "var(--chart-cat-4)",
  ],
  /** Secuencia (fase, tramo, tamaño): un solo tono, claro → oscuro. */
  scale: [
    "var(--chart-ord-1)",
    "var(--chart-ord-2)",
    "var(--chart-ord-3)",
    "var(--chart-ord-4)",
    "var(--chart-ord-5)",
  ],
};

/**
 * Color de la serie `i` (0-based). Devuelve el neutro en vez de reciclar: una
 * quinta serie con el color de la primera es un gráfico que miente sobre
 * cuántas cosas distintas muestra. Si hacen falta más de cuatro, la respuesta
 * es plegar el resto en «Otros» o partir en múltiplos pequeños.
 */
export function serieColor(i: number): string {
  return PALETTE.series[i] ?? PALETTE.neutral;
}

// ===========================================================================
// US-153 — Primitivos para dashboards N1/N2 (Gauge, TrendLines, RiskMatrix,
// Heatmap, Treemap). Todos render-only y consumen tokens del design-system.
// ===========================================================================

const HEALTH_FILL: Record<string, string> = {
  green: "var(--color-success-fg)",
  yellow: "var(--color-warning-fg)",
  red: "var(--color-danger-fg)",
};

/**
 * ADR-023: el `tone` de un medidor es un ESTADO, no una serie — «este número
 * está bien / mal»—, así que aquí el semáforo sí corresponde. Va en su propio
 * mapa para que no vuelva a colarse entre los colores de serie de `PALETTE`.
 */
const GAUGE_TONE: Record<string, string> = {
  accent: PALETTE.accent,
  primary: PALETTE.primary,
  success: "var(--color-success-fg)",
  warning: "var(--color-warning-fg)",
  danger: "var(--color-danger-fg)",
};

/** Dona de progreso/desviación con el valor al centro (0-100). */
export function Gauge({
  value,
  size = 120,
  thickness = 12,
  ariaLabel,
  tone = "accent",
  suffix = "%",
}: {
  value: number;
  size?: number;
  thickness?: number;
  ariaLabel: string;
  tone?: "accent" | "success" | "warning" | "danger" | "primary";
  suffix?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const cx = size / 2;
  const r = size / 2 - thickness / 2 - 2;
  const circ = TAU * r;
  const stroke = GAUGE_TONE[tone] ?? PALETTE.accent;
  return (
    <svg width={size} height={size} role="img" aria-label={ariaLabel}>
      <g transform={`rotate(-90 ${cx} ${cx})`}>
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke="var(--color-subtle)"
          strokeWidth={thickness}
        />
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * circ} ${circ}`}
        />
      </g>
      <text
        x={cx}
        y={cx + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={size * 0.22}
        fontWeight="600"
        className="tabular-nums"
        fill="var(--color-primary)"
      >
        {Math.round(pct)}
        <tspan fontSize={size * 0.12} fill="var(--color-tertiary)">
          {suffix}
        </tspan>
      </text>
    </svg>
  );
}

/** Línea de tendencia (una métrica) con área suave. `data` ordenado por x. */
export function TrendLines({
  data,
  ariaLabel,
  valueFormat,
  color = "var(--color-accent)",
}: {
  data: { x: string; y: number }[];
  ariaLabel: string;
  valueFormat?: (n: number) => string;
  color?: string;
}) {
  if (data.length === 0) return <EmptyCanvas size={120} label="Sin datos" />;
  const VB_W = 300;
  const VB_H = 100;
  const padX = 6;
  const padY = 10;
  const max = Math.max(1, ...data.map((d) => d.y));
  const min = Math.min(0, ...data.map((d) => d.y));
  const span = max - min || 1;
  const n = data.length;
  const xAt = (i: number) =>
    n === 1 ? VB_W / 2 : padX + (i * (VB_W - 2 * padX)) / (n - 1);
  const yAt = (v: number) => VB_H - padY - ((v - min) / span) * (VB_H - 2 * padY);
  const line = data.map((d, i) => `${xAt(i)},${yAt(d.y)}`).join(" ");
  const area = `${padX},${VB_H - padY} ${line} ${xAt(n - 1)},${VB_H - padY}`;
  const last = data[n - 1];
  return (
    <div className="w-full" style={{ aspectRatio: `${VB_W} / ${VB_H}` }}>
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={ariaLabel}
      >
        <polygon points={area} fill={color} opacity={0.1} />
        <polyline
          points={line}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
        {n <= 24
          ? data.map((d, i) => (
              <circle key={i} cx={xAt(i)} cy={yAt(d.y)} r={1.6} fill={color}>
                <title>{`${d.x}: ${valueFormat ? valueFormat(d.y) : d.y}`}</title>
              </circle>
            ))
          : null}
        <circle cx={xAt(n - 1)} cy={yAt(last.y)} r={2.6} fill={color} />
      </svg>
    </div>
  );
}

/** Matriz 5×5 de riesgos (probabilidad × impacto). `cells` 1-indexados. */
export function RiskMatrix({
  cells,
  ariaLabel,
  onCellClick,
}: {
  cells: { probability: number; impact: number; count: number }[];
  ariaLabel: string;
  onCellClick?: (probability: number, impact: number) => void;
}) {
  const map = new Map<string, number>();
  for (const c of cells) map.set(`${c.probability}:${c.impact}`, c.count);
  const zoneClass = (sev: number) =>
    sev <= 6
      ? "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]"
      : sev <= 12
        ? "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]"
        : "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]";
  const probs = [5, 4, 3, 2, 1];
  const impacts = [1, 2, 3, 4, 5];
  return (
    <div role="img" aria-label={ariaLabel} className="text-xs">
      <div className="flex gap-1">
        <div className="flex w-4 items-center">
          <span className="-rotate-90 whitespace-nowrap text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
            Probabilidad
          </span>
        </div>
        <div className="grid flex-1 grid-cols-5 gap-1">
          {probs.map((p) =>
            impacts.map((im) => {
              const count = map.get(`${p}:${im}`) ?? 0;
              const sev = p * im;
              const interactive = onCellClick && count > 0;
              return (
                <button
                  key={`${p}:${im}`}
                  type="button"
                  disabled={!interactive}
                  onClick={interactive ? () => onCellClick!(p, im) : undefined}
                  title={`Prob ${p} × Impacto ${im} — ${count} riesgo(s)`}
                  className={cnLocal(
                    "flex aspect-square items-center justify-center rounded-[var(--radius-sm)] font-semibold tabular-nums transition-opacity",
                    zoneClass(sev),
                    count === 0 ? "opacity-30" : "",
                    interactive ? "cursor-pointer hover:opacity-80" : "cursor-default",
                  )}
                >
                  {count > 0 ? count : ""}
                </button>
              );
            }),
          )}
        </div>
      </div>
      <div className="mt-1 grid grid-cols-5 gap-1 pl-5 text-center text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
        {impacts.map((im) => (
          <span key={im}>{im}</span>
        ))}
      </div>
      <div className="mt-0.5 pl-5 text-center text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
        Impacto →
      </div>
    </div>
  );
}

/** Heatmap Organización × Salud (conteo de proyectos por celda). */
export function Heatmap({
  rows,
  ariaLabel,
  onCellClick,
}: {
  rows: { org_id: string; org_name: string; green: number; yellow: number; red: number; total: number }[];
  ariaLabel: string;
  onCellClick?: (orgId: string, health: "green" | "yellow" | "red") => void;
}) {
  if (rows.length === 0) return <EmptyCanvas size={120} label="Sin organizaciones" />;
  const maxByCol = {
    green: Math.max(1, ...rows.map((r) => r.green)),
    yellow: Math.max(1, ...rows.map((r) => r.yellow)),
    red: Math.max(1, ...rows.map((r) => r.red)),
  };
  const cols: ("green" | "yellow" | "red")[] = ["green", "yellow", "red"];
  const colLabel = { green: "Verde", yellow: "Amarillo", red: "Rojo" };
  return (
    <div role="img" aria-label={ariaLabel} className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="text-left font-medium text-[var(--color-tertiary)]" />
            {cols.map((c) => (
              <th key={c} className="px-2 text-center font-medium text-[var(--color-tertiary)]">
                {colLabel[c]}
              </th>
            ))}
            <th className="px-2 text-right font-medium text-[var(--color-tertiary)]">Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.org_id}>
              <td className="max-w-[180px] truncate pr-2 text-[var(--color-secondary)]" title={r.org_name}>
                {r.org_name}
              </td>
              {cols.map((c) => {
                const count = r[c];
                const intensity = count / maxByCol[c];
                const interactive = onCellClick && count > 0;
                return (
                  <td key={c} className="p-0">
                    <button
                      type="button"
                      disabled={!interactive}
                      onClick={interactive ? () => onCellClick!(r.org_id, c) : undefined}
                      title={`${r.org_name} · ${colLabel[c]}: ${count}`}
                      style={{ opacity: count === 0 ? 0.25 : 0.35 + intensity * 0.65 }}
                      className={cnLocal(
                        "flex h-8 w-full items-center justify-center rounded-[var(--radius-sm)] font-semibold tabular-nums",
                        c === "green"
                          ? "bg-[var(--color-success-fg)] text-white"
                          : c === "yellow"
                            ? "bg-[var(--color-warning-fg)] text-white"
                            : "bg-[var(--color-danger-fg)] text-white",
                        interactive ? "cursor-pointer hover:brightness-110" : "cursor-default",
                      )}
                    >
                      {count > 0 ? count : ""}
                    </button>
                  </td>
                );
              })}
              <td className="px-2 text-right font-semibold tabular-nums text-[var(--color-primary)]">
                {r.total}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type TreeProject = { id: string; name: string; folio: string; value: number; health: string | null };
type TreeProgram = { id: string; name: string; children: TreeProject[] };
type TreeOrg = { id: string; name: string; children: TreeProgram[] };

/** Treemap proporcional Organización → Programa → Proyecto (valor=presupuesto). */
export function Treemap({
  tree,
  ariaLabel,
  moneda,
}: {
  tree: TreeOrg[];
  ariaLabel: string;
  /** BUG-092 — sin defecto: el treemap agrega cartera, así que la moneda la
   *  aporta la pantalla (la preferida del inquilino). */
  moneda: string;
}) {
  if (tree.length === 0) return <EmptyCanvas size={120} label="Sin proyectos" />;
  const fmt = (n: number) =>
    new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency: moneda,
      maximumFractionDigits: 0,
      notation: "compact",
    }).format(n);
  return (
    <div role="img" aria-label={ariaLabel} className="space-y-3">
      {tree.map((org) => {
        const orgTotal = org.children.reduce(
          (a, p) => a + p.children.reduce((b, c) => b + c.value, 0),
          0,
        );
        return (
          <div key={org.id} className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-2">
            <div className="mb-1.5 flex items-center justify-between text-xs">
              <span className="truncate font-semibold text-[var(--color-primary)]">{org.name}</span>
              <span className="tabular-nums text-[var(--color-tertiary)]">{fmt(orgTotal)}</span>
            </div>
            <div className="space-y-1">
              {org.children.map((prog) => {
                const projects = prog.children.filter((p) => p.value > 0);
                const total = projects.reduce((a, p) => a + p.value, 0);
                if (projects.length === 0) return null;
                return (
                  <div key={prog.id} className="flex items-center gap-2">
                    <span className="w-24 shrink-0 truncate text-[10px] text-[var(--color-tertiary)]" title={prog.name}>
                      {prog.name}
                    </span>
                    <div className="flex h-6 flex-1 overflow-hidden rounded-[var(--radius-sm)]">
                      {projects.map((p) => (
                        <div
                          key={p.id}
                          title={`${p.name} (${p.folio}) · ${fmt(p.value)}`}
                          style={{
                            flexGrow: p.value,
                            flexBasis: 0,
                            backgroundColor: HEALTH_FILL[p.health ?? ""] ?? "var(--color-muted)",
                          }}
                          className="min-w-[3px] border-r border-[var(--color-surface)] last:border-r-0"
                        />
                      ))}
                    </div>
                    <span className="w-14 shrink-0 text-right text-[10px] tabular-nums text-[var(--color-tertiary)]">
                      {fmt(total)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function cnLocal(...parts: (string | false | undefined | null)[]): string {
  return parts.filter(Boolean).join(" ");
}
