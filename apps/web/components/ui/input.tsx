import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean;
};

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { className, invalid, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(
        "h-8 w-full rounded-[var(--radius-md)] border bg-[var(--color-surface)] px-3 text-[13px] shadow-[var(--hundido)]",
        "text-[var(--color-primary)] placeholder:text-[var(--color-tertiary)]",
        "transition-colors",
        invalid
          ? "border-[var(--color-danger-border)]"
          : "border-[var(--border-strong)]",
        "disabled:cursor-not-allowed disabled:bg-[var(--color-subtle)] disabled:text-[var(--color-disabled)]",
        className,
      )}
    />
  );
});
