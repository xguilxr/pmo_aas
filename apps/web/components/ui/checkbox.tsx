import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Props = InputHTMLAttributes<HTMLInputElement>;

export const Checkbox = forwardRef<HTMLInputElement, Props>(function Checkbox(
  { className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      type="checkbox"
      {...rest}
      className={cn(
        "h-4 w-4 cursor-pointer rounded-[var(--radius-xs)] border-[var(--border-strong)]",
        "accent-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
    />
  );
});
