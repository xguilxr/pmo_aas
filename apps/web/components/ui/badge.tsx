import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "neutral" | "success" | "warning" | "danger" | "info" | "accent";

const VARIANTS: Record<Variant, string> = {
  neutral:
    "bg-[var(--color-subtle)] text-[var(--color-secondary)] border-[var(--border-default)]",
  success:
    "bg-[var(--color-success-bg)] text-[var(--color-success-fg)] border-[var(--color-success-border)]",
  warning:
    "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)] border-[var(--color-warning-border)]",
  danger:
    "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)] border-[var(--color-danger-border)]",
  info: "bg-[var(--color-info-bg)] text-[var(--color-info-fg)] border-[var(--color-info-border)]",
  accent:
    "bg-[var(--color-primary)] text-[var(--color-inverse)] border-[var(--color-primary)]",
};

type Props = HTMLAttributes<HTMLSpanElement> & {
  variant?: Variant;
};

export function Badge({ variant = "neutral", className, ...rest }: Props) {
  return (
    <span
      {...rest}
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius-sm)] border px-2 py-0.5 text-xs font-medium",
        VARIANTS[variant],
        className,
      )}
    />
  );
}
