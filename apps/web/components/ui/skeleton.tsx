import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Skeleton({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={cn(
        "animate-pulse rounded-[var(--radius-sm)] bg-[var(--color-muted)]",
        className,
      )}
    />
  );
}
