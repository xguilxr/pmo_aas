"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut, ShieldCheck, User as UserIcon } from "lucide-react";

import { RequireAuth } from "@/components/require-auth";
import { Button } from "@/components/ui/button";
import { logout } from "@/lib/auth";
import { getStoredUser } from "@/lib/auth-storage";

function DashboardContent() {
  const router = useRouter();
  const user = getStoredUser();
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    await logout();
    router.replace("/login");
  }

  return (
    <main className="min-h-screen bg-[var(--color-app)]">
      <header className="border-b border-[var(--border-default)] bg-[var(--color-surface)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold text-[var(--color-primary)]">PMO-aaS</h1>
            <p className="text-xs text-[var(--color-tertiary)]">Tablero</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleLogout}
            loading={signingOut}
          >
            <LogOut className="h-4 w-4" aria-hidden />
            Cerrar sesión
          </Button>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
          <h2 className="text-xl font-semibold text-[var(--color-primary)]">
            Bienvenido, {user?.full_name || user?.username || "usuario"}
          </h2>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            La plataforma está viva. Iremos construyendo cada módulo del PMO paso a paso.
          </p>

          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-[var(--radius-md)] border border-[var(--border-default)] p-4">
              <dt className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
                <UserIcon className="h-3.5 w-3.5" aria-hidden />
                Usuario
              </dt>
              <dd className="mt-1 text-sm text-[var(--color-primary)]">
                {user?.email ?? "—"}
              </dd>
            </div>
            <div className="rounded-[var(--radius-md)] border border-[var(--border-default)] p-4">
              <dt className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
                <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
                Roles
              </dt>
              <dd className="mt-1 text-sm text-[var(--color-primary)]">
                {user?.is_superadmin
                  ? "Superadmin global"
                  : user?.roles?.length
                    ? user.roles.join(", ")
                    : "Sin roles asignados"}
              </dd>
            </div>
          </dl>
        </div>

        <p className="mt-6 text-center text-xs text-[var(--color-tertiary)]">
          Próximo: administración de usuarios, roles y auditoría.
        </p>
      </section>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <DashboardContent />
    </RequireAuth>
  );
}
