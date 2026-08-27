"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { Icono } from "@/components/ui/icono";
import { NotificationBell } from "@/components/notification-bell";
import { SwitcherDeInquilino } from "@/components/switcher-de-inquilino";
import { SwitcherDeOrganizacion } from "@/components/switcher-de-organizacion";
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
  icono: string;
  href?: string;
  match?: (path: string) => boolean;
  children?: NavItem[];
  // US-138: oculta el item del sidebar si el user no es admin / PMO del
  // tenant. Aplicado en `NavTree` con la prop `adminVisible`.
  adminOnly?: boolean;
};

// US-204 — el sidebar baja de «todo al mismo nivel» a grupos estables, según
// el mockup aprobado (`reestructura-navegacion.md` §2). Dos cambios de fondo:
//
// 1. Se disuelve el grupo colapsable «Módulos». Agrupaba por *implementación*
//    («son los módulos del producto») y no por lo que la persona va a hacer:
//    metía RAID junto a Recursos y Reportes, que no se parecen en nada. Un
//    nivel de plegado que hay que abrir para llegar a lo de todos los días es
//    un clic de peaje.
// 2. Los grupos son rótulos, no acordeones. Se ven los diez destinos a la vez;
//    con siete entradas por grupo no hace falta plegar nada.
//
// «Portafolio» apunta a `/pmo` mientras US-207 construya la vista maestra
// (control tower) que el mockup pide en ese lugar.
type GrupoNav = {
  id: string;
  titulo: string;
  items: NavItem[];
};

const GRUPOS_NAV: GrupoNav[] = [
  {
    id: "organizacion",
    titulo: "Organización",
    items: [
      {
        id: "dashboard",
        label: "Dashboard",
        icono: "layout-dashboard",
        href: "/dashboard",
        match: (p) => p === "/dashboard",
      },
      {
        id: "portfolio",
        label: "Portafolio",
        icono: "folders",
        href: "/pmo",
        match: (p) => p === "/pmo",
      },
      {
        // US-219 — el board contesta «¿qué persigo esta semana?». Va junto a
        // Portafolio porque es la misma cartera vista por otro eje.
        id: "board",
        label: "Board",
        icono: "grid-2x2",
        href: "/pmo/board",
        match: (p) => p.startsWith("/pmo/board"),
      },
      {
        id: "projects",
        label: "Proyectos",
        icono: "folder",
        href: "/pmo/projects",
        match: (p) => p.startsWith("/pmo/projects"),
      },
      {
        // US-216 — el onboarding masivo va junto a Proyectos porque es su carga
        // inicial: el artboard lo sitúa en «Org activa › Proyectos › Importar».
        id: "imports",
        label: "Importar",
        icono: "upload",
        href: "/pmo/imports",
        match: (p) => p.startsWith("/pmo/imports"),
      },
      {
        id: "requests",
        label: "Solicitudes",
        icono: "list-check",
        href: "/pmo/requests",
        match: (p) => p.startsWith("/pmo/requests"),
      },
      {
        // US-183: capacidad y saturación. El mockup lo sube al primer grupo:
        // es una pregunta de la organización, no un módulo del proyecto.
        id: "resources",
        label: "Recursos",
        icono: "users",
        href: "/pmo/resources",
        match: (p) => p.startsWith("/pmo/resources"),
      },
      {
        id: "reports",
        label: "Reportes",
        icono: "file-spreadsheet",
        href: "/pmo/reports",
        match: (p) => p === "/pmo/reports" || p.startsWith("/pmo/reports/"),
      },
    ],
  },
  {
    id: "transversal",
    titulo: "Transversal",
    items: [
      {
        id: "raid",
        label: "RAID",
        icono: "triangle-alert",
        href: "/pmo/raid",
        match: (p) => p.startsWith("/pmo/raid"),
      },
      {
        id: "changes",
        label: "Cambios",
        icono: "git-branch",
        href: "/pmo/changes",
        match: (p) => p.startsWith("/pmo/changes"),
      },
      {
        id: "minutes",
        label: "Minutas",
        icono: "file-text",
        href: "/pmo/minutes",
        match: (p) => p === "/pmo/minutes" || p.startsWith("/pmo/minutes/"),
      },
      {
        // El mockup lo pone en este grupo, y encaja: una notificación no es de
        // una organización ni de un proyecto — es de quien la recibe.
        id: "notifications",
        label: "Notificaciones",
        icono: "bell",
        href: "/notifications",
        match: (p) => p.startsWith("/notifications"),
      },
    ],
  },
];

