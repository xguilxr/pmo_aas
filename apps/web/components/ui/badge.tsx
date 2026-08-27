import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "neutral" | "success" | "warning" | "danger" | "info" | "accent";

const VARIANTS: Record<Variant, string> = {
  neutral: "bg-[var(--color-muted)] text-[var(--color-secondary)]",
  success: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]",
  danger: "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]",
  info: "bg-[var(--color-info-bg)] text-[var(--color-info-fg)]",
  accent: "bg-[var(--color-primary)] text-[var(--color-inverse)]",
};

type Props = HTMLAttributes<HTMLSpanElement> & {
  variant?: Variant;
};

export function Badge({ variant = "neutral", className, ...rest }: Props) {
  return (
    <span
      {...rest}
      className={cn(
        "inline-flex h-5.5 items-center gap-1 rounded-[var(--radius-sm)] px-2 text-[11.5px] font-medium",
        VARIANTS[variant],
        className,
      )}
    />
  );
}
