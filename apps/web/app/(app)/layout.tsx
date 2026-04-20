import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { TenantBrandingProvider } from "@/components/tenant-branding-provider";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <TenantBrandingProvider>
        <AppShell>{children}</AppShell>
      </TenantBrandingProvider>
    </RequireAuth>
  );
}
