"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Building2,
  ChevronRight,
  ClipboardList,
  FileText,
  FolderKanban,
  GitPullRequest,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Network,
  ScrollText,
  ServerCog,
  Shield,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { NotificationBell } from "@/components/notification-bell";
import { OrgTreeNav } from "@/components/org-tree-nav";
import { UserMenu } from "@/components/user-menu";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { getStoredUser, type StoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

type NavItem = {
  id: string;
  label: string;
  icon: ReactNode;
  href?: string;
  match?: (path: string) => boolean;
  children?: NavItem[];
};

// US-052: sidebar top-nav extendido con vistas cross-tenant. El orden
// refleja el flujo del PMO: de resumen (Tablero) a ingreso (Solicitudes)
// a ejecución (Proyectos) a gobernanza (Módulos de Proyecto con RAID/Cambios/Minutas/Reportes).
// ENH-012: RAID, Cambios, Minutas y Reportes agrupados bajo "Módulos de Proyecto" (colapsable).
const TOP_NAV: NavItem[] = [
  {
    id: "dashboard",
    label: "Tablero",
    icon: <LayoutDashboard className="h-4 w-4" aria-hidden />,
    href: "/dashboard",
    match: (p) => p === "/dashboard",
  },
  {
    id: "requests",
    label: "Solicitudes",
    icon: <ClipboardList className="h-4 w-4" aria-hidden />,
    href: "/pmo/requests",
    match: (p) => p.startsWith("/pmo/requests"),
  },
  {
    id: "projects",
    label: "Proyectos",
    icon: <FolderKanban className="h-4 w-4" aria-hidden />,
    href: "/pmo/projects",
    match: (p) => p.startsWith("/pmo/projects"),
  },
  {
    id: "project-modules",
    label: "Módulos de Proyecto",
    icon: <FolderKanban className="h-4 w-4" aria-hidden />,
    match: (p) =>
      p.startsWith("/pmo/raid") ||
      p.startsWith("/pmo/changes") ||
      p.startsWith("/pmo/minutes") ||
      p.startsWith("/pmo/reports"),
    children: [
      {
        id: "raid",
        label: "RAID",
        icon: <Shield className="h-4 w-4" aria-hidden />,
        href: "/pmo/raid",
        match: (p) => p.startsWith("/pmo/raid"),
      },
      {
        id: "changes",
        label: "Cambios",
        icon: <GitPullRequest className="h-4 w-4" aria-hidden />,
        href: "/pmo/changes",
        match: (p) => p.startsWith("/pmo/changes"),
      },
      {
        id: "minutes",
        label: "Minutas",
        icon: <MessageSquare className="h-4 w-4" aria-hidden />,
        href: "/pmo/minutes",
        match: (p) => p === "/pmo/minutes" || p.startsWith("/pmo/minutes/"),
      },
      {
        id: "reports",
        label: "Reportes",
        icon: <FileText className="h-4 w-4" aria-hidden />,
        href: "/pmo/reports",
        match: (p) => p === "/pmo/reports" || p.startsWith("/pmo/reports/"),
      },
    ],
  },
  // US-068: vista informativa del portafolio (separada del CRUD en /admin).
  // US-075 (DEC-022): retirado del TOP_NAV — el portafolio se accede por
  // el header del OrgTreeNav (entrada `PMO`). Mantener el item aquí
  // duplicaba la entrada en el sidebar (un "PMO" en TOP_NAV + otro en
  // OrgTreeNav).
];

// Admin-only. Sidebar con 4 ítems raíz (US-036 / issue #17).
// "Tenant" fusiona "Mi tenant" + "Panel del Tenant" + "Configuración"
// con tabs internos (?tab=info|branding|config|stats) en /admin/tenant.
// El drill-down real (Organizaciones → Programas → Proyectos) vive en el
// sidebar principal vía <OrgTreeNav />.
const ADMIN_NAV: NavItem = {
  id: "admin",
  label: "Admin",
  icon: <ShieldCheck className="h-4 w-4" aria-hidden />,
  href: "/admin",
  match: (p) =>
    p === "/admin" ||
    p.startsWith("/admin/supervision") ||
    p.startsWith("/admin/users") ||
    p.startsWith("/admin/permissions") ||
    p.startsWith("/admin/audit-logs") ||
    p.startsWith("/admin/settings") ||
    p.startsWith("/admin/tenant") ||
    p.startsWith("/admin/ai") ||
    p.startsWith("/admin/organizations"),
  children: [
    {
      id: "tenant-mgmt",
      label: "Tenant",
      icon: <Building2 className="h-4 w-4" aria-hidden />,
      href: "/admin/tenant",
      match: (p) =>
        p.startsWith("/admin/tenant") ||
        p.startsWith("/admin/supervision") ||
        p.startsWith("/admin/settings"),
    },
    {
      id: "tenant-ai",
      label: "IA",
      icon: <Sparkles className="h-4 w-4" aria-hidden />,
      href: "/admin/ai",
      match: (p) => p.startsWith("/admin/ai"),
    },
    {
      id: "orgs-mgmt",
      label: "Organizaciones",
      icon: <Network className="h-4 w-4" aria-hidden />,
      href: "/admin/organizations",
      match: (p) =>
        p.startsWith("/admin/organizations") && !p.includes("/panel"),
    },
    {
      id: "users",
      label: "Usuarios",
      icon: <Users className="h-4 w-4" aria-hidden />,
      href: "/admin/users",
      match: (p) => p.startsWith("/admin/users"),
    },
    {
      id: "permissions",
      label: "Permisos",
      icon: <ShieldCheck className="h-4 w-4" aria-hidden />,
      href: "/admin/permissions",
      match: (p) => p.startsWith("/admin/permissions"),
    },
    {
      id: "audit",
      label: "Auditoría",
      icon: <ScrollText className="h-4 w-4" aria-hidden />,
      href: "/admin/audit-logs",
      match: (p) => p.startsWith("/admin/audit-logs"),
    },
  ],
};

// 4 ítems raíz, en este orden (US-041, issue #19).
const SUPERADMIN_NAV: NavItem[] = [
  {
    id: "sa-overview",
    label: "Visión General",
    icon: <LayoutDashboard className="h-4 w-4" aria-hidden />,
    href: "/superadmin",
    match: (p) => p === "/superadmin",
  },
  {
    id: "sa-tenants",
    label: "Tenants",
    icon: <ServerCog className="h-4 w-4" aria-hidden />,
    href: "/superadmin/tenants",
    match: (p) => p.startsWith("/superadmin/tenants"),
  },
  {
    id: "sa-users",
    label: "Usuarios",
    icon: <Users className="h-4 w-4" aria-hidden />,
    href: "/superadmin/users",
    match: (p) => p.startsWith("/superadmin/users"),
  },
  {
    id: "sa-ai",
    label: "IA",
    icon: <Sparkles className="h-4 w-4" aria-hidden />,
    href: "/superadmin/ai",
    match: (p) => p.startsWith("/superadmin/ai"),
  },
  {
    id: "sa-logs",
    label: "Logs platform",
    icon: <ScrollText className="h-4 w-4" aria-hidden />,
    href: "/superadmin/logs",
    match: (p) => p.startsWith("/superadmin/logs"),
  },
];

function collectExpandedIds(items: NavItem[], pathname: string, acc: Set<string>): boolean {
  let anyActive = false;
  for (const it of items) {
    const selfActive = it.match?.(pathname) ?? false;
    const childActive = it.children ? collectExpandedIds(it.children, pathname, acc) : false;
    if (childActive) acc.add(it.id);
    if (selfActive || childActive) anyActive = true;
  }
  return anyActive;
}

function NavTree({
  items,
  pathname,
  onNavigate,
  expanded,
  toggle,
  depth = 0,
}: {
  items: NavItem[];
  pathname: string;
  onNavigate: () => void;
  expanded: Set<string>;
  toggle: (id: string) => void;
  depth?: number;
}) {
  return (
    <ul className={cn("space-y-0.5", depth > 0 && "mt-0.5")}>
      {items.map((item) => {
        const hasChildren = !!item.children?.length;
        const isOpen = hasChildren && expanded.has(item.id);
        const active = item.match?.(pathname) ?? false;
        const rowClass = cn(
          "flex h-9 items-center gap-2.5 rounded-[var(--radius-md)] pr-1.5 text-[13px] transition-colors",
          active
            ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text)]"
            : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]",
        );
        const indent = { paddingLeft: `${0.625 + depth * 0.75}rem` };

        return (
          <li key={item.id}>
            <div className={rowClass} style={indent}>
              {item.href ? (
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  className="flex min-w-0 flex-1 items-center gap-2.5"
                >
                  {item.icon}
                  <span className="truncate">{item.label}</span>
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => hasChildren && toggle(item.id)}
                  className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
                >
                  {item.icon}
                  <span className="truncate">{item.label}</span>
                </button>
              )}
              {hasChildren ? (
                <button
                  type="button"
                  onClick={() => toggle(item.id)}
                  aria-label={isOpen ? `Colapsar ${item.label}` : `Expandir ${item.label}`}
                  aria-expanded={isOpen}
                  className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]"
                >
                  <ChevronRight
                    className={cn("h-3.5 w-3.5 transition-transform", isOpen && "rotate-90")}
                    aria-hidden
                  />
                </button>
              ) : null}
            </div>
            {hasChildren && isOpen ? (
              <NavTree
                items={item.children!}
                pathname={pathname}
                onNavigate={onNavigate}
                expanded={expanded}
                toggle={toggle}
                depth={depth + 1}
              />
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  // BUG-005: leer user en useEffect evita que el primer render (SSR y
  // primera hidratación cliente) muestre TOP_NAV para un superadmin antes
  // de leer localStorage. El flag `userReady` distingue "aún no leído" de
  // "leído y es null" para no flashear la navegación equivocada.
  const [user, setUser] = useState<StoredUser | null>(null);
  const [userReady, setUserReady] = useState(false);
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const close = () => setOpen(false);

  useEffect(() => {
    setUser(getStoredUser());
    setUserReady(true);
    function refresh() {
      setUser(getStoredUser());
    }
    window.addEventListener("storage", refresh);
    window.addEventListener("pmoaas:user-updated", refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("pmoaas:user-updated", refresh);
    };
  }, []);

  // US-075 (DEC-022): el OrgTreeNav lo ve cualquier usuario del tenant
  // (no solo admin). El menú ADMIN_NAV se restringe a role_type=admin
  // (o superadmin actuando como admin del tenant).
  const orgTreeVisible = useMemo(
    () => Boolean(user && !user.is_superadmin),
    [user],
  );
  const { roleType } = useMyPermissions();
  const adminVisible = orgTreeVisible && roleType === "admin";

  useEffect(() => {
    setExpanded((prev) => {
      const next = new Set(prev);
      collectExpandedIds(TOP_NAV, pathname, next);
      if (adminVisible) collectExpandedIds([ADMIN_NAV], pathname, next);
      collectExpandedIds(SUPERADMIN_NAV, pathname, next);
      return next;
    });
  }, [pathname, adminVisible]);

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-app)]">
      {open ? (
        <button
          type="button"
          aria-label="Cerrar menú"
          className="fixed inset-0 z-30 bg-[oklch(0%_0_0_/_0.35)] lg:hidden"
          onClick={close}
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex h-full w-60 flex-col border-r border-[var(--chrome-border)] transition-transform lg:static lg:translate-x-0",
          "bg-[var(--chrome-bg)]",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center justify-between px-5">
          <Link
            href={user?.is_superadmin ? "/superadmin" : "/dashboard"}
            className="inline-flex items-center"
            aria-label="Inicio"
          >
            <BrandMark variant="sidebar" />
          </Link>
          <button
            type="button"
            onClick={close}
            aria-label="Cerrar menú"
            className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-2">
          {userReady && !user?.is_superadmin ? (
            <NavTree
              items={TOP_NAV}
              pathname={pathname}
              onNavigate={close}
              expanded={expanded}
              toggle={toggle}
            />
          ) : null}
          {orgTreeVisible ? (
            <div className="mt-0.5">
              <OrgTreeNav onNavigate={close} />
            </div>
          ) : null}
          {adminVisible ? (
            <div className="mt-0.5">
              <NavTree
                items={[ADMIN_NAV]}
                pathname={pathname}
                onNavigate={close}
                expanded={expanded}
                toggle={toggle}
              />
            </div>
          ) : null}
          {userReady && user?.is_superadmin ? (
            <NavTree
              items={SUPERADMIN_NAV}
              pathname={pathname}
              onNavigate={close}
              expanded={expanded}
              toggle={toggle}
            />
          ) : null}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-[var(--chrome-border)] bg-[var(--chrome-bg)] px-4 lg:px-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-label="Abrir menú"
              className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
            >
              <Menu className="h-5 w-5" aria-hidden />
            </button>
            <div className="inline-flex items-center">
              <span className="text-[13px] font-medium tracking-tight text-[var(--chrome-text-muted)]">
                PMO · aaS
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {userReady && user ? <NotificationBell /> : null}
            <UserMenu user={user} variant="chrome" />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
