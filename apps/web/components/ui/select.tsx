import { forwardRef, type SelectHTMLAttributes } from "react";

import { Icono } from "@/components/ui/icono";
import { cn } from "@/lib/cn";

type Props = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { className, children, ...rest },
  ref,
) {
  return (
    <div className="relative">
      <select
        ref={ref}
        {...rest}
        className={cn(
          "h-8 w-full appearance-none rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] pl-3 pr-8 text-[13px] shadow-[var(--hundido)]",
          "text-[var(--color-primary)]",
          "disabled:cursor-not-allowed disabled:bg-[var(--color-subtle)]",
          className,
        )}
      >
        {children}
      </select>
      <Icono
        nombre="chevron-down"
        size={14}
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
      />
    </div>
  );
});
