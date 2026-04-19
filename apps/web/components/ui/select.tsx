import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Props = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { className, children, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      {...rest}
      className={cn(
        "h-10 w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 text-sm",
        "text-[var(--color-primary)] hover:border-[var(--border-strong)]",
        "disabled:cursor-not-allowed disabled:bg-[var(--color-subtle)]",
        className,
      )}
    >
      {children}
    </select>
  );
});
