import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

export type Crumb = {
  href?: string;
  label: ReactNode;
};

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-[var(--color-tertiary)]">
      <ol className="flex flex-wrap items-center gap-1">
        {items.map((c, i) => {
          const last = i === items.length - 1;
          return (
            <li key={i} className="flex items-center gap-1">
              {c.href && !last ? (
                <Link
                  href={c.href}
                  className="hover:text-[var(--color-primary)] hover:underline"
                >
                  {c.label}
                </Link>
              ) : (
                <span className={last ? "text-[var(--color-primary)] font-medium" : undefined}>
                  {c.label}
                </span>
              )}
              {!last ? <ChevronRight className="h-3 w-3" aria-hidden /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
