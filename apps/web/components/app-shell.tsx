"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  BarChart3,
  Building2,
  ChevronRight,
  ClipboardList,
  Cog,
  Eye,
  FileText,
  FolderKanban,
  GitPullRequest,
  LayoutDashboard,
  Layers,
  Lightbulb,
  ListTree,
  Menu,
  MessageSquare,
  Network,
  ScrollText,
  ServerCog,
  Shield,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Users,
  X,
} from "lucide-react";

import { OrgTreeNav } from "@/components/org-tree-nav";
import { UserMenu } from "@/components/user-menu";
import { getStoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

type NavItem = {
  id: string;
  label: string;
  icon: ReactNode;
  href?: string;
  match?: (path: string) => boolean;
  children?: NavItem[];
};

const PROJECT_ID_RE = /^\/admin\/projects\/([^/]+)(?:\/|$)/;

function projectModuleHref(pathname: string, slug: string): string {
  const m = PROJECT_ID_RE.exec(pathname);
  if (m && m[1] !== "new") {
    return `/admin/projects/${m[1]}/${slug}`;
  }
  return "/admin/projects";
}

function buildNav(pathname: string): NavItem[] {
  const projectModules: NavItem[] = [
    {
      id: "mod-risks",
      label: "Riesgos",
      icon: <TriangleAlert className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "risks"),
      match: (p) => /^\/admin\/projects\/[^/]+\/risks/.test(p),
    },
    {
      id: "mod-issues",
      label: "AIDs",
      icon: <Shield className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "issues"),
      match: (p) => /^\/admin\/projects\/[^/]+\/issues/.test(p),
    },
    {
      id: "mod-changes",
      label: "Cambios",
      icon: <GitPullRequest className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "changes"),
      match: (p) => /^\/admin\/projects\/[^/]+\/changes/.test(p),
    },
    {
      id: "mod-documents",
      label: "Documentos",
      icon: <FileText className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "documents"),
      match: (p) => /^\/admin\/projects\/[^/]+\/documents/.test(p),
    },
    {
      id: "mod-lessons",
      label: "Lecciones",
      icon: <Lightbulb className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "lessons"),
      match: (p) => /^\/admin\/projects\/[^/]+\/lessons/.test(p),
    },
    {
      id: "mod-minutes",
      label: "Minutas",
      icon: <MessageSquare className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "minutes"),
      match: (p) => /^\/admin\/projects\/[^/]+\/minutes(?!\/ai)/.test(p),
    },
    {
      id: "mod-tasks",
      label: "Tareas",
      icon: <ListTree className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "tasks"),
      match: (p) => /^\/admin\/projects\/[^/]+\/tasks/.test(p),
    },
    {
      id: "mod-gantt",
      label: "Gantt",
      icon: <BarChart3 className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "gantt"),
      match: (p) => /^\/admin\/projects\/[^/]+\/gantt/.test(p),
    },
    {
      id: "mod-ai-minutes",
      label: "Minuta IA",
      icon: <Sparkles className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "ai-minutes/new"),
      match: (p) => /^\/admin\/projects\/[^/]+\/ai-minutes/.test(p),
    },
    {
      id: "mod-reports",
      label: "Reporte IA",
      icon: <Sparkles className="h-4 w-4" aria-hidden />,
      href: projectModuleHref(pathname, "reports"),
      match: (p) => /^\/admin\/projects\/[^/]+\/reports/.test(p),
    },
  ];

  return [
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
      href: "/admin/requests",
      match: (p) => p.startsWith("/admin/requests"),
    },
    {
      id: "organizations",
      label: "Organizaciones",
      icon: <Building2 className="h-4 w-4" aria-hidden />,
      href: "/admin/organizations",
      match: (p) => p.startsWith("/admin/organizations"),
      children: [
        {
          id: "programs",
          label: "Programas",
          icon: <Network className="h-4 w-4" aria-hidden />,
          href: "/admin/programs",
          match: (p) => p.startsWith("/admin/programs"),
        },
        {
          id: "projects",
          label: "Proyectos",
          icon: <FolderKanban className="h-4 w-4" aria-hidden />,
          href: "/admin/projects",
          match: (p) => p.startsWith("/admin/projects"),
          children: [
            {
              id: "project-modules",
              label: "Módulos de Proyectos",
              icon: <Layers className="h-4 w-4" aria-hidden />,
              match: (p) => /^\/admin\/projects\/[^/]+\/(risks|issues|changes|documents|lessons|minutes|tasks|gantt|ai-minutes|reports)/.test(p),
              children: projectModules,
            },
          ],
        },
      ],
    },
    {
      id: "admin",
      label: "Admin",
      icon: <ShieldCheck className="h-4 w-4" aria-hidden />,
      match: (p) =>
        p.startsWith("/admin/supervision") ||
        p.startsWith("/admin/users") ||
        p.startsWith("/admin/roles") ||
        p.startsWith("/admin/audit-logs") ||
        p.startsWith("/admin/settings"),
      children: [
        {
          id: "tenant-panel",
          label: "Panel del Tenant",
          icon: <Eye className="h-4 w-4" aria-hidden />,
          href: "/admin/supervision",
          match: (p) => p.startsWith("/admin/supervision"),
        },
        {
          id: "users",
          label: "Usuarios",
          icon: <Users className="h-4 w-4" aria-hidden />,
          href: "/admin/users",
          match: (p) => p.startsWith("/admin/users"),
        },
        {
          id: "roles",
          label: "Roles",
          icon: <ShieldCheck className="h-4 w-4" aria-hidden />,
          href: "/admin/roles",
          match: (p) => p.startsWith("/admin/roles"),
        },
        {
          id: "audit",
          label: "Auditoría",
          icon: <ScrollText className="h-4 w-4" aria-hidden />,
          href: "/admin/audit-logs",
          match: (p) => p.startsWith("/admin/audit-logs"),
        },
        {
          id: "settings",
          label: "Configuración",
          icon: <Cog className="h-4 w-4" aria-hidden />,
          href: "/admin/settings",
          match: (p) => p.startsWith("/admin/settings"),
        },
      ],
    },
  ];
}

