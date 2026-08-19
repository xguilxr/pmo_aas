"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  BarChart3,
  Boxes,
  Building2,
  ChevronRight,
  ClipboardCheck,
  FolderKanban,
  Gauge,
  GitBranch,
  Inbox,
  KeyRound,
  LayoutDashboard,
  Menu,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  ScrollText,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";

import { NotificationBell } from "@/components/notification-bell";
import { OrgTreeNav } from "@/components/org-tree-nav";
import { useTenantBranding } from "@/components/tenant-branding-provider";
import { UserMenu } from "@/components/user-menu";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { resolveLogoUrl } from "@/lib/api/branding";
import {
  getActiveTenantId,
  getStoredUser,
  type StoredUser,
} from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

const SIDEBAR_COLLAPSE_KEY = "pmoaas:sidebar-collapsed";

type NavItem = {
  id: string;
  label: string;
  icon: ReactNode;
  href?: string;
  match?: (path: string) => boolean;
  children?: NavItem[];
  // US-138: oculta el item del sidebar si el user no es admin / PMO del
  // tenant. Aplicado en `NavTree` con la prop `adminVisible`.
  adminOnly?: boolean;
};

// US-052: sidebar top-nav extendido con vistas cross-tenant. El orden
// refleja el flujo del PMO: de resumen (Tablero) a ingreso (Solicitudes)
// a ejecución (Proyectos) a gobernanza (Módulos con RAID/Cambios/Minutas/Reportes).
// ENH-012 / ENH-116: RAID, Cambios, Minutas y Reportes agrupados bajo "Módulos" (colapsable).
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
    icon: <Inbox className="h-4 w-4" aria-hidden />,
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
    label: "Módulos",
    icon: <Boxes className="h-4 w-4" aria-hidden />,
    match: (p) =>
      p.startsWith("/pmo/raid") ||
      p.startsWith("/pmo/changes") ||
      p.startsWith("/pmo/minutes") ||
      p.startsWith("/pmo/reports") ||
      p.startsWith("/pmo/resources"),
    children: [
      {
        id: "raid",
        label: "RAID",
        icon: <ShieldAlert className="h-4 w-4" aria-hidden />,
        href: "/pmo/raid",
        match: (p) => p.startsWith("/pmo/raid"),
      },
      {
        id: "changes",
        label: "Cambios",
        icon: <GitBranch className="h-4 w-4" aria-hidden />,
        href: "/pmo/changes",
        match: (p) => p.startsWith("/pmo/changes"),
      },
      {
        id: "minutes",
        label: "Minutas",
        icon: <MessageSquareText className="h-4 w-4" aria-hidden />,
        href: "/pmo/minutes",
        match: (p) => p === "/pmo/minutes" || p.startsWith("/pmo/minutes/"),
      },
      {
        // ENH-116: Reportes ahora apunta directo a /pmo/reports (sin
        // dropdown). Builder Portafolio vive como TAB dentro de esa
        // página (US-144). Esto aplana la jerarquía del sidebar.
        id: "reports",
        label: "Reportes",
        icon: <BarChart3 className="h-4 w-4" aria-hidden />,
        href: "/pmo/reports",
        match: (p) => p === "/pmo/reports" || p.startsWith("/pmo/reports/"),
      },
      {
        // US-183: vista ejecutiva de capacidad/saturación de recursos
        // (individual + rol/área/equipo + conflictos).
        id: "resources",
        label: "Recursos",
        icon: <Gauge className="h-4 w-4" aria-hidden />,
        href: "/pmo/resources",
        match: (p) => p.startsWith("/pmo/resources"),
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
// Sigue siendo una función y no una constante porque el árbol lleva JSX de
// iconos: construirlo en el módulo lo evaluaría antes del render.
// (ENH-190 hacía configurable el label "Organizaciones"; se retiró en DEC-032.)
function buildAdminNav(): NavItem {
  return {
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
        icon: <Building2 className="h-4 w-4" aria-hidden />,
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
        icon: <ClipboardCheck className="h-4 w-4" aria-hidden />,
        href: "/admin/audit-logs",
        match: (p) => p.startsWith("/admin/audit-logs"),
      },
    ],
  };
}

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
    icon: <Server className="h-4 w-4" aria-hidden />,
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
    id: "sa-permission-requests",
    label: "Permisos",
    icon: <KeyRound className="h-4 w-4" aria-hidden />,
    href: "/superadmin/permission-requests",
    match: (p) => p.startsWith("/superadmin/permission-requests"),
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
  adminVisible = false,
  collapsed = false,
  onExpandSidebar,
}: {
  items: NavItem[];
  pathname: string;
  onNavigate: () => void;
  expanded: Set<string>;
  toggle: (id: string) => void;
  depth?: number;
  adminVisible?: boolean;
  collapsed?: boolean;
  onExpandSidebar?: () => void;
}) {
  // US-138: filtra items con `adminOnly` cuando el user no es admin / PMO.
  const visibleItems = items.filter((it) => !it.adminOnly || adminVisible);
  return (
    <ul className={cn("space-y-0.5", depth > 0 && !collapsed && "mt-0.5")}>
      {visibleItems.map((item) => {
        const hasChildren = !!item.children?.length;
        const isOpen = hasChildren && expanded.has(item.id);
        const active = item.match?.(pathname) ?? false;
        const rowClass = cn(
          "flex h-9 items-center gap-2.5 rounded-[var(--radius-md)] text-[13px] transition-colors",
          collapsed ? "justify-center px-0" : "pr-1.5",
          active
            ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text-strong)]"
            : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text-strong)]",
        );

        // Rail colapsado (76px): solo iconos centrados. Un item de grupo
        // re-expande el sidebar al hacer click (no hay flyout).
        if (collapsed) {
          return (
            <li key={item.id}>
              {item.href ? (
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  title={item.label}
                  aria-label={item.label}
                  className={rowClass}
                >
                  {item.icon}
                </Link>
              ) : (
                <button
                  type="button"
                  title={item.label}
                  aria-label={item.label}
                  onClick={() => {
                    onExpandSidebar?.();
                    if (hasChildren && !expanded.has(item.id)) toggle(item.id);
                  }}
                  className={cn(rowClass, "w-full")}
                >
                  {item.icon}
                </button>
              )}
            </li>
          );
        }

        const indent = { paddingLeft: `${0.625 + depth * 0.75}rem` };
        // Los grupos de primer nivel (con hijos) actúan como encabezados de
        // sección: label en mayúsculas (US-164).
        const isSectionHeader = depth === 0 && hasChildren;

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
                  <span
                    className={cn(
                      "truncate",
                      isSectionHeader && "text-[11px] font-semibold uppercase tracking-wide",
                    )}
                  >
                    {item.label}
                  </span>
                </button>
              )}
              {hasChildren ? (
                <button
                  type="button"
                  onClick={() => toggle(item.id)}
                  aria-label={isOpen ? `Colapsar ${item.label}` : `Expandir ${item.label}`}
                  aria-expanded={isOpen}
                  className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text-strong)]"
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
                adminVisible={adminVisible}
                onExpandSidebar={onExpandSidebar}
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
  // El detalle de proyecto monta la barra de tabs sticky (project-tabs-bar);
  // ahí el scroll container no lleva padding-top para que la barra pegue
  // flush bajo el topbar. La página de creación (/projects/new) no la monta.
  const isProjectDetail =
    /^\/pmo\/projects\/[^/]+/.test(pathname) &&
    !pathname.includes("/projects/new");
  // BUG-005: leer user en useEffect evita que el primer render (SSR y
  // primera hidratación cliente) muestre TOP_NAV para un superadmin antes
  // de leer localStorage. El flag `userReady` distingue "aún no leído" de
  // "leído y es null" para no flashear la navegación equivocada.
  const [user, setUser] = useState<StoredUser | null>(null);
  const [userReady, setUserReady] = useState(false);
  const [activeTenantId, setActiveTid] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const close = () => setOpen(false);

  // US-164: colapso del sidebar (desktop), persistido en localStorage.
  const [collapsed, setCollapsed] = useState(false);
  const { branding } = useTenantBranding();

  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === "1");
    } catch {
      /* ignore */
    }
  }, []);

  const setCollapsedPersisted = (next: boolean) => {
    setCollapsed(next);
    try {
      window.localStorage.setItem(SIDEBAR_COLLAPSE_KEY, next ? "1" : "0");
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    setUser(getStoredUser());
    setActiveTid(getActiveTenantId());
    setUserReady(true);
    function refresh() {
      setUser(getStoredUser());
      setActiveTid(getActiveTenantId());
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
  // BUG-056: el superadmin que usó "Unirme como admin" guarda
  // `active_tenant_id` en localStorage — cuando ese flag está presente
  // se renderiza como admin del tenant para que el nav y los flujos
  // (dashboard, /admin/*, OrgTreeNav) le aparezcan.
  const superadminJoinedTenant = Boolean(
    user?.is_superadmin && activeTenantId,
  );
  const orgTreeVisible = useMemo(
    () =>
      Boolean(user && (!user.is_superadmin || superadminJoinedTenant)),
    [user, superadminJoinedTenant],
  );
  const { roleType } = useMyPermissions();
  const adminVisible =
    superadminJoinedTenant || (orgTreeVisible && roleType === "admin");

  // ENH-190: label configurable por tenant para "Organización(es)".
  const adminNav = useMemo(() => buildAdminNav(), []);

  useEffect(() => {
    setExpanded((prev) => {
      const next = new Set(prev);
      collectExpandedIds(TOP_NAV, pathname, next);
      if (adminVisible) collectExpandedIds([adminNav], pathname, next);
      collectExpandedIds(SUPERADMIN_NAV, pathname, next);
      return next;
    });
  }, [pathname, adminVisible, adminNav]);

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const homeHref = user?.is_superadmin ? "/superadmin" : "/dashboard";
  const logoSrc = resolveLogoUrl(branding?.logo_url ?? null);
  const brandName = branding?.tenant_name ?? "PMO · aaS";

  return (
    <div className="flex h-screen flex-col bg-[var(--color-app)]">
      {/* Topbar full-width sobre el lienzo cream (US-164). */}
      <header className="flex h-[60px] shrink-0 items-center justify-between gap-2 px-3 lg:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Abrir menú"
            className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          <Link
            href={homeHref}
            className="flex min-w-0 items-center gap-3"
            aria-label="Inicio"
          >
            {logoSrc ? (
              <span className="flex h-11 w-[200px] flex-none items-center overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={logoSrc}
                  alt={brandName}
                  className="h-full w-auto max-w-full object-contain object-left"
                />
              </span>
            ) : (
              <span className="truncate text-[15px] font-semibold tracking-tight text-[var(--color-primary)]">
                {brandName}
              </span>
            )}
            <span className="whitespace-nowrap text-[13px] font-medium tracking-tight text-[var(--text-tertiary)]">
              PMO-aaS
            </span>
          </Link>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-label="Buscar"
            title="Buscar"
            className="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
          >
            <Search className="h-4 w-4" aria-hidden />
          </button>
          {userReady && user ? <NotificationBell /> : null}
          <UserMenu user={user} variant="surface" />
        </div>
      </header>

      {/* Cuerpo: sidebar azul flotante + área de trabajo en el lienzo. */}
      <div className="flex min-h-0 flex-1">
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
            "fixed inset-y-0 left-0 z-40 flex h-full w-60 flex-col rounded-r-[14px] bg-[var(--chrome-bg)] shadow-[var(--sb-shadow)] transition-transform",
            "lg:static lg:z-auto lg:h-auto lg:translate-x-0 lg:mb-3 lg:ml-3 lg:mt-1.5 lg:rounded-[14px]",
            collapsed ? "lg:w-[76px]" : "lg:w-60",
            open ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div
            className={cn(
              "flex h-12 items-center px-2",
              collapsed ? "justify-end lg:justify-center" : "justify-end",
            )}
          >
            <button
              type="button"
              onClick={close}
              aria-label="Cerrar menú"
              className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text-strong)]"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
            <button
              type="button"
              onClick={() => setCollapsedPersisted(!collapsed)}
              aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
              title={collapsed ? "Expandir menú" : "Colapsar menú"}
              className="hidden lg:inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text-strong)]"
            >
              {collapsed ? (
                <PanelLeftOpen className="h-4 w-4" aria-hidden />
              ) : (
                <PanelLeftClose className="h-4 w-4" aria-hidden />
              )}
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-3">
            {userReady && (!user?.is_superadmin || superadminJoinedTenant) ? (
              <NavTree
                items={TOP_NAV}
                pathname={pathname}
                onNavigate={close}
                expanded={expanded}
                toggle={toggle}
                adminVisible={adminVisible}
                collapsed={collapsed}
                onExpandSidebar={() => setCollapsedPersisted(false)}
              />
            ) : null}
            {orgTreeVisible && !collapsed ? (
              <div className="mt-0.5">
                <OrgTreeNav onNavigate={close} />
              </div>
            ) : null}
            {adminVisible ? (
              <div className="mt-0.5">
                <NavTree
                  items={[adminNav]}
                  pathname={pathname}
                  onNavigate={close}
                  expanded={expanded}
                  toggle={toggle}
                  collapsed={collapsed}
                  onExpandSidebar={() => setCollapsedPersisted(false)}
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
                collapsed={collapsed}
                onExpandSidebar={() => setCollapsedPersisted(false)}
              />
            ) : null}
          </nav>
        </aside>

        <main
          className={cn(
            "min-w-0 flex-1 overflow-y-auto px-4 lg:px-8",
            // En el detalle de proyecto la barra de tabs es sticky y debe
            // pegar flush bajo el topbar; el padding-top del scroll container
            // rompería ese anclaje (desfase + bleed-through), así que se quita
            // solo aquí. El resto de páginas conserva su respiro superior.
            isProjectDetail ? "pb-6" : "py-6",
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
