import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Props = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, Props>(function Textarea(
  { className, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      {...rest}
      className={cn(
        "min-h-[80px] w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-sm",
        "text-[var(--color-primary)] placeholder:text-[var(--color-tertiary)]",
        "hover:border-[var(--border-strong)]",
        className,
      )}
    />
  );
});
