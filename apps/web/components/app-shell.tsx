"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  Building2,
  LayoutDashboard,
  LogOut,
  Menu,
  ServerCog,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { logout } from "@/lib/auth";
import { getStoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
  match: (path: string) => boolean;
};

const NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Tablero",
    icon: <LayoutDashboard className="h-4 w-4" aria-hidden />,
    match: (p) => p === "/dashboard",
  },
  {
    href: "/admin/organizations",
    label: "Organizaciones",
    icon: <Building2 className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/organizations"),
  },
  {
    href: "/admin/users",
    label: "Usuarios",
    icon: <Users className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/users"),
  },
  {
    href: "/admin/roles",
    label: "Roles y permisos",
    icon: <ShieldCheck className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/roles"),
  },
];

const SUPERADMIN_NAV: NavItem[] = [
  {
    href: "/superadmin/tenants",
    label: "Tenants",
    icon: <ServerCog className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/superadmin/tenants"),
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const user = getStoredUser();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    await logout();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen bg-[var(--color-app)]">
      {open ? (
        <button
          type="button"
          aria-label="Cerrar menú"
          className="fixed inset-0 z-30 bg-[oklch(0%_0_0_/_0.35)] lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-[var(--border-default)] bg-[var(--color-surface)] transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center justify-between px-5">
          <Link href="/dashboard" className="text-base font-semibold text-[var(--color-primary)]">
            PMO-aaS
          </Link>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Cerrar menú"
            className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)]"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {NAV.map((item) => {
              const active = item.match(pathname);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-[var(--color-subtle)] text-[var(--color-primary)] font-medium"
                        : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]",
                    )}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
          {user?.is_superadmin ? (
            <>
              <div className="mt-5 px-3 text-[0.65rem] font-semibold uppercase tracking-wider text-[var(--color-tertiary)]">
                Super Admin
              </div>
              <ul className="mt-1 space-y-1">
                {SUPERADMIN_NAV.map((item) => {
                  const active = item.match(pathname);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        className={cn(
                          "flex items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-sm transition-colors",
                          active
                            ? "bg-[var(--color-subtle)] text-[var(--color-primary)] font-medium"
                            : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]",
                        )}
                      >
                        {item.icon}
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : null}
        </nav>
        <div className="border-t border-[var(--border-default)] px-3 py-3">
          <div className="px-2 pb-2">
            <p className="truncate text-sm font-medium text-[var(--color-primary)]">
              {user?.full_name || user?.username || "—"}
            </p>
            <p className="truncate text-xs text-[var(--color-tertiary)]">{user?.email ?? ""}</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={handleLogout}
            loading={signingOut}
          >
            <LogOut className="h-4 w-4" aria-hidden />
            Cerrar sesión
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-2 border-b border-[var(--border-default)] bg-[var(--color-surface)] px-4 lg:px-6">
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Abrir menú"
            className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          <div className="text-sm text-[var(--color-tertiary)]">PMO-aaS</div>
        </header>
        <main className="flex-1 px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
