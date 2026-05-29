import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { AssistantWidget } from "@/components/assistant-widget";
import { RequireAuth } from "@/components/require-auth";
import { TenantBrandingProvider } from "@/components/tenant-branding-provider";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <TenantBrandingProvider>
        <AppShell>{children}</AppShell>
        {/* US-165 — copiloto IA flotante en todas las páginas autenticadas. */}
        <AssistantWidget />
      </TenantBrandingProvider>
    </RequireAuth>
  );
}
