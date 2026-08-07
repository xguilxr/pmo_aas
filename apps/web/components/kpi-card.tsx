"use client";

import Link from "next/link";
import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { formatearImporte } from "@/lib/moneda";
import { esSinDato, SIN_DATO, SIN_DATO_ETIQUETA } from "@/lib/sin-dato";

/** US-153 — variación vs. periodo anterior para la píldora de tendencia. */
export type KpiTrend = {
  delta: number;
  /** Texto opcional (ej. "vs. semana previa"). */
  label?: string;
  /** Si subir es "bueno" (verde). Por defecto true; ponlo false para
   *  métricas donde subir es malo (riesgos, atrasos). */
  goodWhenUp?: boolean;
  format?: "number" | "currency" | "percent";
  /** Obligatoria si `format="currency"`. Sin defecto: BUG-092. */
  moneda?: string;
};

type Props = {
  label: string;
  /**
   * DAT-12: `null` es «no hay dato» y se pinta distinto del cero. Antes el
   * tipo era `number` a secas, así que cada sitio ponía su `?? 0` y un
   * proyecto sin presupuesto cargado salía «$0» — indistinguible de uno con
   * presupuesto cero, que es otro problema y pide otra acción.
   */
  value: number | null | undefined;
  href?: string;
  icon?: ReactNode;
  format?: "number" | "currency" | "percent";
  /**
   * BUG-092 — el código de moneda del importe, **sin valor por defecto**. Un
   * defecto escondido aquí sería el mismo bug que el `currency: "MXN"` que
   * había escrito a mano en diez sitios, solo que más difícil de encontrar.
   */
  moneda?: string;
  tone?: "neutral" | "accent" | "danger" | "warning" | "success";
  loading?: boolean;
  trend?: KpiTrend;
  /** BUG-069: subtítulo opcional (ej. "12 total") para des-duplicar las
   *  KpiCard re-implementadas localmente en org/program. */
  hint?: string;
};

function formatValue(value: number, format: Props["format"], moneda?: string): string {
  if (format === "currency") {
    // Sin moneda no se inventa una: se muestra el número desnudo. Es feo a
    // propósito — un importe sin unidad tiene que verse raro, no plausible.
    return moneda ? formatearImporte(value, moneda) : new Intl.NumberFormat("es-MX").format(value);
  }
  if (format === "percent") {
    return `${Math.round(value)}%`;
  }
  return new Intl.NumberFormat("es-MX").format(value);
}

function useCountUp(target: number, durationMs = 600): number {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    if (!Number.isFinite(target)) {
      setCurrent(0);
      return;
    }
    const from = 0;
    const to = target;
    const start = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const p = Math.min(1, (t - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      setCurrent(from + (to - from) * eased);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);
  return current;
}

const TONES: Record<NonNullable<Props["tone"]>, string> = {
  neutral: "text-[var(--color-primary)]",
  accent: "text-[var(--color-accent)]",
  danger: "text-[var(--color-danger-fg)]",
  warning: "text-[var(--color-warning-fg)]",
  success: "text-[var(--color-success-fg)]",
};

function TrendPill({ trend }: { trend: KpiTrend }) {
  const { delta, label, goodWhenUp = true } = trend;
  const flat = Math.abs(delta) < 1e-9;
  const up = delta > 0;
  const good = flat ? null : up === goodWhenUp;
  const Icon = flat ? Minus : up ? TrendingUp : TrendingDown;
  const tone = flat
    ? "bg-[var(--color-subtle)] text-[var(--color-tertiary)]"
    : good
      ? "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]"
      : "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]";
  const sign = flat ? "" : up ? "+" : "−";
  return (
    <span className="flex items-center gap-1.5">
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular-nums",
          tone,
        )}
      >
        <Icon className="h-3 w-3" aria-hidden />
        {sign}
        {formatValue(Math.abs(delta), trend.format ?? "number", trend.moneda)}
      </span>
      {label ? <span className="text-[11px] text-[var(--color-tertiary)]">{label}</span> : null}
    </span>
  );
}

export function KpiCard({
  label,
  value,
  href,
  icon,
  format = "number",
  tone = "neutral",
  loading,
  trend,
  hint,
  moneda,
}: Props) {
  const vacio = esSinDato(value);
  const animated = useCountUp(vacio ? 0 : (value as number));

  const body = (
    <div className="group flex h-full flex-col gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--color-subtle)]">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
          {label}
        </span>
        {icon ? <span className="text-[var(--color-tertiary)]">{icon}</span> : null}
      </div>
      <span
        className={cn(
          "text-2xl font-semibold tabular-nums",
          TONES[tone],
          loading || vacio ? "opacity-50" : "",
        )}
        // DAT-12: el guion largo lo lee un lector de pantalla como una pausa,
        // o no lo lee. Sin la etiqueta, «Presupuesto —» suena a «Presupuesto»
        // y el hueco desaparece justo para quien menos puede inferirlo.
        aria-label={loading ? "cargando" : vacio ? SIN_DATO_ETIQUETA : undefined}
        title={vacio && !loading ? SIN_DATO_ETIQUETA : undefined}
      >
        {loading || vacio ? SIN_DATO : formatValue(animated, format, moneda)}
      </span>
      {!loading && !vacio && trend ? <TrendPill trend={trend} /> : null}
      {hint ? <span className="text-[11px] text-[var(--color-tertiary)]">{hint}</span> : null}
      {href ? (
        <span className="text-xs text-[var(--color-tertiary)] group-hover:text-[var(--color-secondary)]">
          Ver detalle →
        </span>
      ) : null}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block focus:outline-none">
        {body}
      </Link>
    );
  }
  return body;
}
