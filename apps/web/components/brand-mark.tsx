"use client";

import { resolveLogoUrl } from "@/lib/api/branding";
import { cn } from "@/lib/cn";
import { useTenantBranding } from "@/components/tenant-branding-provider";

type BrandMarkProps = {
  variant?: "sidebar" | "topbar";
  className?: string;
};

/**
 * Renders the tenant branding (logo + name) in chrome surfaces.
 * Falls back to the literal "PMO · aaS" when no tenant logo is configured.
 */
export function BrandMark({ variant = "sidebar", className }: BrandMarkProps) {
  const { branding } = useTenantBranding();
  const logoSrc = resolveLogoUrl(branding?.logo_url ?? null);
  const name = branding?.tenant_name ?? "PMO · aaS";

  if (logoSrc) {
    const height = variant === "sidebar" ? "h-7" : "h-6";
    return (
      <span className={cn("inline-flex items-center gap-2", className)}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={logoSrc}
          alt={name}
          className={cn(height, "w-auto max-w-[160px] object-contain")}
        />
      </span>
    );
  }

  const textSize = variant === "sidebar" ? "text-[15px] font-semibold" : "text-[13px] font-medium";
  const color =
    variant === "sidebar"
      ? "text-[var(--chrome-text)]"
      : "text-[var(--chrome-text-muted)]";
  return (
    <span className={cn("tracking-tight", textSize, color, className)}>
      {name}
    </span>
  );
}
