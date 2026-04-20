"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  Activity,
  Building2,
  ClipboardList,
  Cog,
  Eye,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  ScrollText,
  ServerCog,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

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
    href: "/admin/requests",
    label: "Solicitudes",
    icon: <ClipboardList className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/requests"),
  },
  {
    href: "/admin/projects",
    label: "Proyectos",
    icon: <FolderKanban className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/projects"),
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

const ADMIN_NAV: NavItem[] = [
  {
    href: "/admin/supervision",
    label: "Supervisión",
    icon: <Eye className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/supervision"),
  },
  {
    href: "/admin/audit-logs",
    label: "Auditoría",
    icon: <ScrollText className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/audit-logs"),
  },
  {
    href: "/admin/settings",
    label: "Configuración",
    icon: <Cog className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/admin/settings"),
  },
];

const SUPERADMIN_NAV: NavItem[] = [
  {
    href: "/superadmin",
    label: "Visión general",
    icon: <LayoutDashboard className="h-4 w-4" aria-hidden />,
    match: (p) => p === "/superadmin",
  },
  {
    href: "/superadmin/tenants",
    label: "Tenants",
    icon: <ServerCog className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/superadmin/tenants"),
  },
  {
    href: "/superadmin/logs",
    label: "Logs platform",
    icon: <ScrollText className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/superadmin/logs"),
  },
  {
    href: "/superadmin/health",
    label: "Health",
    icon: <Activity className="h-4 w-4" aria-hidden />,
    match: (p) => p.startsWith("/superadmin/health"),
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
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-[var(--chrome-border)] transition-transform lg:static lg:translate-x-0",
          "bg-[var(--chrome-bg-translucent)] backdrop-blur-xl backdrop-saturate-150",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        style={{ WebkitBackdropFilter: "saturate(140%) blur(20px)" }}
      >
        <div className="flex h-14 items-center justify-between px-5">
          <Link
            href="/dashboard"
            className="text-[15px] font-semibold tracking-tight text-[var(--chrome-text)]"
          >
            PMO · aaS
          </Link>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Cerrar menú"
            className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-2">
          <ul className="space-y-0.5">
            {NAV.map((item) => {
              const active = item.match(pathname);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex h-9 items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 text-[13px] transition-colors",
                      active
                        ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text)]"
                        : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]",
                    )}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
          <div className="mt-5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--chrome-text-muted)]/80">
            Admin
          </div>
          <ul className="mt-1 space-y-0.5">
            {ADMIN_NAV.map((item) => {
              const active = item.match(pathname);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex h-9 items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 text-[13px] transition-colors",
                      active
                        ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text)]"
                        : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]",
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
              <div className="mt-5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--chrome-text-muted)]/80">
                Super admin
              </div>
              <ul className="mt-1 space-y-0.5">
                {SUPERADMIN_NAV.map((item) => {
                  const active = item.match(pathname);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        className={cn(
                          "flex h-9 items-center gap-2.5 rounded-[var(--radius-md)] px-2.5 text-[13px] transition-colors",
                          active
                            ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text)]"
                            : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]",
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
        <div className="m-3 rounded-[var(--radius-lg)] border border-[var(--chrome-border)] bg-[var(--chrome-active)]/60 p-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 flex-none items-center justify-center rounded-[var(--radius-md)] bg-[var(--chrome-text)] text-[11px] font-bold text-[var(--chrome-bg)]">
              {(user?.full_name || user?.username || "U")
                .split(/\s+/)
                .slice(0, 2)
                .map((p) => p.charAt(0).toUpperCase())
                .join("")}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold text-[var(--chrome-text)]">
                {user?.full_name || user?.username || "—"}
              </p>
              <p className="truncate text-[11px] text-[var(--chrome-text-muted)]">
                {user?.email ?? ""}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={signingOut}
            className="mt-2 inline-flex h-8 w-full items-center gap-2 rounded-[var(--radius-sm)] px-2 text-[12px] font-medium text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)] disabled:opacity-60"
          >
            {signingOut ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <LogOut className="h-3.5 w-3.5" aria-hidden />
            )}
            Cerrar sesión
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--color-surface)] px-4 lg:px-6">
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Abrir menú"
            className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          <div className="text-[13px] text-[var(--color-tertiary)]">PMO · aaS</div>
        </header>
        <main className="flex-1 px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