const SUPERADMIN_NAV: NavItem[] = [
  {
    id: "sa-overview",
    label: "Visión general",
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
    id: "sa-logs",
    label: "Logs platform",
    icon: <ScrollText className="h-4 w-4" aria-hidden />,
    href: "/superadmin/logs",
    match: (p) => p.startsWith("/superadmin/logs"),
  },
  {
    id: "sa-health",
    label: "Health",
    icon: <Activity className="h-4 w-4" aria-hidden />,
    href: "/superadmin/health",
    match: (p) => p.startsWith("/superadmin/health"),
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
  const user = getStoredUser();
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const close = () => setOpen(false);

  const nav = useMemo(() => buildNav(pathname), [pathname]);

  useEffect(() => {
    setExpanded((prev) => {
      const next = new Set(prev);
      collectExpandedIds(nav, pathname, next);
      collectExpandedIds(SUPERADMIN_NAV, pathname, next);
      return next;
    });
  }, [pathname, nav]);

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="flex min-h-screen bg-[var(--color-app)]">
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
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-[var(--chrome-border)] transition-transform lg:static lg:translate-x-0",
          "bg-[var(--chrome-bg)]",
          open ? "translate-x-0" : "-translate-x-full",
        )}
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
            onClick={close}
            aria-label="Cerrar menú"
            className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-2">
          <NavTree
            items={nav}
            pathname={pathname}
            onNavigate={close}
            expanded={expanded}
            toggle={toggle}
          />
          {user && !user.is_superadmin ? (
            <OrgTreeNav onNavigate={close} />
          ) : null}
          {user?.is_superadmin ? (
            <>
              <div className="mt-5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--chrome-text-muted)]/80">
                Super admin
              </div>
              <div className="mt-1">
                <NavTree
                  items={SUPERADMIN_NAV}
                  pathname={pathname}
                  onNavigate={close}
                  expanded={expanded}
                  toggle={toggle}
                />
              </div>
            </>
          ) : null}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-2 border-b border-[var(--chrome-border)] bg-[var(--chrome-bg)] px-4 lg:px-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-label="Abrir menú"
              className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)]"
            >
              <Menu className="h-5 w-5" aria-hidden />
            </button>
            <div className="text-[13px] font-medium text-[var(--chrome-text-muted)]">
              PMO · aaS
            </div>
          </div>
          <UserMenu user={user} variant="chrome" />
        </header>
        <main className="flex-1 px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
