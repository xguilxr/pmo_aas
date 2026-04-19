import type { HTMLAttributes, ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/cn";

type Variant = "success" | "warning" | "danger" | "info";

const STYLES: Record<Variant, { box: string; icon: ReactNode }> = {
  success: {
    box: "bg-[var(--color-success-bg)] border-[var(--color-success-border)] text-[var(--color-success-fg)]",
    icon: <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />,
  },
  warning: {
    box: "bg-[var(--color-warning-bg)] border-[var(--color-warning-border)] text-[var(--color-warning-fg)]",
    icon: <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />,
  },
  danger: {
    box: "bg-[var(--color-danger-bg)] border-[var(--color-danger-border)] text-[var(--color-danger-fg)]",
    icon: <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />,
  },
  info: {
    box: "bg-[var(--color-info-bg)] border-[var(--color-info-border)] text-[var(--color-info-fg)]",
    icon: <Info className="h-4 w-4 shrink-0" aria-hidden />,
  },
};

type Props = HTMLAttributes<HTMLDivElement> & {
  variant?: Variant;
  title?: string;
};

export function Banner({ variant = "info", title, className, children, ...rest }: Props) {
  const style = STYLES[variant];
  return (
    <div
      role="alert"
      {...rest}
      className={cn(
        "flex items-start gap-2 rounded-[var(--radius-md)] border px-3 py-2 text-sm",
        style.box,
        className,
      )}
    >
      {style.icon}
      <div className="flex-1">
        {title ? <div className="font-medium">{title}</div> : null}
        <div>{children}</div>
      </div>
    </div>
  );
}