// Admin-only. Sidebar con 4 ítems raíz (US-036 / issue #17).
// "Tenant" fusiona "Mi tenant" + "Panel del Tenant" + "Configuración"
// con tabs internos (?tab=info|branding|config|stats) en /admin/tenant.
// El drill-down por portafolio y programa vive en los filtros de cada vista
// desde US-205, no en un árbol del sidebar.
// Sigue siendo una función y no una constante porque el árbol lleva JSX de
// iconos: construirlo en el módulo lo evaluaría antes del render.
// (ENH-190 hacía configurable el label "Organizaciones"; se retiró en DEC-032.)
function buildAdminNav(): NavItem {
  return {
    id: "admin",
    label: "Admin",
    icono: "settings",
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
        icono: "building",
        href: "/admin/tenant",
        match: (p) =>
          p.startsWith("/admin/tenant") ||
          p.startsWith("/admin/supervision") ||
          p.startsWith("/admin/settings"),
      },
      {
        id: "tenant-ai",
        label: "IA",
        icono: "star",
        href: "/admin/ai",
        match: (p) => p.startsWith("/admin/ai"),
      },
      {
        id: "orgs-mgmt",
        label: "Organizaciones",
        icono: "building",
        href: "/admin/organizations",
        match: (p) =>
          p.startsWith("/admin/organizations") && !p.includes("/panel"),
      },
      {
        id: "users",
        label: "Usuarios",
        icono: "users",
        href: "/admin/users",
        match: (p) => p.startsWith("/admin/users"),
      },
      {
        id: "permissions",
        label: "Permisos",
        icono: "lock",
        href: "/admin/permissions",
        match: (p) => p.startsWith("/admin/permissions"),
      },
      {
        // US-221 — el plan va antes de Auditoría y después de Permisos: es
        // configuración de la cuenta, no un registro que se consulta.
        id: "plan",
        label: "Plan",
        icono: "credit-card",
        href: "/admin/plan",
        match: (p) => p.startsWith("/admin/plan"),
      },
      {
        id: "audit",
        label: "Auditoría",
        icono: "file-text",
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
    icono: "layout-dashboard",
    href: "/superadmin",
    match: (p) => p === "/superadmin",
  },
  {
    id: "sa-tenants",
    label: "Tenants",
    icono: "server",
    href: "/superadmin/tenants",
    match: (p) => p.startsWith("/superadmin/tenants"),
  },
  {
    id: "sa-users",
    label: "Usuarios",
    icono: "users",
    href: "/superadmin/users",
    match: (p) => p.startsWith("/superadmin/users"),
  },
  {
    id: "sa-permission-requests",
    label: "Permisos",
    icono: "lock",
    href: "/superadmin/permission-requests",
    match: (p) => p.startsWith("/superadmin/permission-requests"),
  },
  {
    id: "sa-ai",
    label: "IA",
    icono: "star",
    href: "/superadmin/ai",
    match: (p) => p.startsWith("/superadmin/ai"),
  },
  {
    id: "sa-logs",
    label: "Logs platform",
    icono: "file-text",
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

/**
 * Rótulo de grupo del sidebar. Con el sidebar colapsado desaparece en vez de
 * truncarse: «Organización» recortado a «Org…» sobre una columna de iconos no
 * informa de nada y roba las dos líneas que necesitan los destinos.
 *
 * Es `aria-hidden` y no un encabezado real porque los grupos son ayuda visual:
 * cada destino ya se anuncia por su propio texto, y un `<h3>` por grupo mete
 * tres niveles de encabezado en el árbol de accesibilidad que no corresponden
 * a la estructura del documento.
 */
function RotuloDeGrupo({ titulo, oculto }: { titulo: string; oculto: boolean }) {
  if (oculto) return null;
  return (
    <p
      aria-hidden
      className="px-3 pb-1 pt-2.5 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[var(--chrome-text-muted)]"
    >
      {titulo}
    </p>
  );
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
          "flex h-8 items-center gap-2.5 rounded-[var(--radius-md)] text-[13px] transition-colors",
          collapsed ? "justify-center px-0" : "pr-1.5",
          active
            ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text-strong)]"
            : "text-[var(--chrome-text)] hover:bg-[var(--chrome-hover)]",
        );

        // Rail colapsado (68px): solo iconos centrados. Un item de grupo
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
                  <Icono nombre={item.icono} size={17} />
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
                  <Icono nombre={item.icono} size={17} />
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
                  <Icono nombre={item.icono} size={17} />
                  <span className="truncate">{item.label}</span>
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => hasChildren && toggle(item.id)}
                  className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
                >
                  <Icono nombre={item.icono} size={17} />
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
                  className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]"
                >
                  <Icono
                    nombre="chevron-right"
                    size={14}
                    className={cn("transition-transform", isOpen && "rotate-90")}
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

  // BUG-056: el superadmin que usó "Unirme como admin" guarda
  // `active_tenant_id` en localStorage — cuando ese flag está presente se
  // renderiza como admin del tenant para que el nav y los flujos (dashboard,
  // /admin/*) le aparezcan.
  const superadminJoinedTenant = Boolean(
    user?.is_superadmin && activeTenantId,
  );
  // US-075 (DEC-022) lo llamaba `orgTreeVisible` porque decidía si se pintaba
  // el árbol del sidebar. US-205 retiró ese árbol —el contexto vive en el
  // header— y la condición sobrevive porque sigue diciendo lo mismo: si esta
  // persona está actuando dentro de un inquilino.
  const dentroDeInquilino = useMemo(
    () =>
      Boolean(user && (!user.is_superadmin || superadminJoinedTenant)),
    [user, superadminJoinedTenant],
  );
  const { roleType } = useMyPermissions();
  const adminVisible =
    superadminJoinedTenant || (dentroDeInquilino && roleType === "admin");

  const adminNav = useMemo(() => buildAdminNav(), []);

  useEffect(() => {
    setExpanded((prev) => {
      const next = new Set(prev);
      // Los grupos ya no se plegan, pero sus items sí pueden tener hijos, así
      // que el recorrido sigue: se hace por grupo en vez de sobre una lista.
      for (const grupo of GRUPOS_NAV) collectExpandedIds(grupo.items, pathname, next);
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
      {/* Topbar a sangre: se separa del cuerpo con filete + luz, sin sombra
          (Revamp v2 — el sidebar y el topbar dejan de flotar). */}
      <header
        className="flex h-[56px] shrink-0 items-center justify-between gap-2 border-b border-[var(--border-default)] px-3 shadow-[var(--linea-surco)] lg:px-4"
      >
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Abrir menú"
            className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
          >
            <Icono nombre="menu" size={19} />
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
          {/* US-205 — el contexto de organización, una vez y aquí. El mockup lo
              pega a la marca: se lee «esta plataforma, esta organización» de
              izquierda a derecha, que es el orden en que se decide. */}
          {/* US-214 — el inquilino va **antes** de la organización, porque la
              contiene: leídos de izquierda a derecha dicen «este cliente, esta
              organización suya». Al revés se leen como dos filtros
              independientes, que es lo que no son. El de inquilino se pinta solo
              con más de una membresía; él mismo lo decide. */}
          {userReady && user && !user.is_superadmin ? (
            <>
              <SwitcherDeInquilino />
              <SwitcherDeOrganizacion />
            </>
          ) : null}
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-label="Buscar"
            title="Buscar (⌘K)"
            className="hidden sm:flex h-8 w-[260px] items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-2.5 text-left shadow-[var(--hundido)]"
          >
            <Icono nombre="search" size={15} className="text-[var(--text-faint)]" />
            <span className="flex-1 truncate text-[13px] text-[var(--text-faint)]">Buscar</span>
            <kbd className="rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-tertiary)]">
              ⌘K
            </kbd>
          </button>
          <button
            type="button"
            aria-label="Buscar"
            title="Buscar"
            className="sm:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
          >
            <Icono nombre="search" size={15} />
          </button>
          {userReady && user ? <NotificationBell /> : null}
          <UserMenu user={user} variant="surface" />
        </div>
      </header>

      {/* Cuerpo: sidebar claro a sangre + área de trabajo. */}
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
            "fixed inset-y-0 left-0 z-40 flex h-full w-[216px] flex-col border-r border-[var(--chrome-border)] bg-[var(--chrome-bg)] transition-transform",
            "lg:static lg:z-auto lg:h-auto lg:translate-x-0",
            collapsed ? "lg:w-[68px]" : "lg:w-[216px]",
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
              className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
            >
              <Icono nombre="x" size={16} />
            </button>
            <button
              type="button"
              onClick={() => setCollapsedPersisted(!collapsed)}
              aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
              title={collapsed ? "Expandir menú" : "Colapsar menú"}
              className="hidden lg:inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
            >
              <Icono nombre={collapsed ? "panel-left" : "panel-left-close-dashed"} size={16} />
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-3">
            {userReady && (!user?.is_superadmin || superadminJoinedTenant)
              ? GRUPOS_NAV.map((grupo) => (
                  <div key={grupo.id} className="mb-1.5">
                    <RotuloDeGrupo titulo={grupo.titulo} oculto={collapsed} />
                    <NavTree
                      items={grupo.items}
                      pathname={pathname}
                      onNavigate={close}
                      expanded={expanded}
                      toggle={toggle}
                      adminVisible={adminVisible}
                      collapsed={collapsed}
                      onExpandSidebar={() => setCollapsedPersisted(false)}
                    />
                  </div>
                ))
              : null}
            {adminVisible ? (
              <div className="mt-0.5">
                <RotuloDeGrupo titulo="Admin" oculto={collapsed} />
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
              <div className="mt-0.5">
                <RotuloDeGrupo titulo="Plataforma" oculto={collapsed} />
                <NavTree
                  items={SUPERADMIN_NAV}
                  pathname={pathname}
                  onNavigate={close}
                  expanded={expanded}
                  toggle={toggle}
                  collapsed={collapsed}
                  onExpandSidebar={() => setCollapsedPersisted(false)}
                />
              </div>
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
