"use client";

import Link from "next/link";
import { ShieldCheck, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getStoredUser } from "@/lib/auth-storage";

export default function DashboardPage() {
  const user = getStoredUser();

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Bienvenido, {user?.full_name || user?.username || "usuario"}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Aquí verás el resumen de tu portafolio. Iremos sumando módulos en próximas iteraciones.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
          <h2 className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Cuenta
          </h2>
          <p className="mt-1 text-sm text-[var(--color-primary)]">{user?.email ?? "—"}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {user?.is_superadmin ? (
              <Badge variant="accent">Superadmin</Badge>
            ) : user?.roles?.length ? (
              user.roles.map((r) => <Badge key={r}>{r}</Badge>)
            ) : (
              <span className="text-xs text-[var(--color-tertiary)]">Sin roles asignados</span>
            )}
          </div>
        </article>

        <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
          <h2 className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Atajos
          </h2>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link
                href="/admin/users"
                className="inline-flex items-center gap-2 text-[var(--color-primary)] hover:underline"
              >
                <Users className="h-4 w-4" aria-hidden />
                Gestionar usuarios
              </Link>
            </li>
            <li>
              <Link
                href="/admin/roles"
                className="inline-flex items-center gap-2 text-[var(--color-primary)] hover:underline"
              >
                <ShieldCheck className="h-4 w-4" aria-hidden />
                Gestionar roles
              </Link>
            </li>
          </ul>
        </article>
      </section>
    </div>
  );
}
