import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { AssistantWidget } from "@/components/assistant-widget";
import { FronteraDePermiso } from "@/components/frontera-de-permiso";
import { OrganizacionActivaProvider } from "@/components/organizacion-activa";
import { RequireAuth } from "@/components/require-auth";
import { TenantBrandingProvider } from "@/components/tenant-branding-provider";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <TenantBrandingProvider>
        {/* US-205 — la organización activa envuelve al shell **y** al
            contenido: el switcher vive en el header y las pantallas leen de
            aquí, así que los dos necesitan el mismo proveedor. */}
        <OrganizacionActivaProvider>
          {/* MCS DIS-03 — el estado «sin permiso» de las 75 pantallas. */}
          <AppShell>
            <FronteraDePermiso>{children}</FronteraDePermiso>
          </AppShell>
          {/* US-165 — copiloto IA flotante en todas las páginas autenticadas. */}
          <AssistantWidget />
        </OrganizacionActivaProvider>
      </TenantBrandingProvider>
    </RequireAuth>
  );
}
